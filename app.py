from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.service import Service
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import json
import os
import time
import schedule
import threading
import atexit
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('whatsapp_bot.log'),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

# Global variables
bot = None
bot_thread = None
scheduler_thread = None
is_bot_running = False

# Initialize scheduler when the app starts
def init_scheduler():
    global scheduler_thread, is_bot_running
    is_bot_running = True
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logging.info("Scheduler thread started")

# Cleanup function to be called on exit
def cleanup():
    global is_bot_running
    is_bot_running = False
    if 'bot' in globals() and bot:
        try:
            bot.quit()
            logging.info("Browser closed during cleanup")
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

# Register cleanup function
atexit.register(cleanup)

def load_config():
    """Load configuration from config.json"""
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {
        'recipients': [],
        'message_templates': [],
        'scheduled_messages': [],
        'message_history': [],
        'stats': {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'pending': 0
        }
    }

def save_config(config):
    """Save configuration to config.json"""
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=4)

def update_stats(status):
    """Update message statistics"""
    config = load_config()
    config['stats']['total'] += 1
    if status == 'success':
        config['stats']['successful'] += 1
    elif status == 'error':
        config['stats']['failed'] += 1
    save_config(config)

def add_to_history(recipient, message, status):
    """Add message to history"""
    config = load_config()
    config['message_history'].append({
        'recipient': recipient,
        'message': message,
        'status': status,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })
    save_config(config)

def setup_scheduled_message(schedule_item, recipient, template):
    """Set up a scheduled message using the schedule library"""
    try:
        logging.info(f"[SCHEDULER] Setting up message: ID {schedule_item['id']} for {schedule_item['date']} at {schedule_item['time']}")
        
        # Parse the schedule time in local timezone
        schedule_time = datetime.strptime(schedule_item['time'], '%H:%M').time()
        schedule_date = datetime.strptime(schedule_item['date'], '%Y-%m-%d').date()
        
        # Combine date and time in local timezone
        schedule_datetime = datetime.combine(schedule_date, schedule_time)
        now = datetime.now()
        
        # Calculate time difference in minutes
        time_diff = (schedule_datetime - now).total_seconds() / 60  # in minutes
        
        # If the message is more than 1 minute in the past, skip it
        if time_diff < -1:  # Changed from 5 minutes to 1 minute buffer
            logging.warning(f"[SCHEDULER] Skipping past schedule: {schedule_item['id']} at {schedule_datetime} ({abs(time_diff):.1f} minutes ago)")
            return False
        # If the message is in the past but within 1 minute, still send it
        elif time_diff < 0:
            logging.warning(f"[SCHEDULER] Message {schedule_item['id']} is {abs(time_diff):.1f} minutes in the past, but will still attempt to send")
        # If the message is in the future, log how long until it will be sent
        else:
            logging.info(f"[SCHEDULER] Message {schedule_item['id']} will be sent in {time_diff:.1f} minutes")
            
        # Create a function to send the message
        def send_message():
            logging.info(f"[SCHEDULER] [JOB START] Executing scheduled message for {recipient.get('name')}")
            try:
                logging.info(f"[SCHEDULER] [JOB] Sending message to {recipient.get('phone')}")
                send_scheduled_message(recipient, template)
                logging.info(f"[SCHEDULER] [JOB SUCCESS] Message sent to {recipient.get('name')}")
            except Exception as e:
                logging.error(f"[SCHEDULER] [JOB ERROR] Error sending message: {str(e)}", exc_info=True)
        
        # Get schedule ID for logging
        schedule_id = str(schedule_item.get('id', 'unknown'))
        logging.info(f"[SCHEDULER] Creating schedule {schedule_id} for {schedule_item['type']} at {schedule_time}")
        
        # Schedule based on type
        if schedule_item['type'] == 'one_time':
            # For one-time messages, schedule to run once at the specified time
            logging.info(f"[SCHEDULER] Creating schedule {schedule_id} for one_time at {schedule_time}")
            
            # Calculate delay in seconds
            delay_seconds = (schedule_datetime - datetime.now()).total_seconds()
            
            # If the message is in the past but within 1 minute, send it immediately
            if -60 <= delay_seconds < 0:
                logging.info(f"[SCHEDULER] Sending one-time message {schedule_id} immediately (was {abs(delay_seconds):.0f} seconds ago)")
                send_message()
                return True
            # If the message is in the future, schedule it
            elif delay_seconds >= 0:
                logging.info(f"[SCHEDULER] Scheduling one-time message {schedule_id} in {delay_seconds:.0f} seconds")
                # Schedule the message using a separate thread with a delay
                def schedule_one_time():
                    time.sleep(delay_seconds)
                    send_message()
                
                thread = threading.Thread(target=schedule_one_time, daemon=True)
                thread.start()
                return True
            # Otherwise, the message is too far in the past
            else:
                logging.warning(f"[SCHEDULER] Not scheduling one-time message {schedule_id} from {abs(delay_seconds/60):.1f} minutes ago")
                return False
            
        elif schedule_item['type'] == 'daily':
            logging.info(f"[SCHEDULER] Scheduling daily message at {schedule_time}")
            schedule.every().day.at(schedule_time.strftime('%H:%M')).do(send_message).tag(schedule_id)
            
        elif schedule_item['type'] == 'weekly':
            day = schedule_item.get('day', 'monday').lower()
            logging.info(f"[SCHEDULER] Scheduling weekly message on {day} at {schedule_time}")
            getattr(schedule.every(), day).at(schedule_time.strftime('%H:%M')).do(send_message).tag(schedule_id)
            
        elif schedule_item['type'] == 'monthly':
            day_of_month = schedule_item.get('day', 1)
            logging.info(f"[SCHEDULER] Scheduling monthly message on day {day_of_month} at {schedule_time}")
            
            def monthly_job():
                now = datetime.now()
                if now.day == day_of_month:
                    logging.info(f"[SCHEDULER] Executing monthly message for day {day_of_month}")
                    send_scheduled_message(recipient, template)
                else:
                    logging.info(f"[SCHEDULER] Not the right day for monthly message (today is {now.day}, waiting for {day_of_month})")
                    
            schedule.every().day.at(schedule_time.strftime('%H:%M')).do(monthly_job).tag(schedule_id)
        
        # Log all scheduled jobs for debugging
        jobs = schedule.get_jobs()
        logging.info(f"[SCHEDULER] Current jobs: {len(jobs)}")
        for job in jobs:
            logging.info(f"[SCHEDULER] Job {job.id}: {job.job_func} at {job.next_run}")
            
        return True
        
    except Exception as e:
        logging.error(f"[SCHEDULER] Error setting up scheduled message: {str(e)}", exc_info=True)
        return False

