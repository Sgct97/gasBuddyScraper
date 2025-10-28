#!/usr/bin/env python3
"""
Email utility module for GasBuddy scraper automation
Handles sending and receiving emails via Gmail SMTP/IMAP
"""
import smtplib
import imaplib
import email
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os
from datetime import datetime

class EmailConfig:
    """Email configuration - will be loaded from secure config file"""
    def __init__(self, config_file='/opt/gasbuddy/email_config.txt'):
        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587
        self.imap_server = 'imap.gmail.com'
        self.imap_port = 993
        
        # Load credentials from config file
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == 'email':
                            self.email_address = value
                        elif key == 'app_password':
                            self.app_password = value
                        elif key == 'client_email':
                            self.client_email = value
        else:
            # Defaults - will be overwritten during setup
            self.email_address = None
            self.app_password = None
            self.client_email = None

def send_email(to_address, subject, body_html, attachment_path=None, config=None):
    """
    Send an email via Gmail SMTP
    
    Args:
        to_address: Recipient email
        subject: Email subject
        body_html: HTML body content
        attachment_path: Optional path to file to attach
        config: EmailConfig object (if None, will create one)
    
    Returns:
        True if successful, False otherwise
    """
    if config is None:
        config = EmailConfig()
    
    if not config.email_address or not config.app_password:
        print("❌ Email not configured! Run setup_email.py first.")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = config.email_address
        msg['To'] = to_address
        msg['Subject'] = subject
        msg['Date'] = email.utils.formatdate(localtime=True)
        
        # Attach HTML body
        msg.attach(MIMEText(body_html, 'html'))
        
        # Attach file if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{os.path.basename(attachment_path)}"'
            )
            msg.attach(part)
        
        # Send via SMTP
        with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
            server.starttls()
            server.login(config.email_address, config.app_password)
            server.send_message(msg)
        
        return True
    
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def check_for_approval(run_id, config=None):
    """
    Check inbox for approval reply to review email
    
    Args:
        run_id: The RUN_ID to check approval for
        config: EmailConfig object (if None, will create one)
    
    Returns:
        True if approved, False otherwise
    """
    if config is None:
        config = EmailConfig()
    
    if not config.email_address or not config.app_password:
        print("❌ Email not configured!")
        return False
    
    try:
        # Connect to IMAP
        mail = imaplib.IMAP4_SSL(config.imap_server, config.imap_port)
        mail.login(config.email_address, config.app_password)
        mail.select('INBOX')
        
        # Search for emails with run_id in subject
        search_subject = f'GasBuddy Scrape'
        status, messages = mail.search(None, f'(SUBJECT "{search_subject}")')
        
        if status != 'OK':
            mail.logout()
            return False
        
        # Check recent emails for approval
        email_ids = messages[0].split()
        for email_id in email_ids[-10:]:  # Check last 10 matching emails
            status, msg_data = mail.fetch(email_id, '(RFC822)')
            if status != 'OK':
                continue
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Check if this is about our run_id
                    subject = msg.get('subject', '')
                    body = ''
                    
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode()
                                break
                    else:
                        body = msg.get_payload(decode=True).decode()
                    
                    # Check for approval keywords
                    combined = (subject + ' ' + body).upper()
                    if run_id in subject and ('APPROVED' in combined or 'OK' in combined or 'APPROVE' in combined):
                        mail.logout()
                        return True
        
        mail.logout()
        return False
    
    except Exception as e:
        print(f"❌ Failed to check inbox: {e}")
        return False

