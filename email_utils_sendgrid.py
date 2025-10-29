#!/usr/bin/env python3
"""
Email utility module for GasBuddy scraper automation - SendGrid Version
Uses SendGrid Python library
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class EmailConfig:
    """Email configuration - will be loaded from secure config file"""
    def __init__(self, config_file='/opt/gasbuddy/email_config.txt'):
        # Load credentials from config file
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == 'email':
                            self.email_address = value
                        elif key == 'sendgrid_api_key':
                            self.sendgrid_api_key = value
                        elif key == 'client_email':
                            self.client_email = value
        else:
            # Defaults - will be overwritten during setup
            self.email_address = None
            self.sendgrid_api_key = None
            self.client_email = None

def send_email(to_address, subject, body_html, attachment_path=None, config=None):
    """
    Send an email via SendGrid API
    
    Args:
        to_address: Recipient email
        subject: Email subject
        body_html: HTML body content
        attachment_path: Optional path to file to attach (NOT IMPLEMENTED YET)
        config: EmailConfig object (if None, will create one)
    
    Returns:
        True if successful, False otherwise
    """
    if config is None:
        config = EmailConfig()
    
    if not config.email_address or not config.sendgrid_api_key:
        print("❌ SendGrid not configured!")
        return False
    
    try:
        message = Mail(
            from_email=config.email_address,
            to_emails=to_address,
            subject=subject,
            html_content=body_html
        )
        
        sg = SendGridAPIClient(config.sendgrid_api_key)
        response = sg.send(message)
        
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.body}")
        
        if response.status_code in [200, 202]:
            return True
        else:
            print(f"❌ SendGrid returned status: {response.status_code}")
            print(f"Headers: {response.headers}")
            return False
    
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        # Print more detailed error info
        if hasattr(e, 'body'):
            print(f"Error body: {e.body}")
        if hasattr(e, 'status_code'):
            print(f"Error status code: {e.status_code}")
        return False

def check_for_approval(run_id, config=None):
    """
    Check inbox for approval reply to review email
    NOTE: This requires IMAP which still uses Gmail credentials
    For now, this is placeholder - we'll implement webhook-based approval later
    
    Args:
        run_id: The RUN_ID to check approval for
        config: EmailConfig object (if None, will create one)
    
    Returns:
        True if approved, False otherwise
    """
    print("⚠️  IMAP approval checking not implemented with SendGrid yet")
    print("   Use manual approval for now")
    return False