@app.route('/check_schedules', methods=['GET'])
def check_schedules():
    """Manually trigger a check of all schedules"""
    logging.info("[SCHEDULER] Manually triggered schedule check")
    setup_all_schedules()
    return jsonify({'status': 'success', 'message': 'Schedule check completed'})

def setup_all_schedules():
    """Set up all active, future scheduled messages from config"""
    config = load_config()
    now = datetime.now()
    logging.info(f"[SCHEDULER] Starting schedule check at {now}")
    
    for schedule_item in config['scheduled_messages']:
        if not schedule_item.get('active', True):
            continue
            
        # Parse schedule time
        try:
            schedule_time = datetime.strptime(schedule_item['time'], '%H:%M').time()
            schedule_date = datetime.strptime(schedule_item['date'], '%Y-%m-%d').date()
            schedule_datetime = datetime.combine(schedule_date, schedule_time)
            
            # Add a 5-minute buffer to handle slight time differences
            buffer = timedelta(minutes=5)
            
            # Only skip if the schedule is more than 5 minutes in the past
            if schedule_datetime < (now - buffer):
                logging.info(f"[SCHEDULER] Skipping past schedule: {schedule_item['id']} at {schedule_datetime}")
                continue
                
        except Exception as e:
            logging.error(f"[SCHEDULER] Error parsing schedule {schedule_item.get('id')}: {str(e)}")
            continue
            
        # Find recipient and template
        recipient = next((r for r in config['recipients'] 
                        if str(r['id']) == str(schedule_item['recipient_id'])), None)
        template = next((t for t in config['message_templates'] 
                        if str(t['id']) == str(schedule_item['template_id'])), None)
                        
        if recipient and template:
            logging.info(f"[SCHEDULER] Setting up future schedule: {schedule_item['id']} for {schedule_datetime}")
            setup_scheduled_message(schedule_item, recipient, template)
        else:
            logging.warning(f"[SCHEDULER] Could not find recipient or template for schedule {schedule_item['id']}")

