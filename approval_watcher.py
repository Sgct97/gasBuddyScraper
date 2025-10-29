#!/usr/bin/env python3
"""
Approval Watcher - Monitors inbox for approval replies
Checks Gmail inbox for replies containing "APPROVED" or "OK"
Runs continuously, checking every 60 seconds
"""
import imaplib
import email
from email.header import decode_header
import time
import os
import sys
import subprocess
from datetime import datetime

class EmailConfig:
    """Load email configuration"""
    def __init__(self, config_file='/opt/gasbuddy/email_config.txt'):
        # For IMAP, we need Gmail credentials (not SendGrid)
        # These should be added to the config file
        self.imap_email = None
        self.imap_password = None  # Gmail app password for IMAP
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        if key == 'imap_email':
                            self.imap_email = value
                        elif key == 'imap_password':
                            self.imap_password = value

def log_message(message):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    log_file = '/opt/gasbuddy/logs/approval_watcher.log'
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a') as f:
        f.write(log_line + '\n')

def get_pending_reviews():
    """Get list of merge IDs waiting for approval"""
    pending = []
    review_log = '/opt/gasbuddy/logs/review_requests.log'
    approval_log = '/opt/gasbuddy/logs/approvals.log'
    
    if not os.path.exists(review_log):
        return pending
    
    # Get all sent reviews
    sent_reviews = set()
    with open(review_log, 'r') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) >= 5 and parts[4] == 'SENT':
                sent_reviews.add(parts[1])  # merge_id
    
    # Remove already approved
    if os.path.exists(approval_log):
        with open(approval_log, 'r') as f:
            for line in f:
                parts = line.strip().split('|')
                if len(parts) >= 2:
                    merge_id = parts[1]
                    if merge_id in sent_reviews:
                        sent_reviews.remove(merge_id)
    
    return list(sent_reviews)

def check_for_approval(config):
    """
    Check Gmail inbox AND Sent Mail for approval emails
    Gmail stores replies in Sent Mail folder, not Inbox!
    
    Returns:
        List of approved merge_ids
    """
    if not config.imap_email or not config.imap_password:
        log_message("⚠️  IMAP credentials not configured")
        return []
    
    try:
        # Connect to Gmail IMAP
        log_message("📧 Connecting to Gmail IMAP...")
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        log_message("   ✅ SSL connection established")
        
        mail.login(config.imap_email, config.imap_password)
        log_message("   ✅ Login successful")
        
        # CHECK SENT MAIL FOLDER (where replies are stored!)
        mail.select('"[Gmail]/Sent Mail"')
        log_message("   ✅ Sent Mail selected")
        
        # Search for emails TO info@aiearlybird.com (approval replies)
        from datetime import datetime, timedelta
        since_date = (datetime.now() - timedelta(hours=24)).strftime("%d-%b-%Y")
        log_message(f"   🔍 Searching Sent Mail for replies TO info@aiearlybird.com since: {since_date}")
        status, messages = mail.search(None, f'(TO info@aiearlybird.com SINCE {since_date})')
        log_message(f"   📬 Search status: {status}, Found: {len(messages[0].split()) if messages[0] else 0} emails")
        
        if status != 'OK' or not messages[0]:
            mail.logout()
            return []
        
        approved_merges = []
        email_ids = messages[0].split()
        
        # Check ALL emails sent to info@aiearlybird.com
        log_message(f"   📨 Checking {len(email_ids)} sent emails for approval...")
        emails_checked = 0
        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                if status != 'OK':
                    continue
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get subject, from, and body
                        subject = str(msg.get('subject', ''))
                        from_addr = str(msg.get('from', ''))
                        
                        emails_checked += 1
                        if emails_checked <= 10:  # Log first 10 for debugging
                            log_message(f"      Email {emails_checked}: From={from_addr[:40]}, Subject={subject[:60]}")
                        
                        # Get body (text and HTML)
                        body_text = ''
                        body_html = ''
                        
                        if msg.is_multipart():
                            for part in msg.walk():
                                ctype = part.get_content_type()
                                if ctype == 'text/plain':
                                    try:
                                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    except:
                                        pass
                                elif ctype == 'text/html':
                                    try:
                                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    except:
                                        pass
                        else:
                            try:
                                body_text = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except:
                                pass
                        
                        # Check if body starts with "OK" (approval reply)
                        body_clean = body_text.strip()
                        
                        # Look for approval keywords at the START of the body
                        has_approval = (body_clean.upper().startswith('OK') or
                                       body_clean.upper().startswith('APPROVED') or
                                       body_clean.upper().startswith('APPROVE'))
                        
                        # Check if this references GasBuddy (reply to review email)
                        subject_upper = subject.upper()
                        has_gasbuddy_ref = ('GASBUDDY' in subject_upper or 
                                           'GAS BUDDY' in subject_upper or
                                           'RE:' in subject_upper)
                        
                        if emails_checked <= 10:
                            log_message(f"         Subject: {subject[:80]}")
                            log_message(f"         Body start: {body_clean[:50]}")
                            log_message(f"         HasApproval={has_approval}, HasGasBuddy={has_gasbuddy_ref}")
                        
                        # Must have approval keyword AND reference GasBuddy
                        if has_approval and has_gasbuddy_ref:
                            # Found a genuine approval reply from user!
                            pending = get_pending_reviews()
                            if pending:
                                # Approve the most recent pending
                                merge_id = pending[-1]
                                log_message(f"✅ Found approval email FROM USER!")
                                log_message(f"   From: {from_addr[:50]}")
                                log_message(f"   Subject: {subject[:80]}")
                                log_message(f"   Body snippet: {body_text[:100]}")
                                log_message(f"   Approving: {merge_id}")
                                
                                # Only approve once
                                if merge_id not in approved_merges:
                                    approved_merges.append(merge_id)
            
            except Exception as e:
                log_message(f"⚠️  Error processing email: {e}")
                continue
        
        mail.logout()
        return approved_merges
    
    except Exception as e:
        log_message(f"❌ Failed to check inbox: {e}")
        return []

