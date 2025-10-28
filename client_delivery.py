#!/usr/bin/env python3
"""
Client Delivery - Sends approved CSVs to client after 20 minute delay
Runs continuously, checking pending_delivery directory every 60 seconds
"""
import os
import time
from datetime import datetime
from email_utils import EmailConfig, send_email

CHECK_INTERVAL = 60  # Check every 60 seconds
PENDING_DELIVERY_DIR = '/opt/gasbuddy/pending_delivery'
DELIVERED_LOG = '/opt/gasbuddy/delivered_to_client.log'
AUDIT_LOG = '/opt/gasbuddy/audit.log'

def parse_delivery_file(delivery_file):
    """Parse a deliver_RUNID.txt file and return info dict"""
    info = {}
    with open(delivery_file, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                info[key] = value
    return info

def format_client_email(run_id, stats):
    """Generate professional HTML email for client"""
    
    # Parse timestamp from run_id
    try:
        timestamp = datetime.strptime(run_id, '%Y%m%d_%H%M%S')
        date_str = timestamp.strftime('%B %d, %Y')
    except:
        date_str = run_id
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .stats {{ background-color: #f5f5f5; padding: 15px; border-left: 4px solid #2196F3; margin: 20px 0; }}
            .stats-item {{ margin: 10px 0; }}
            .label {{ font-weight: bold; color: #333; }}
            .value {{ color: #555; }}
            .footer {{ background-color: #f9f9f9; padding: 15px; text-align: center; color: #777; font-size: 12px; margin-top: 30px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⛽ GasBuddy Data Delivery</h1>
        </div>
        
        <div class="content">
            <p>Hello,</p>
            
            <p>Please find attached the latest GasBuddy data for <strong>{date_str}</strong>.</p>
            
            <div class="stats">
                <h3>📊 Data Summary</h3>
                <div class="stats-item">
                    <span class="label">Total Gas Stations:</span>
                    <span class="value">{stats.get('total_stations', 'N/A'):,}</span>
                </div>
                <div class="stats-item">
                    <span class="label">Coverage:</span>
                    <span class="value">United States (All 50 states)</span>
                </div>
                <div class="stats-item">
                    <span class="label">Data Collected:</span>
                    <span class="value">{date_str}</span>
                </div>
                <div class="stats-item">
                    <span class="label">File Format:</span>
                    <span class="value">CSV (UTF-8 encoded)</span>
                </div>
            </div>
            
            <p><strong>📎 The complete dataset is attached to this email as a CSV file.</strong></p>
            
            <h3>📋 Data Fields</h3>
            <ul>
                <li>Station ID</li>
                <li>Station Name / Brand</li>
                <li>Complete Address (Street, City, State, ZIP)</li>
                <li>Gas Prices (by fuel type)</li>
                <li>Price Posted Time</li>
                <li>Reporter / Source</li>
                <li>Price Type (Cash / Credit)</li>
            </ul>
            
            <p>The data has been validated, deduplicated, and is ready for immediate integration.</p>
            
            <p>If you have any questions or need additional information, please don't hesitate to reach out.</p>
            
            <p>Best regards,<br>Spencer</p>
        </div>
        
        <div class="footer">
            <p>GasBuddy Data Service</p>
            <p>Automated Delivery System</p>
        </div>
    </body>
    </html>
    """
    
    return html

def log_audit_entry(run_id, stats, delivery_status):
    """Log delivery to audit trail"""
    with open(AUDIT_LOG, 'a') as f:
        f.write(f"{run_id}|"
                f"{stats.get('completed_at', '')}|"
                f"{stats.get('approved_at', '')}|"
                f"{datetime.now().isoformat()}|"
                f"{stats.get('total_stations', '')}|"
                f"{stats.get('merged_csv', '')}|"
                f"{delivery_status}\n")

def main():
    print("="*70)
    print("📬 CLIENT DELIVERY SYSTEM")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Pending directory: {PENDING_DELIVERY_DIR}")
    print(f"Check interval: {CHECK_INTERVAL}s")
    print("="*70)
    print()
    
    # Load email config
    config = EmailConfig()
    if not config.email_address or not config.client_email:
        print("❌ Email not configured! Please set up email_config.txt")
        return
    
    print(f"✅ From: {config.email_address}")
    print(f"✅ To: {config.client_email}")
    print()
    
    # Create log files and directories
    os.makedirs(PENDING_DELIVERY_DIR, exist_ok=True)
    if not os.path.exists(DELIVERED_LOG):
        open(DELIVERED_LOG, 'w').close()
    if not os.path.exists(AUDIT_LOG):
        # Write audit log header
        with open(AUDIT_LOG, 'w') as f:
            f.write("run_id|completed_at|approved_at|delivered_at|total_stations|csv_file|status\n")
    
    # Track delivered runs
    delivered_run_ids = set()
    with open(DELIVERED_LOG, 'r') as f:
        for line in f:
            if '|' in line:
                run_id = line.split('|')[0]
                delivered_run_ids.add(run_id)
    
    print(f"📋 Already delivered {len(delivered_run_ids)} runs to client")
    print()
    
    # Main delivery loop
    while True:
        try:
            # Find all pending deliveries
            delivery_files = [f for f in os.listdir(PENDING_DELIVERY_DIR) 
                            if f.startswith('deliver_') and f.endswith('.txt')]
            
            for delivery_file in delivery_files:
                delivery_path = os.path.join(PENDING_DELIVERY_DIR, delivery_file)
                
                # Parse delivery info
                info = parse_delivery_file(delivery_path)
                run_id = info.get('run_id')
                
                # Skip if already delivered
                if run_id in delivered_run_ids:
                    continue
                
                # Check if delivery time has arrived
                deliver_at_str = info.get('deliver_at')
                if not deliver_at_str:
                    continue
                
                deliver_at = datetime.fromisoformat(deliver_at_str)
                now = datetime.now()
                
                if now >= deliver_at:
                    print(f"[{now.strftime('%H:%M:%S')}] 📤 Delivering to client: {run_id}")
                    
                    csv_path = info.get('csv_path')
                    if not csv_path or not os.path.exists(csv_path):
                        print(f"   ❌ CSV file not found: {csv_path}")
                        continue
                    
                    print(f"   CSV: {os.path.basename(csv_path)}")
                    print(f"   Stations: {info.get('total_stations', 'N/A')}")
                    print(f"   Recipient: {config.client_email}")
                    
                    # Generate email
                    subject = f"GasBuddy Data - {datetime.now().strftime('%B %d, %Y')}"
                    body_html = format_client_email(run_id, info)
                    
                    # Send to client
                    print(f"   📧 Sending...")
                    
                    if send_email(config.client_email, subject, body_html, csv_path, config):
                        print(f"   ✅ Delivered successfully!")
                        
                        # Log delivery
                        with open(DELIVERED_LOG, 'a') as f:
                            f.write(f"{run_id}|{datetime.now().isoformat()}|{csv_path}|{config.client_email}\n")
                        
                        delivered_run_ids.add(run_id)
                        
                        # Audit log
                        log_audit_entry(run_id, info, 'delivered')
                        
                        # Remove delivery file
                        os.remove(delivery_path)
                        print(f"   🗑️  Removed delivery file")
                        print()
                    else:
                        print(f"   ❌ Delivery failed! Will retry...")
                        log_audit_entry(run_id, info, 'failed')
                        print()
                else:
                    # Show countdown
                    time_remaining = (deliver_at - now).total_seconds() / 60
                    if time_remaining > 0:
                        print(f"[{now.strftime('%H:%M:%S')}] ⏳ Waiting to deliver {run_id} "
                              f"({time_remaining:.1f} minutes remaining)")
            
            time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n❌ Error in delivery check: {e}")
            print("   Continuing...")
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopped by user")
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}")
        raise