def send_scheduled_message(recipient, template):
    """Send a scheduled message"""
    try:
        logging.info(f"Attempting to send message to {recipient.get('name', 'Unknown')} with template {template.get('name', 'Unknown')}")
        message = template['content'].format(name=recipient['name'])
        logging.info(f"Formatted message: {message[:100]}{'...' if len(message) > 100 else ''}")
        success = send_whatsapp_message(recipient['phone'], message)
        status = 'success' if success else 'error'
        logging.info(f"Message send status: {status}")
        add_to_history(recipient['name'], message, status)
        update_stats(status)
        return success
    except Exception as e:
        error_msg = f"Error sending scheduled message: {str(e)}"
        logging.error(error_msg, exc_info=True)
        if 'recipient' in locals() and 'template' in locals():
            add_to_history(recipient.get('name', 'Unknown'), 
                         template.get('content', 'No content'), 
                         'error')
            update_stats('error')
        return False

def send_whatsapp_message(phone, message):
    global bot
    try:
        # Use the existing bot instance if available
        if not bot:
            logging.error("Bot is not initialized. Please start the bot first.")
            return False
            
        driver = bot  # Use the existing browser instance
        
        # Format phone number
        phone = phone.replace('+', '').replace(' ', '')
        
        # Navigate to WhatsApp Web
        driver.get(f'https://web.whatsapp.com/send?phone={phone}&text={message}')
        
        # Wait for send button and click it
        send_button = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[@data-icon='send']"))
        )
        send_button.click()
        
        # Wait for message to be sent
        time.sleep(2)
        driver.quit()
        return True
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        if 'driver' in locals():
            driver.quit()
        return False

def run_scheduler():
    """Run the scheduler in the main thread"""
    logging.info("[SCHEDULER] Scheduler started")
    last_check = time.time()
    
    while is_bot_running:
        try:
            current_time = time.time()
            
            # Log job status every 30 seconds
            if current_time - last_check > 30:
                jobs = schedule.jobs
                if jobs:
                    next_run = min(job.next_run for job in jobs) if jobs else None
                    logging.info(f"[SCHEDULER] {len(jobs)} pending jobs, next run: {next_run}")
                    for i, job in enumerate(jobs, 1):
                        logging.info(f"  Job {i}: {job.job_func.__name__} at {job.next_run}")
                else:
                    logging.info("[SCHEDULER] No pending jobs")
                last_check = current_time
            
            # Run pending jobs
            schedule.run_pending()
            
            # Small delay to prevent high CPU usage
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"[SCHEDULER] Error in scheduler: {str(e)}", exc_info=True)
            time.sleep(5)  # Wait before retrying if there's an error