def log_approval(merge_id):
    """Log approval event"""
    approval_log = '/opt/gasbuddy/logs/approvals.log'
    os.makedirs(os.path.dirname(approval_log), exist_ok=True)
    with open(approval_log, 'a') as f:
        f.write(f"{datetime.now().isoformat()}|{merge_id}|APPROVED\n")

def trigger_client_delivery(merge_id):
    """Trigger client delivery after delay"""
    try:
        log_message(f"🚀 Triggering client delivery for {merge_id}")
        
        # Call send_to_client.py script
        result = subprocess.run(
            ['python3', '/opt/gasbuddy/send_to_client.py', merge_id],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            log_message(f"✅ Client delivery completed successfully")
            return True
        else:
            log_message(f"❌ Client delivery failed")
            log_message(f"   Error: {result.stderr}")
            return False
    
    except Exception as e:
        log_message(f"❌ Failed to trigger client delivery: {e}")
        return False

def main():
    """Main approval watcher loop"""
    log_message("=" * 60)
    log_message("👀 APPROVAL WATCHER STARTED")
    log_message("=" * 60)
    log_message("Monitoring inbox for approval emails...")
    log_message("Check interval: 60 seconds")
    log_message("")
    
    config = EmailConfig()
    
    if not config.imap_email or not config.imap_password:
        log_message("❌ IMAP credentials not configured!")
        log_message("   Add to /opt/gasbuddy/email_config.txt:")
        log_message("   imap_email=your_email@gmail.com")
        log_message("   imap_password=your_gmail_app_password")
        sys.exit(1)
    
    check_count = 0
    
    while True:
        try:
            check_count += 1
            
            # Check for pending reviews
            pending = get_pending_reviews()
            
            if pending:
                log_message(f"📋 Pending reviews: {len(pending)}")
                for merge_id in pending:
                    log_message(f"   - {merge_id}")
                
                # Check inbox for approvals
                log_message("📬 Checking inbox...")
                approved = check_for_approval(config)
                
                if approved:
                    for merge_id in approved:
                        log_message(f"")
                        log_message(f"🎉 APPROVAL RECEIVED: {merge_id}")
                        log_message(f"")
                        
                        # Log approval
                        log_approval(merge_id)
                        
                        # Trigger client delivery
                        trigger_client_delivery(merge_id)
                else:
                    log_message("   No approvals found")
            else:
                if check_count % 10 == 1:  # Log every 10 checks
                    log_message("✓ No pending reviews")
            
            # Wait before next check
            time.sleep(60)
        
        except KeyboardInterrupt:
            log_message("")
            log_message("👋 Approval watcher stopped by user")
            sys.exit(0)
        
        except Exception as e:
            log_message(f"❌ Error in main loop: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
