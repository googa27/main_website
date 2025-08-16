import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.models.contact import ContactCreate
from app.core.config import settings

async def send_contact_email(contact: ContactCreate) -> bool:
    """Send contact form email"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USER
        msg['To'] = settings.SMTP_USER  # Send to yourself
        msg['Subject'] = f"Portfolio Contact: {contact.name}"
        
        # Email body
        body = f"""
        New contact form submission from your portfolio website:
        
        Name: {contact.name}
        Email: {contact.email}
        Message:
        {contact.message}
        
        ---
        Sent from cristobalcortinez.com
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        if settings.SMTP_TLS:
            server.starttls()
        
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        print(f"Email error: {e}")
        return False
