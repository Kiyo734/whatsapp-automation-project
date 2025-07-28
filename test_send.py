from whatsapp_auto import WhatsAppBot
import time
import sys
import os

def clear_screen():
    """Clear the console screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    """Print a nice banner"""
    banner = """
    ╔══════════════════════════════════════════╗
    ║      WHATSAPP MESSAGE SENDER - BOT       ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)

def wait_for_enter(prompt="\nPress Enter to continue..."):
    """Wait for user to press Enter"""
    input(prompt)

def main():
    clear_screen()
    print_banner()
    
    print("Initializing bot...")
    bot = None
    
    try:
        bot = WhatsAppBot()
        if not hasattr(bot, 'start') or not callable(bot.start):
            print("❌ Error: Invalid WhatsAppBot class. Missing start() method.")
            return
            
        print("Starting WebDriver...")
        if not bot.start():
            print("❌ Failed to start the bot. Please check the logs.")
            wait_for_enter()
            return
            
        clear_screen()
        print_banner()
        print("✅ WebDriver started successfully!")
        print("\n" + "="*50)
        print("  IMPORTANT INSTRUCTIONS")
        print("="*50)
        print("1. A new Edge window should open with WhatsApp Web")
        print("2. If prompted, scan the QR code with your phone")
        print("3. Wait for the chat list to load")
        print("4. DO NOT close the browser window")
        print("5. Keep the browser window visible and active")
        print("="*50)
        wait_for_enter("\nPress Enter when WhatsApp Web is fully loaded...")
        
        while True:
            clear_screen()
            print_banner()
            print("📱 WHATSAPP MESSAGE SENDER")
            print("-"*50)
            print("1. Make sure WhatsApp Web is logged in")
            print("2. Enter phone number with country code (no + or spaces)")
            print("   For Indian numbers: 91XXXXXXXXXX (e.g., 917770045132)")
            print("   For US numbers: 1XXXXXXXXXX (e.g., 14151234567)")
            print("\nType 'exit' to quit or 'restart' to reload WhatsApp Web")
            print("-"*50)
        
            try:
                phone = input("\nEnter phone number (with country code, no +): ").strip()
                
                if phone.lower() == 'exit':
                    print("\nExiting...")
                    break
                    
                if phone.lower() == 'restart':
                    print("\nReloading WhatsApp Web...")
                    bot.driver.get("https://web.whatsapp.com")
                    wait_for_enter("Press Enter after WhatsApp Web has reloaded...")
                    continue
                
                # Clean the phone number - remove all non-digit characters
                phone = ''.join(filter(str.isdigit, phone))
                
                if not phone:
                    print("❌ Please enter a valid phone number")
                    time.sleep(2)
                    continue
                    
                # Handle different number formats
                if phone.startswith('91') and len(phone) == 12:  # Already in correct format
                    print(f"ℹ️  Using number with country code: +{phone}")
                elif phone.startswith('0'):  # Starts with 0 (local number)
                    phone = '91' + phone[1:]
                    print(f"ℹ️  Replaced leading 0 with country code: +{phone}")
                elif len(phone) == 10:  # Local number without country code
                    phone = '91' + phone
                    print(f"ℹ️  Added country code: +{phone}")
                else:
                    print(f"ℹ️  Using number as provided: +{phone}")
                    
                # Double check the number doesn't have any unexpected prefixes
                if phone.startswith('2091'):
                    phone = phone[2:]  # Remove the '20' if it was added
                    print(f"ℹ️  Removed incorrect prefix, using: +{phone}")
                    
                print(f"Final phone number that will be used: +{phone}")
                
                message = input("\nEnter message (press Enter for default): ").strip()
                if not message:
                    message = "Hello from WhatsApp Bot!"
                    print(f"Using default message: {message}")
                
                print(f"\n📱 Sending message to +{phone}...")
                print("-"*50)
                
                if not hasattr(bot, 'send_message_to_number') or not callable(bot.send_message_to_number):
                    print("❌ Error: send_message_to_number method not found")
                    wait_for_enter()
                    continue
                    
                # Debug: Print the phone number and its type
                print(f"📞 Phone number: +{phone}")
                print(f"📝 Message: {message}")
                
                # Ensure phone is a string and doesn't contain any extra characters
                phone = str(phone).strip()
                if not phone.isdigit():
                    print(f"❌ Invalid phone number format: {phone}")
                    wait_for_enter()
                    continue
                    
                print("\n🔍 Checking WhatsApp Web connection...")
                
                # Try sending the message with the cleaned phone number
                print("\n🚀 Sending message...")
                start_time = time.time()
                result = bot.send_message_to_number(phone, message)
                elapsed = time.time() - start_time
                
                print("\n" + "="*50)
                if result:
                    print(f"✅ Message sent successfully in {elapsed:.1f} seconds!")
                else:
                    print(f"❌ Message may not have been sent. Check the browser window.")
                print("="*50)
                
                # Add a small delay before next operation
                time.sleep(2)
                
                wait_for_enter("\nPress Enter to send another message or type 'exit' to quit...")
                
            except KeyboardInterrupt:
                print("\n🛑 Operation cancelled by user.")
                break
            except Exception as e:
                print(f"\n❌ An error occurred: {str(e)}")
                print("Please check the browser window and try again.")
                wait_for_enter()
    
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if bot and hasattr(bot, 'driver') and bot.driver:
            print("\n🧹 Cleaning up...")
            try:
                bot.driver.quit()
                print("✅ Browser closed.")
            except Exception as e:
                print(f"❌ Error closing browser: {str(e)}")
        print("\n👋 Goodbye!")
        time.sleep(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ A critical error occurred: {str(e)}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
