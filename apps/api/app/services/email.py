import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any

from ..core.config import settings
from ..models.contact import ContactCreate

def send_email(contact: ContactCreate) -> bool:
    """
    Send an email with the contact form data.
    
    Args:
        contact: The contact form data.
        
    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.EMAILS_FROM_EMAIL
        msg['To'] = settings.EMAILS_TO_EMAIL
        msg['Subject'] = f"New Contact Form Submission: {contact.subject}"
        
        # Create email body
        body = f"""
        New contact form submission:
        
        Name: {contact.name}
        Email: {contact.email}
        Subject: {contact.subject}
        
        Message:
        {contact.message}
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect to SMTP server and send email
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