def start_bot():
    """Start the WhatsApp bot"""
    global bot, bot_thread, is_bot_running
    
    try:
        # Set up Edge options
        edge_options = EdgeOptions()
        
        # Add these essential arguments
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--start-maximized")
        edge_options.add_argument("--remote-debugging-port=9222")
        
        # Add SSL error handling
        edge_options.add_argument('--ignore-certificate-errors')
        edge_options.add_argument('--ignore-ssl-errors=yes')
        edge_options.add_argument('--allow-insecure-localhost')
        
        # Set user data directory
        user_data_dir = os.path.abspath(os.path.join(os.getcwd(), "whatsapp_bot_profile"))
        if not os.path.exists(user_data_dir):
            os.makedirs(user_data_dir)
        edge_options.add_argument(f"user-data-dir={user_data_dir}")
        
        # Disable automation flags and identity features
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        edge_options.add_experimental_option('useAutomationExtension', False)
        edge_options.add_argument("--disable-features=msEdgeAccountProfile")
        
        # Initialize the WebDriver with better error handling
        try:
            service = EdgeService(EdgeChromiumDriverManager().install())
            bot = webdriver.Edge(service=service, options=edge_options)
            logging.info("WebDriver initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize WebDriver: {str(e)}", exc_info=True)
            return False
        
        try:
            # Navigate to WhatsApp Web
            logging.info("Navigating to WhatsApp Web...")
            bot.get('https://web.whatsapp.com')
            
            # Wait for QR code scan with better timeout handling
            try:
                WebDriverWait(bot, 120).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@id="side"]'))
                )
                logging.info("Successfully logged in to WhatsApp Web")
            except TimeoutException:
                logging.error("Timeout waiting for WhatsApp Web to load")
                return False
            
            is_bot_running = True
            
            # Set up all schedules
            setup_all_schedules()
            logging.info("All schedules set up successfully")
            
            return True
            
        except Exception as e:
            logging.error(f"Error during WhatsApp Web navigation: {str(e)}", exc_info=True)
            if 'bot' in locals() and bot:
                bot.quit()
            return False
        
    except Exception as e:
        logging.error(f"Critical error in start_bot: {str(e)}", exc_info=True)
        if 'bot' in locals() and bot:
            try:
                bot.quit()
            except:
                pass
        return False

def stop_bot():
    """Stop the WhatsApp bot"""
    global bot, bot_thread, scheduler_thread, is_bot_running
    
    try:
        is_bot_running = False
        if bot:
            bot.quit()
        if scheduler_thread:
            scheduler_thread.join()
        return True
    except Exception as e:
        logging.error(f"Error stopping bot: {str(e)}")
        return False

@app.route('/')
def index():
    """Render the main page"""
    config = load_config()
    return render_template('index.html',
                         recipients=config['recipients'],
                         templates=config['message_templates'],
                         scheduled_messages=config['scheduled_messages'],
                         message_history=config['message_history'],
                         stats=config['stats'])

@app.route('/start_bot', methods=['POST'])
def start_bot_route():
    """Start the WhatsApp bot"""
    success = start_bot()
    return jsonify({'success': success})

@app.route('/stop_bot', methods=['POST'])
def stop_bot_route():
    """Stop the WhatsApp bot"""
    success = stop_bot()
    return jsonify({'success': success})

@app.route('/add_recipient', methods=['POST'])
def add_recipient():
    """Add a new recipient"""
    try:
        # Get form data
        name = request.form.get('name')
        phone = request.form.get('phone')
        
        if not name or not phone:
            return jsonify({'status': 'error', 'message': 'Name and phone number are required'}), 400
            
        # Remove any non-digit characters from phone number
        phone = ''.join(filter(str.isdigit, phone))
        
        config = load_config()
        
        # Check if recipient already exists
        if any(r['phone'] == phone for r in config['recipients']):
            return jsonify({'status': 'error', 'message': 'Recipient with this phone number already exists'}), 400
        
        # Generate unique ID
        recipient_id = str(len(config['recipients']) + 1)
        
        new_recipient = {
            'id': recipient_id,
            'name': name,
            'phone': phone
        }
        
        config['recipients'].append(new_recipient)
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'message': 'Recipient added successfully',
            'recipient': new_recipient
        })
        
    except Exception as e:
        logging.error(f"Error adding recipient: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to add recipient: {str(e)}'
        }), 500

@app.route('/add_template', methods=['POST'])
def add_template():
    """Add a new message template"""
    try:
        # Get form data
        name = request.form.get('name')
        content = request.form.get('content')
        
        if not name or not content:
            return jsonify({'status': 'error', 'message': 'Template name and content are required'}), 400
            
        config = load_config()
        
        # Check if template with this name already exists
        if any(t['name'].lower() == name.lower() for t in config['message_templates']):
            return jsonify({'status': 'error', 'message': 'A template with this name already exists'}), 400
        
        # Generate unique ID
        template_id = str(len(config['message_templates']) + 1)
        
        new_template = {
            'id': template_id,
            'name': name,
            'content': content
        }
        
        config['message_templates'].append(new_template)
        save_config(config)
        
        return jsonify({
            'status': 'success',
            'message': 'Template added successfully',
            'template': new_template
        })
        
    except Exception as e:
        logging.error(f"Error adding template: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to add template: {str(e)}'
        }), 500

