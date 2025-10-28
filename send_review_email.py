#!/usr/bin/env python3
"""
Email Review Sender - Watches for merge completion and sends review email
Runs continuously, checking for new merged CSVs every 60 seconds
"""
import os
import time
from datetime import datetime
from email_utils import EmailConfig, send_email

CHECK_INTERVAL = 60  # Check every 60 seconds
MERGE_DIR = '/opt/gasbuddy/merged'
SENT_LOG = '/opt/gasbuddy/review_emails_sent.log'

def parse_complete_file(complete_file):
    """Parse a complete_RUNID.txt file and return stats dict"""
    stats = {}
    with open(complete_file, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                stats[key] = value
    return stats

def format_review_email(run_id, stats):
    """Generate HTML email body for review"""
    
    # Parse timestamp from run_id
    try:
        timestamp = datetime.strptime(run_id, '%Y%m%d_%H%M%S')
        date_str = timestamp.strftime('%B %d, %Y at %I:%M %p')
    except:
        date_str = run_id
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .stats {{ background-color: #f5f5f5; padding: 15px; border-left: 4px solid #4CAF50; margin: 20px 0; }}
            .stats-item {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #555; }}
            .footer {{ background-color: #f9f9f9; padding: 15px; text-align: center; color: #777; font-size: 12px; }}
            .button {{ background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🔍 GasBuddy Scrape Complete - Awaiting Review</h1>
        </div>
        
        <div class="content">
            <p>Hi Spencer,</p>
            
            <p>The GasBuddy scrape has completed successfully on <strong>{date_str}</strong>.</p>
            
            <div class="stats">
                <h3>📊 Scrape Statistics</h3>
                <div class="stats-item">
                    <span class="label">Run ID:</span>
                    <span class="value">{run_id}</span>
                </div>
                <div class="stats-item">
                    <span class="label">Total Stations:</span>
                    <span class="value">{stats.get('total_stations', 'N/A'):,}</span>
                </div>
                <div class="stats-item">
                    <span class="label">Merged CSV:</span>
                    <span class="value">{os.path.basename(stats.get('merged_csv', 'N/A'))}</span>
                </div>
                <div class="stats-item">
                    <span class="label">Completed At:</span>
                    <span class="value">{stats.get('completed_at', 'N/A')}</span>
                </div>
            </div>
            
            <p><strong>📎 The merged CSV file is attached to this email.</strong></p>
            
            <p>Please review the data and reply with <strong>"APPROVED"</strong> to send it to the client.</p>
            
            <p>The system will automatically send the CSV to the client 20 minutes after receiving your approval.</p>
        </div>
        
        <div class="footer">
            <p>GasBuddy Scraper Automation System</p>
            <p>Run ID: {run_id}</p>
        </div>
    </body>
    </html>
    """
    
    return html

def main():
    print("="*70)
    print("📧 REVIEW EMAIL SENDER")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Merge directory: {MERGE_DIR}")
    print(f"Check interval: {CHECK_INTERVAL}s")
    print("="*70)
    print()
    
    # Load email config
    config = EmailConfig()
    if not config.email_address:
        print("❌ Email not configured! Please set up email_config.txt")
        return
    
    print(f"✅ Email configured: {config.email_address}")
    print()
    
    # Create directories
    os.makedirs(MERGE_DIR, exist_ok=True)
    
    # Track sent emails
    if not os.path.exists(SENT_LOG):
        open(SENT_LOG, 'w').close()
    
    sent_run_ids = set()
    with open(SENT_LOG, 'r') as f:
        for line in f:
            if '|' in line:
                run_id = line.split('|')[0]
                sent_run_ids.add(run_id)
    
    print(f"📋 Already sent review emails for {len(sent_run_ids)} runs")
    print()
    
    # Watch for new merges
    while True:
        # Find all complete_*.txt files in merged directory
        complete_files = [f for f in os.listdir(MERGE_DIR) if f.startswith('complete_') and f.endswith('.txt')]
        
        for complete_file in complete_files:
            # Extract run_id
            run_id = complete_file.replace('complete_', '').replace('.txt', '')
            
            # Skip if already sent
            if run_id in sent_run_ids:
                continue
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 🆕 New merge detected: {run_id}")
            
            # Parse stats
            complete_path = os.path.join(MERGE_DIR, complete_file)
            stats = parse_complete_file(complete_path)
            
            csv_path = stats.get('merged_csv')
            if not csv_path or not os.path.exists(csv_path):
                print(f"   ⚠️  CSV file not found: {csv_path}")
                continue
            
            print(f"   CSV: {os.path.basename(csv_path)}")
            print(f"   Stations: {stats.get('total_stations', 'N/A')}")
            
            # Generate email
            subject = f"🔍 GasBuddy Scrape {run_id[:8]} - Awaiting Review"
            body_html = format_review_email(run_id, stats)
            
            # Send email
            print(f"   📧 Sending review email to {config.email_address}...")
            
            if send_email(config.email_address, subject, body_html, csv_path, config):
                print(f"   ✅ Review email sent!")
                
                # Log this send
                with open(SENT_LOG, 'a') as f:
                    f.write(f"{run_id}|{datetime.now().isoformat()}|{csv_path}\n")
                
                sent_run_ids.add(run_id)
                print()
            else:
                print(f"   ❌ Failed to send email. Will retry...")
                print()
        
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        raise

