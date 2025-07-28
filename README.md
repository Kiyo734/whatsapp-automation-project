# WhatsApp Automation System

A powerful WhatsApp automation system with a modern web interface, message scheduling, and comprehensive message management.

![WhatsApp Automation System](screenshots/dashboard.png.jpeg)

## Features

### Message Management
- **Template System**: Create and manage message templates with variable support
- **Recipient Management**: Organize contacts with custom names and phone numbers
- **Message History**: Track all sent messages with status indicators
- **Statistics Dashboard**: Monitor message success rates and delivery status

### Smart Scheduling
- **One-Time Messages**: Schedule messages for specific dates and times
- **Recurring Messages**: Set up daily, weekly, or monthly recurring messages
- **Schedule Management**: View, edit, and delete scheduled messages
- **Active/Inactive Toggle**: Enable or disable schedules without deletion

### System Features
- **Dark Theme UI**: Modern, eye-friendly interface
- **Responsive Design**: Works on desktop and mobile devices
- **Real-time Status Updates**: Monitor message delivery in real-time
- **Error Handling**: Robust error handling with detailed logging

### Technical Highlights
- **Selenium Integration**: Automated WhatsApp Web interaction
- **Flask Backend**: Fast and reliable Python web framework
- **Schedule Library**: Precise timing for scheduled messages
- **Edge WebDriver**: Modern browser automation

## Tech Stack

- **Backend**: Python, Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Automation**: Selenium, Edge WebDriver
- **Scheduling**: Python Schedule library
- **Data Storage**: JSON-based configuration

## Installation

### Prerequisites
- Python 3.8 or higher
- Microsoft Edge browser
- Git

### Setup Steps



2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the web interface**
   Open your browser and navigate to `http://localhost:5000`

## Usage Guide

### Starting the Bot
1. Click the "Start Bot" button in the dashboard
2. Scan the QR code with your WhatsApp mobile app
3. Wait for the connection to establish

### Adding Recipients
1. Navigate to the "Contacts" tab
2. Click "Add Recipient"
3. Enter the recipient's name and phone number
4. Click "Save"

### Creating Templates
1. Navigate to the "Templates" tab
2. Click "Add Template"
3. Enter a template name and content
4. Use `{name}` as a placeholder for recipient names
5. Click "Save"

### Scheduling Messages
1. Navigate to the "Schedule" tab
2. Click "Schedule Message"
3. Select a recipient and template
4. Choose a schedule type (one-time, daily, weekly, monthly)
5. Set the date and time
6. Click "Schedule"

### Sending Messages
1. Navigate to the "Messages" tab
2. Select a recipient and template
3. Click "Send Message"

## Configuration

The system uses a `config.json` file to store:
- Recipients
- Message templates
- Scheduled messages
- Message history
- Statistics

This file is automatically created when you first run the application.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Selenium](https://www.selenium.dev/) for web automation
- [Flask](https://flask.palletsprojects.com/) for the web framework
- [Bootstrap](https://getbootstrap.com/) for the UI components
- [Schedule](https://schedule.readthedocs.io/) for task scheduling

## Support

If you encounter any issues or have questions, please open an issue in the GitHub repository.

---

**Note**: This project is for educational purposes only. Please use responsibly and in accordance with WhatsApp's terms of service. 