@app.route('/schedule_message', methods=['POST'])
def schedule_message():
    """Schedule a new message"""
    try:
        # Get form data
        schedule_type = request.form.get('schedule_type')
        recipient_id = request.form.get('recipient')
        template_id = request.form.get('template')
        time = request.form.get('time')
        
        # Validate required fields
        if not all([schedule_type, recipient_id, template_id, time]):
            return jsonify({
                'status': 'error',
                'message': 'All fields are required'
            }), 400
        
        config = load_config()
        
        # Validate recipient and template
        recipient = next((r for r in config['recipients'] if r['id'] == recipient_id), None)
        template = next((t for t in config['message_templates'] if t['id'] == template_id), None)
        
        if not recipient:
            return jsonify({
                'status': 'error',
                'message': 'Selected recipient not found'
            }), 400
            
        if not template:
            return jsonify({
                'status': 'error',
                'message': 'Selected template not found'
            }), 400
        
        # Prepare schedule data based on type
        schedule_data = {
            'type': schedule_type,
            'time': time,
            'active': True
        }
        
        # Add type-specific fields
        if schedule_type == 'weekly':
            days = request.form.getlist('days[]')
            if not days:
                return jsonify({
                    'status': 'error',
                    'message': 'Please select at least one day for weekly schedule'
                }), 400
            schedule_data['days'] = days
        elif schedule_type == 'monthly':
            day_of_month = request.form.get('day_of_month')
            if not day_of_month:
                return jsonify({
                    'status': 'error',
                    'message': 'Please select a day of the month'
                }), 400
            schedule_data['day'] = day_of_month
        elif schedule_type == 'one_time':
            date = request.form.get('date')
            if not date:
                return jsonify({
                    'status': 'error',
                    'message': 'Please select a date for one-time schedule'
                }), 400
            schedule_data['date'] = date
        
        # Generate unique ID
        new_id = str(len(config['scheduled_messages']) + 1)
        
        # Log the schedule details
        logging.info(f"[SCHEDULER] Creating new schedule - ID: {new_id}, Type: {schedule_type}, Time: {time}")
        
        # Create new schedule
        new_schedule = {
            'id': new_id,
            'recipient_id': recipient_id,
            'template_id': template_id,
            **schedule_data
        }
        
        config['scheduled_messages'].append(new_schedule)
        save_config(config)
        
        # If bot is running, set up the schedule immediately
        if is_bot_running and 'scheduler' in globals():
            setup_scheduled_message(new_schedule, recipient, template)
        
        return jsonify({
            'status': 'success',
            'message': 'Message scheduled successfully',
            'schedule': new_schedule
        })
        
    except Exception as e:
        logging.error(f"Error scheduling message: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Failed to schedule message: {str(e)}'
        }), 500

@app.route('/send_message', methods=['POST'])
def send_message():
    """Send a message immediately"""
    try:
        data = request.json
        config = load_config()
        
        recipient = next((r for r in config['recipients'] if r['id'] == data['recipient_id']), None)
        template = next((t for t in config['message_templates'] if t['id'] == data['template_id']), None)
        
        if not recipient or not template:
            return jsonify({'success': False, 'error': 'Invalid recipient or template'})
        
        message = template['content'].format(name=recipient['name'])
        success = send_whatsapp_message(recipient['phone'], message)
        
        status = 'success' if success else 'error'
        add_to_history(recipient['name'], message, status)
        update_stats(status)
        
        return jsonify({'success': success})
    except Exception as e:
        logging.error(f"Error sending message: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    try:
        # Start the scheduler in a separate thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Run Flask in the main thread
        logging.info("Starting Flask server on http://127.0.0.1:5000")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
        
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        cleanup()
