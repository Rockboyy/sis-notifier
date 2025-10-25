import requests
from bs4 import BeautifulSoup
from twilio.rest import Client
import json
import os

# Credentials
USERNAME = os.environ.get('FCPS_USERNAME', 'YOUR_USERNAME')
PASSWORD = os.environ.get('FCPS_PASSWORD', 'YOUR_PASSWORD')

# Twilio
TWILIO_SID = os.environ.get('TWILIO_SID', 'ACdbb1fb8fbe404c51d93c13468e3d5271')
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN', 'YOUR_AUTH_TOKEN')
TWILIO_FROM = 'whatsapp:+14155238886'
TWILIO_TO = os.environ.get('TWILIO_TO', 'whatsapp:+17034537430')

# URLs
LOGIN_URL = 'https://sisstudent.fcps.edu/SVUE/PXP2_Login_Student_OVR.aspx?regenerateSessionId=true'
GRADEBOOK_URL = 'https://sisstudent.fcps.edu/SVUE/PXP2_Gradebook.aspx'

GRADES_FILE = 'previous_grades.json'

def login_and_get_grades():
    """Login and fetch current grades"""
    session = requests.Session()
    
    # Step 1: GET login page for viewstate
    response = session.get(LOGIN_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    viewstate = soup.find('input', {'name': '__VIEWSTATE'})['value']
    eventvalidation = soup.find('input', {'name': '__EVENTVALIDATION'})['value']
    viewstate_generator = soup.find('input', {'name': '__VIEWSTATEGENERATOR'})['value']
    
    # Step 2: POST login
    login_data = {
        '__VIEWSTATE': viewstate,
        '__EVENTVALIDATION': eventvalidation,
        '__VIEWSTATEGENERATOR': viewstate_generator,
        'ctl00$MainContent$username': USERNAME,
        'ctl00$MainContent$password': PASSWORD,
    }
    
    session.post(LOGIN_URL, data=login_data)
    
    # Step 3: GET gradebook
    response = session.get(GRADEBOOK_URL)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Step 4: Extract all <span class="score"> values
    scores = soup.find_all('span', class_='score')
    grades = [score.get_text(strip=True) for score in scores]
    
    return grades

def load_previous_grades():
    """Load previous grades from file"""
    if os.path.exists(GRADES_FILE):
        with open(GRADES_FILE, 'r') as f:
            return json.load(f)
    return None

def save_grades(grades):
    """Save current grades to file"""
    with open(GRADES_FILE, 'w') as f:
        json.dump(grades, f)

def send_whatsapp(message_text):
    """Send WhatsApp notification via Twilio"""
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        message = client.messages.create(
            from_=TWILIO_FROM,
            body=message_text,
            to=TWILIO_TO
        )
        print(f"✓ WhatsApp sent: {message.sid}")
    except Exception as e:
        print(f"❌ Failed to send WhatsApp: {e}")

def main():
    print("Checking grades...")
    
    # Get current grades
    current_grades = login_and_get_grades()
    print(f"Found {len(current_grades)} grades: {current_grades}")
    
    # Load previous grades
    previous_grades = load_previous_grades()
    
    # Check for changes
    if previous_grades is None:
        print("First run - saving initial grades")
        save_grades(current_grades)
    elif current_grades != previous_grades:
        print("🔔 GRADES CHANGED!")
        
        # Build notification message
        message = "📚 Grade Update!\n\n"
        for i, (old, new) in enumerate(zip(previous_grades, current_grades), 1):
            if old != new:
                message += f"Class {i}: {old} → {new}\n"
        
        # Send notification
        send_whatsapp(message)
        
        # Save new grades
        save_grades(current_grades)
    else:
        print("No changes detected")

if __name__ == "__main__":
    main()
