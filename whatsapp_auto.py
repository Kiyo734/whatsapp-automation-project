import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import subprocess
import os
from urllib.parse import quote
from datetime import datetime
from webdriver_manager.microsoft import EdgeChromiumDriverManager

class WhatsAppBot:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.is_running = False
        
    def kill_edge_processes(self):
        """Kill any existing Edge processes"""
        try:
            subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Warning: Could not kill Edge processes: {str(e)}")
    
    def setup_driver(self):
        """Setup the Edge WebDriver with existing profile"""
        try:
            print("🔧 Setting up Edge WebDriver...")
            self.kill_edge_processes()
            
            # Configure Edge options
            options = Options()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument('--disable-web-security')
            options.add_argument('--allow-running-insecure-content')
            options.add_argument("--start-maximized")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-site-isolation-trials")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0")
            
            # Set up user data directory for persistent session
            edge_profile = os.path.join(os.getcwd(), "whatsapp_bot_profile")
            if not os.path.exists(edge_profile):
                os.makedirs(edge_profile)
            options.add_argument(f"user-data-dir={edge_profile}")
            
            # Initialize the WebDriver
            service = Service()
            self.driver = webdriver.Edge(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 60)
            
            # Set page load timeout
            self.driver.set_page_load_timeout(60)
            
            print("✅ WebDriver setup complete")
            return self.driver
            
        except Exception as e:
            error_msg = f"❌ Error setting up Edge driver: {str(e)}"
            print(error_msg)
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as quit_error:
                    print(f"⚠️  Error while quitting driver: {str(quit_error)}")
            self.driver = None
            raise Exception(error_msg)
    
    def login_to_whatsapp(self):
        """Open WhatsApp Web with existing session"""
        try:
            print("🔗 Connecting to WhatsApp Web...")
            self.driver.get("https://web.whatsapp.com")
            time.sleep(5)  # Initial load time
            
            print("⏳ Waiting for WhatsApp Web to load...")
            # Wait for either the chat list (logged in) or QR code (needs login)
            initial_load = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"], div[data-testid="qrcode"]'))
            )
            
            # Check if already logged in
            textbox = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="textbox"]')
            if textbox:
                print("✅ Successfully connected to existing WhatsApp Web session!")
                return True
                
            # If not logged in, wait for QR code scan
            qr_code = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-testid="qrcode"]'))
            )
            if qr_code:
                print("📱 Please scan the QR code with your phone to log in to WhatsApp Web...")
                # Wait for login to complete
                chat_list = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="textbox"]'))
                )
                if chat_list:
                    print("✅ Successfully logged in to WhatsApp Web!")
                    return True
            
            raise Exception("Could not detect login status")
                
        except Exception as e:
            error_msg = f"❌ Error connecting to WhatsApp Web: {str(e)}"
            print(error_msg)
            # Take screenshot for debugging
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(os.getcwd(), f"login_error_{timestamp}.png")
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Screenshot saved to: {screenshot_path}")
            except Exception as screenshot_error:
                print(f"⚠️  Failed to take screenshot: {str(screenshot_error)}")
            raise Exception(error_msg)

    def send_message_to_number(self, phone_number, message):
        """Send a message to a specific phone number
        
        Args:
            phone_number (str): Phone number in international format (e.g., 919335669767)
            message (str): Message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            if not self.driver or not self.is_running:
                print("❌ Bot is not initialized or not running")
                return False
            
            # Clean the phone number - remove all non-digit characters
            phone_number = ''.join(filter(str.isdigit, str(phone_number)))
            
            # Ensure the number is in international format
            if len(phone_number) == 10:  # If only local number provided, assume India (+91)
                phone_number = '91' + phone_number
                print(f"ℹ️  Added country code: +{phone_number}")
            elif phone_number.startswith('0'):  # If starts with 0, replace with country code
                phone_number = '91' + phone_number[1:]
                print(f"ℹ️  Replaced leading 0 with country code: +{phone_number}")
            
            print(f"📱 Sending message to +{phone_number}")
            print(f"📝 Message: {message[:50]}{'...' if len(message) > 50 else ''}")
            
            # Construct the WhatsApp URL with the phone number and message
            encoded_message = quote(message)
            whatsapp_url = f"https://web.whatsapp.com/send?phone={phone_number}&text={encoded_message}"
            
            print(f"🌐 Opening chat URL: {whatsapp_url}")
            self.driver.get(whatsapp_url)
            
            try:
                # Wait for the chat to load - check for input box or error message
                WebDriverWait(self.driver, 30).until(
                    lambda d: d.find_elements(By.XPATH, "//div[@role='textbox']") or \
                             d.find_elements(By.XPATH, "//div[contains(text(),'Phone number shared via url is invalid')]")
                )
                
                # Check if we got an error message
                error_elements = self.driver.find_elements(By.XPATH, "//div[contains(text(),'Phone number shared via url is invalid')]")
                if error_elements:
                    print("❌ Error: Invalid phone number format")
                    return False
                
                # Wait for chat to be fully loaded and input box to be interactable
                print("⏳ Waiting for chat to load...")
                time.sleep(3)  # Give some time for chat to load
                
                # Try multiple approaches to find and interact with the input box
                input_box = None
                input_selectors = [
                    (By.XPATH, "//div[@title='Type a message' and @role='textbox']"),
                    (By.XPATH, "//div[@role='textbox']"),
                    (By.XPATH, "//div[@class='_3Uu1_']//div[@role='textbox']"),
                    (By.CSS_SELECTOR, "div[title='Type a message']")
                ]
                
                for selector in input_selectors:
                    try:
                        input_box = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable(selector)
                        )
                        if input_box:
                            break
                    except:
                        continue
                
                if not input_box:
                    raise Exception("Could not find message input box")
                
                print("📝 Typing message...")
                # Scroll the input box into view and click it
                self.driver.execute_script("arguments[0].scrollIntoView(true);", input_box)
                time.sleep(1)
                input_box.click()
                time.sleep(1)
                
                # Clear any existing text and type the message
                input_box.clear()
                for chunk in message.split("\n"):
                    input_box.send_keys(chunk)
                    ActionChains(self.driver).key_down(Keys.SHIFT).key_down(Keys.ENTER).key_up(Keys.SHIFT).key_up(Keys.ENTER).perform()
                    time.sleep(0.1)
                time.sleep(1)  # Wait for message to be typed
                
                # Find and click the send button
                print("🔄 Sending message...")
                send_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button//span[@data-icon='send']"))
                )
                send_button.click()
                
                # Verify the message was sent
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//span[@data-icon='msg-check']"))
                    )
                    print("✅ Message sent successfully!")
                    return True
                except:
                    print("⚠️ Message may have been sent, but couldn't verify delivery")
                    return True
                
            except Exception as e:
                print(f"❌ Error in chat interaction: {str(e)}")
                # Take a screenshot for debugging
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = os.path.join(os.getcwd(), f"error_{timestamp}.png")
                    self.driver.save_screenshot(screenshot_path)
                    print(f"📸 Screenshot saved to: {screenshot_path}")
                except Exception as screenshot_error:
                    print(f"❌ Failed to take screenshot: {str(screenshot_error)}")
                return False
                
        except Exception as e:
            print(f"❌ Error in send_message_to_number: {str(e)}")
            return False

    def start(self):
        """Start the WhatsApp bot"""
        try:
            print("🚀 Starting WhatsApp bot...")
            self.driver = self.setup_driver()
            self.wait = WebDriverWait(self.driver, 60)
            
            print("🔑 Logging in to WhatsApp Web...")
            if not self.login_to_whatsapp():
                return False
                
            self.is_running = True
            print("✅ Bot started successfully")
            return True
            
        except Exception as e:
            error_msg = f"❌ Error starting bot: {str(e)}"
            print(error_msg)
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as quit_error:
                    print(f"⚠️  Error while quitting driver: {str(quit_error)}")
            self.driver = None
            self.is_running = False
            return False
            
    def stop(self):
        """Stop the WhatsApp bot"""
        try:
            if self.driver:
                print("🛑 Stopping bot...")
                self.driver.quit()
                print("✅ Bot stopped successfully")
            self.is_running = False
            return True
        except Exception as e:
            print(f"❌ Error stopping bot: {str(e)}")
            return False
            
    def __del__(self):
        """Destructor to ensure resources are cleaned up"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

def main():
    bot = WhatsAppBot()
    bot.start()

if __name__ == "__main__":
    main()