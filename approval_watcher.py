#!/usr/bin/env python3
"""
Approval Watcher - Checks inbox for approval replies
Runs continuously, checking every 5 minutes for approval emails
When approved, triggers client delivery after 20 minute delay
"""
import os
import time
from datetime import datetime, timedelta
from email_utils import EmailConfig, check_for_approval

CHECK_INTERVAL = 300  # Check every 5 minutes
SENT_LOG = '/opt/gasbuddy/review_emails_sent.log'
APPROVED_LOG = '/opt/gasbuddy/approved_runs.log'
PENDING_DELIVERY_DIR = '/opt/gasbuddy/pending_delivery'

def get_pending_approvals():
    """Get list of runs waiting for approval"""
    pending = {}
    
    if not os.path.exists(SENT_LOG):
        return pending
    
    # Load sent review emails
    with open(SENT_LOG, 'r') as f:
        for line in f:
            if '|' in line:
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    run_id = parts[0]
                    sent_time = parts[1]
                    csv_path = parts[2]
                    pending[run_id] = {'sent_time': sent_time, 'csv_path': csv_path}
    
    # Remove already approved
    if os.path.exists(APPROVED_LOG):
        with open(APPROVED_LOG, 'r') as f:
            for line in f:
                if '|' in line:
                    run_id = line.split('|')[0]
                    if run_id in pending:
                        del pending[run_id]
    
    return pending

def schedule_client_delivery(run_id, csv_path, stats):
    """Schedule a CSV for delivery to client after 20 minute delay"""
    delivery_time = datetime.now() + timedelta(minutes=20)
    
    # Create pending delivery file
    os.makedirs(PENDING_DELIVERY_DIR, exist_ok=True)
    delivery_file = os.path.join(PENDING_DELIVERY_DIR, f'deliver_{run_id}.txt')
    
    with open(delivery_file, 'w') as f:
        f.write(f"run_id={run_id}\n")
        f.write(f"csv_path={csv_path}\n")
        f.write(f"approved_at={datetime.now().isoformat()}\n")
        f.write(f"deliver_at={delivery_time.isoformat()}\n")
        for key, value in stats.items():
            f.write(f"{key}={value}\n")
    
    print(f"   📅 Scheduled for delivery at {delivery_time.strftime('%I:%M %p')}")
    print(f"   📁 Delivery file: {delivery_file}")
    
    return delivery_file

def main():
    print("="*70)
    print("👀 APPROVAL WATCHER")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Check interval: {CHECK_INTERVAL}s (5 minutes)")
    print("="*70)
    print()
    
    # Load email config
    config = EmailConfig()
    if not config.email_address:
        print("❌ Email not configured! Please set up email_config.txt")
        return
    
    print(f"✅ Email configured: {config.email_address}")
    print()
    
    # Create log files
    if not os.path.exists(APPROVED_LOG):
        open(APPROVED_LOG, 'w').close()
    
    os.makedirs(PENDING_DELIVERY_DIR, exist_ok=True)
    
    # Main watch loop
    while True:
        try:
            pending = get_pending_approvals()
            
            if pending:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Checking {len(pending)} pending approval(s)...")
                
                for run_id, info in pending.items():
                    # Check inbox for approval
                    if check_for_approval(run_id, config):
                        print(f"\n   ✅ APPROVED: {run_id}")
                        print(f"   CSV: {os.path.basename(info['csv_path'])}")
                        
                        # Parse stats from merge complete file
                        stats = {}
                        complete_file = f'/opt/gasbuddy/merged/complete_{run_id}.txt'
                        if os.path.exists(complete_file):
                            with open(complete_file, 'r') as f:
                                for line in f:
                                    if '=' in line:
                                        key, value = line.strip().split('=', 1)
                                        stats[key] = value
                        
                        # Schedule for client delivery
                        delivery_file = schedule_client_delivery(run_id, info['csv_path'], stats)
                        
                        # Log approval
                        with open(APPROVED_LOG, 'a') as f:
                            f.write(f"{run_id}|{datetime.now().isoformat()}|{info['csv_path']}|{delivery_file}\n")
                        
                        print(f"   ✅ Logged to approved_runs.log\n")
                
            time.sleep(CHECK_INTERVAL)
        
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"\n❌ Error in approval check: {e}")
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

