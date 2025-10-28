#!/usr/bin/env python3
"""
Email Configuration Setup
Interactive script to configure Gmail SMTP/IMAP for automation
Securely stores credentials in email_config.txt with proper permissions
"""
import os
import sys
import subprocess
from getpass import getpass

CONFIG_FILE = '/opt/gasbuddy/email_config.txt'

def print_banner():
    """Print setup banner"""
    print("="*70)
    print("📧 GASBUDDY EMAIL CONFIGURATION SETUP")
    print("="*70)
    print()

def print_instructions():
    """Print Gmail app password instructions"""
    print("📋 Gmail App Password Setup Instructions:")
    print()
    print("1. Go to your Google Account: https://myaccount.google.com/")
    print("2. Navigate to Security → 2-Step Verification (must be enabled)")
    print("3. Scroll to bottom → App passwords")
    print("4. Select app: 'Mail' and device: 'Other (Custom name)'")
    print("5. Name it 'GasBuddy Scraper' and click Generate")
    print("6. Copy the 16-character password (no spaces)")
    print()
    print("⚠️  Note: You need to have 2-Step Verification enabled first!")
    print()

def test_email_connection(email, app_password):
    """Test SMTP and IMAP connection"""
    print("\n🔍 Testing email connection...")
    
    try:
        import smtplib
        import imaplib
        
        # Test SMTP
        print("  Testing SMTP (sending)...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(email, app_password)
        print("  ✅ SMTP connection successful")
        
        # Test IMAP
        print("  Testing IMAP (receiving)...")
        mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        mail.login(email, app_password)
        mail.logout()
        print("  ✅ IMAP connection successful")
        
        return True
    
    except Exception as e:
        print(f"  ❌ Connection failed: {e}")
        print()
        print("Common issues:")
        print("  - App password not generated or incorrect")
        print("  - 2-Step Verification not enabled")
        print("  - Gmail account security settings blocking access")
        return False

def save_config(email, app_password, client_email):
    """Save configuration to file with secure permissions"""
    
    # Create config content
    config_content = f"""# GasBuddy Email Configuration
# Generated: {subprocess.check_output('date', shell=True).decode().strip()}
email={email}
app_password={app_password}
client_email={client_email}
"""
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    
    # Write config
    with open(CONFIG_FILE, 'w') as f:
        f.write(config_content)
    
    # Set secure permissions (owner read/write only)
    os.chmod(CONFIG_FILE, 0o600)
    
    print(f"\n✅ Configuration saved to: {CONFIG_FILE}")
    print(f"✅ Permissions set to 600 (owner read/write only)")

def main():
    """Main setup flow"""
    print_banner()
    
    # Check if config already exists
    if os.path.exists(CONFIG_FILE):
        print(f"⚠️  Configuration file already exists: {CONFIG_FILE}")
        response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
        if response != 'yes':
            print("Setup cancelled.")
            sys.exit(0)
        print()
    
    # Show instructions
    print_instructions()
    input("Press Enter once you have your Gmail app password ready...")
    print()
    
    # Collect information
    print("📝 Enter your configuration details:")
    print()
    
    email = input("Your Gmail address: ").strip()
    if not email or '@' not in email:
        print("❌ Invalid email address")
        sys.exit(1)
    
    app_password = getpass("Gmail App Password (16 chars, input hidden): ").strip().replace(' ', '')
    if len(app_password) != 16:
        print(f"⚠️  Warning: App password should be 16 characters (you entered {len(app_password)})")
        response = input("Continue anyway? (yes/no): ").strip().lower()
        if response != 'yes':
            sys.exit(1)
    
    client_email = input("Client's email address: ").strip()
    if not client_email or '@' not in client_email:
        print("❌ Invalid client email address")
        sys.exit(1)
    
    # Test connection
    if not test_email_connection(email, app_password):
        print("\n❌ Email configuration failed validation")
        print("Please check your credentials and try again")
        sys.exit(1)
    
    # Save configuration
    save_config(email, app_password, client_email)
    
    # Success summary
    print()
    print("="*70)
    print("✅ EMAIL CONFIGURATION COMPLETE")
    print("="*70)
    print()
    print("Your settings:")
    print(f"  From: {email}")
    print(f"  To (client): {client_email}")
    print()
    print("The following systems will now work:")
    print("  ✅ Review email sending (send_review_email.py)")
    print("  ✅ Approval detection (approval_watcher.py)")
    print("  ✅ Client delivery (client_delivery.py)")
    print("  ✅ Health alerts (health_check.py)")
    print("  ✅ Watchdog notifications (watchdog.py)")
    print()
    print("Next steps:")
    print("  1. Deploy all scripts to both droplets")
    print("  2. Set up cron jobs (./setup_cron.sh)")
    print("  3. Test email flow (./test_email_flow.py)")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Setup failed: {e}")
        sys.exit(1)

