#!/usr/bin/env python3
"""
Send Review Email - Sends merged CSV to user for approval
Called by post_run_droplet2.sh after successful merge
"""
import os
import sys
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import base64

class EmailConfig:
    """Load email configuration"""
    def __init__(self, config_file='/opt/gasbuddy/email_config.txt'):
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
            self.email_address = None
            self.sendgrid_api_key = None
            self.client_email = None

def send_review_email(merge_id, csv_path, station_count, review_email):
    """
    Send merged CSV to user for review
    
    Args:
        merge_id: Unique ID for this merge (RUN_ID_D1_RUN_ID_D2)
        csv_path: Path to merged CSV file
        station_count: Number of stations in CSV
        review_email: Email address to send review to
    
    Returns:
        True if successful, False otherwise
    """
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    # Get file size
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    
    config = EmailConfig()
    
    if not config.email_address or not config.sendgrid_api_key:
        print("❌ SendGrid not configured!")
        return False
    
    try:
        # Create HTML email body
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats {{ background-color: #f5f5f5; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0; }}
                .approval {{ background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }}
                .button {{ 
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #4CAF50;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 GasBuddy Scrape Complete - Review Required</h1>
            </div>
            
            <div class="content">
                <h2>Scrape Successful!</h2>
                <p>Both droplets have completed their scraping run and the data has been merged and deduplicated.</p>
                
                <div class="stats">
                    <h3>📈 Run Statistics</h3>
                    <p><strong>Merge ID:</strong> {merge_id}</p>
                    <p><strong>Total Unique Stations:</strong> {station_count:,}</p>
                    <p><strong>File Size:</strong> {file_size_mb:.1f} MB</p>
                    <p><strong>Completed:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h3>📎 Attached File</h3>
                <p>The merged and deduplicated CSV is attached to this email.</p>
                
                <div class="approval">
                    <h3>⚠️ Action Required: Review & Approve</h3>
                    <p><strong>To approve this data for client delivery:</strong></p>
                    <ol>
                        <li>Download and review the attached CSV file</li>
                        <li>Reply to this email with: <strong>"APPROVED"</strong> or <strong>"OK"</strong></li>
                        <li>The system will automatically send to the client 30 seconds after approval</li>
                    </ol>
                    <p><em>Note: You can reply from any device - just include "APPROVED" or "OK" in your reply.</em></p>
                </div>
                
                <h3>🔍 Quick Quality Checks</h3>
                <ul>
                    <li>Verify station count is reasonable (~100K-150K expected)</li>
                    <li>Check file opens correctly</li>
                    <li>Spot-check a few familiar stations</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        # Create message
        message = Mail(
            from_email=config.email_address,
            to_emails=review_email,
            subject=f'🔔 GasBuddy Scrape Complete - Review Required ({station_count:,} stations)',
            html_content=html
        )
        
        # Attach CSV file
        with open(csv_path, 'rb') as f:
            csv_data = f.read()
        
        encoded_file = base64.b64encode(csv_data).decode()
        
        attached_file = Attachment(
            FileContent(encoded_file),
            FileName(os.path.basename(csv_path)),
            FileType('text/csv'),
            Disposition('attachment')
        )
        message.attachment = attached_file
        
        # Send via SendGrid
        sg = SendGridAPIClient(config.sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            print(f"✅ Review email sent successfully")
            print(f"   To: {review_email}")
            print(f"   Attachment: {os.path.basename(csv_path)} ({file_size_mb:.1f} MB)")
            print(f"   SendGrid Status: {response.status_code}")
            
            # Log the review request
            log_file = '/opt/gasbuddy/logs/review_requests.log'
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()}|{merge_id}|{station_count}|{review_email}|SENT\n")
            
            return True
        else:
            print(f"❌ SendGrid returned status: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Failed to send review email: {e}")
        if hasattr(e, 'body'):
            print(f"   Error details: {e.body}")
        return False

def main():
    """Main execution"""
    if len(sys.argv) != 4:
        print("Usage: send_review_email.py <MERGE_ID> <CSV_PATH> <STATION_COUNT>")
        sys.exit(1)
    
    merge_id = sys.argv[1]
    csv_path = sys.argv[2]
    station_count = int(sys.argv[3])
    
    # For now, hardcode review email (can be made configurable later)
    review_email = "scourvilletaylor@gmail.com"
    
    print("=" * 60)
    print("📧 SENDING REVIEW EMAIL")
    print("=" * 60)
    print(f"Merge ID: {merge_id}")
    print(f"CSV: {csv_path}")
    print(f"Stations: {station_count:,}")
    print(f"To: {review_email}")
    print()
    
    success = send_review_email(merge_id, csv_path, station_count, review_email)
    
    if success:
        print()
        print("=" * 60)
        print("✅ REVIEW EMAIL SENT")
        print("=" * 60)
        print("Waiting for approval reply...")
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ FAILED TO SEND")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()
