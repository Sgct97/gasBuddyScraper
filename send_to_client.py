#!/usr/bin/env python3
"""
Send to Client - Delivers approved CSV to client
Called by approval_watcher.py after approval + delay
"""
import os
import sys
import time
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

def get_merge_info(merge_id):
    """Get information about the merge from complete file"""
    complete_file = f"/opt/gasbuddy/merged/complete_{merge_id}.txt"
    
    if not os.path.exists(complete_file):
        # Check archive
        # Format: archive/YYYY/MM/RUN_ID/complete_MERGE_ID.txt
        # But MERGE_ID contains two RUN_IDs, need to find it
        archive_base = "/opt/gasbuddy/archive"
        for year in os.listdir(archive_base):
            year_path = os.path.join(archive_base, year)
            if not os.path.isdir(year_path):
                continue
            for month in os.listdir(year_path):
                month_path = os.path.join(year_path, month)
                if not os.path.isdir(month_path):
                    continue
                # Check all run directories for the complete file
                for run_dir in os.listdir(month_path):
                    complete_check = os.path.join(month_path, run_dir, f"complete_{merge_id}.txt")
                    if os.path.exists(complete_check):
                        complete_file = complete_check
                        break
    
    if not os.path.exists(complete_file):
        return None
    
    info = {}
    with open(complete_file, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                info[key] = value
    
    return info

def send_to_client(merge_id, client_email, delay_seconds=30):
    """
    Send merged CSV to client after approval
    
    Args:
        merge_id: Merge ID to send
        client_email: Client email address
        delay_seconds: Delay before sending (default 30 for testing, 1200 for production)
    
    Returns:
        True if successful, False otherwise
    """
    
    print(f"⏱️  Waiting {delay_seconds} seconds before sending to client...")
    time.sleep(delay_seconds)
    
    # Get merge info
    merge_info = get_merge_info(merge_id)
    if not merge_info:
        print(f"❌ Could not find merge info for {merge_id}")
        return False
    
    csv_path = merge_info.get('merged_csv')
    station_count = merge_info.get('total_stations', 'Unknown')
    
    if not csv_path or not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return False
    
    file_size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    
    config = EmailConfig()
    
    if not config.email_address or not config.sendgrid_api_key:
        print("❌ SendGrid not configured!")
        return False
    
    try:
        # Create HTML email body for client
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
                .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; }}
                .stats {{ background-color: #f5f5f5; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>⛽ GasBuddy Gas Station Data - Latest Update</h1>
            </div>
            
            <div class="content">
                <h2>Your Latest Gas Station Data is Ready</h2>
                <p>We've completed our latest comprehensive scrape of gas station data across the United States.</p>
                
                <div class="stats">
                    <h3>📊 Data Summary</h3>
                    <p><strong>Total Unique Stations:</strong> {station_count}</p>
                    <p><strong>Coverage:</strong> All US markets (42,000+ ZIP codes)</p>
                    <p><strong>File Size:</strong> {file_size_mb:.1f} MB</p>
                    <p><strong>Data Freshness:</strong> Last 24-48 hours</p>
                    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <h3>📎 Attached File</h3>
                <p>The complete CSV file is attached to this email with all station details including:</p>
                <ul>
                    <li>Station name, brand, and address</li>
                    <li>Fuel prices (regular, midgrade, premium, diesel)</li>
                    <li>Cash and credit pricing</li>
                    <li>Amenities (car wash, convenience store, etc.)</li>
                    <li>Ratings and recent price update timestamps</li>
                </ul>
                
                <h3>📋 CSV Format</h3>
                <p>The data is provided in standard CSV format, easily imported into databases or applications.</p>
                
                <h3>🔄 Next Update</h3>
                <p>You'll receive the next data update in approximately 12 hours.</p>
                
                <p>If you have any questions or need assistance, please don't hesitate to reach out.</p>
                
                <p>Best regards,<br>
                The GasBuddy Data Team</p>
            </div>
        </body>
        </html>
        """
        
        # Create message
        message = Mail(
            from_email=config.email_address,
            to_emails=client_email,
            subject=f'⛽ GasBuddy Gas Station Data Update - {station_count} Stations',
            html_content=html
        )
        
        # Attach CSV file
        with open(csv_path, 'rb') as f:
            csv_data = f.read()
        
        encoded_file = base64.b64encode(csv_data).decode()
        
        # Use a cleaner filename for client
        client_filename = f"gasbuddy_stations_{datetime.now().strftime('%Y%m%d')}.csv"
        
        attached_file = Attachment(
            FileContent(encoded_file),
            FileName(client_filename),
            FileType('text/csv'),
            Disposition('attachment')
        )
        message.attachment = attached_file
        
        # Send via SendGrid
        sg = SendGridAPIClient(config.sendgrid_api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 202]:
            print(f"✅ Client delivery successful")
            print(f"   To: {client_email}")
            print(f"   Attachment: {client_filename} ({file_size_mb:.1f} MB)")
            print(f"   SendGrid Status: {response.status_code}")
            
            # Log the delivery
            log_file = '/opt/gasbuddy/logs/client_deliveries.log'
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()}|{merge_id}|{station_count}|{client_email}|SUCCESS\n")
            
            return True
        else:
            print(f"❌ SendGrid returned status: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Failed to send to client: {e}")
        if hasattr(e, 'body'):
            print(f"   Error details: {e.body}")
        return False

def main():
    """Main execution"""
    if len(sys.argv) < 2:
        print("Usage: send_to_client.py <MERGE_ID> [delay_seconds]")
        sys.exit(1)
    
    merge_id = sys.argv[1]
    delay_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    config = EmailConfig()
    client_email = config.client_email
    
    if not client_email:
        print("❌ Client email not configured!")
        sys.exit(1)
    
    print("=" * 60)
    print("📤 SENDING TO CLIENT")
    print("=" * 60)
    print(f"Merge ID: {merge_id}")
    print(f"Client: {client_email}")
    print(f"Delay: {delay_seconds} seconds")
    print()
    
    success = send_to_client(merge_id, client_email, delay_seconds)
    
    if success:
        print()
        print("=" * 60)
        print("✅ CLIENT DELIVERY COMPLETE")
        print("=" * 60)
        sys.exit(0)
    else:
        print()
        print("=" * 60)
        print("❌ CLIENT DELIVERY FAILED")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    main()

