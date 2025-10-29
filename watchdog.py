#!/usr/bin/env python3
"""
Watchdog - Auto-restart dead scrapers
Checks every 2 minutes if scraper process is dead but run is incomplete
Automatically restarts and sends email notification
"""
import os
import sys
import subprocess
import time
from datetime import datetime
from email_utils import EmailConfig, send_email

# Configuration
DROPLET_ID = os.environ.get('DROPLET_ID', '1')  # Set via environment: 1 or 2
DROPLET_NAME = f"Droplet {DROPLET_ID}"
SCRAPER_SCRIPT = f'production_scraper_droplet{DROPLET_ID}.py'

# Paths
WATCHDOG_LOG = f'/opt/gasbuddy/watchdog_droplet{DROPLET_ID}.log'
RESTART_LOG = f'/opt/gasbuddy/restarts_droplet{DROPLET_ID}.log'

def log_message(message):
    """Log message to watchdog log"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{timestamp}] {message}\n"
    
    os.makedirs(os.path.dirname(WATCHDOG_LOG), exist_ok=True)
    with open(WATCHDOG_LOG, 'a') as f:
        f.write(log_line)
    
    print(log_line.strip())

def is_process_running():
    """Check if scraper process is running"""
    try:
        # More specific pattern to avoid false positives
        result = subprocess.run(
            f'pgrep -f "^python3 .*{SCRAPER_SCRIPT}"',
            shell=True,
            capture_output=True,
            text=True
        )
        # Also verify the PID actually belongs to our scraper
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    # Double-check this PID is actually the scraper
                    check = subprocess.run(
                        f'ps -p {pid} -o cmd=',
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if SCRAPER_SCRIPT in check.stdout and 'watchdog' not in check.stdout:
                        return True
        return False
    except:
        return False

def should_be_running():
    """Check if there's an active run (incomplete)"""
    current_run_file = f'/opt/gasbuddy/current_run_droplet{DROPLET_ID}.txt'
    
    if not os.path.exists(current_run_file):
        return False, None
    
    try:
        with open(current_run_file, 'r') as f:
            run_id = f.read().strip()
        
        # Check if run is complete
        complete_file = f'/opt/gasbuddy/runs/complete_{run_id}_droplet{DROPLET_ID}.txt'
        if os.path.exists(complete_file):
            return False, run_id  # Run is complete, no need to restart
        
        return True, run_id  # Run is incomplete, should be running
    except:
        return False, None

def restart_scraper():
    """Restart the scraper process"""
    try:
        log_message(f"🔄 Attempting to restart scraper...")
        
        # Change to gasbuddy directory and start scraper in background
        cmd = f'cd /opt/gasbuddy && nohup python3 -u {SCRAPER_SCRIPT} > logs/scraper_run.log 2>&1 &'
        
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        # Give it a moment to start
        time.sleep(3)
        
        # Verify it's running
        if is_process_running():
            log_message(f"✅ Scraper restarted successfully")
            return True
        else:
            log_message(f"❌ Scraper failed to restart")
            return False
    
    except Exception as e:
        log_message(f"❌ Error during restart: {e}")
        return False

def send_restart_notification(run_id, success):
    """Send email notification about restart"""
    config = EmailConfig()
    
    if not config.email_address:
        log_message("⚠️  Email not configured, skipping notification")
        return
    
    if success:
        subject = f"🔄 {DROPLET_NAME} - Scraper Auto-Restarted"
        status_color = "#4CAF50"
        status_icon = "✅"
        status_text = "Successfully Restarted"
    else:
        subject = f"❌ {DROPLET_NAME} - Scraper Restart Failed"
        status_color = "#d32f2f"
        status_icon = "❌"
        status_text = "Restart Failed"
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background-color: {status_color}; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .info {{ background-color: #f5f5f5; padding: 15px; border-left: 4px solid {status_color}; margin: 20px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{status_icon} Watchdog Auto-Restart</h1>
        </div>
        
        <div class="content">
            <p><strong>Droplet:</strong> {DROPLET_NAME}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Status:</strong> {status_text}</p>
            
            <div class="info">
                <h3>Details</h3>
                <p><strong>Run ID:</strong> {run_id}</p>
                <p><strong>Action:</strong> Scraper process was found dead during active run. Watchdog automatically attempted restart.</p>
                {'<p style="color: #4CAF50;"><strong>Result:</strong> Process restarted successfully and is now running.</p>' if success else '<p style="color: #d32f2f;"><strong>Result:</strong> Restart failed. Manual intervention required.</p>'}
            </div>
            
            <h3>🔧 Recommended Actions</h3>
            <ul>
                <li>SSH into {DROPLET_NAME} to verify status</li>
                <li>Check logs: <code>tail -100 /opt/gasbuddy/logs/scraper_run.log</code></li>
                <li>Monitor progress: <code>./monitor_both_droplets.sh</code></li>
                {'<li style="color: #d32f2f;"><strong>Manual restart required:</strong> <code>cd /opt/gasbuddy && python3 ' + SCRAPER_SCRIPT + '</code></li>' if not success else ''}
            </ul>
        </div>
    </body>
    </html>
    """
    
    if send_email(config.email_address, subject, html, None, config):
        log_message(f"📧 Restart notification sent to {config.email_address}")
    else:
        log_message(f"❌ Failed to send restart notification")

def log_restart(run_id, success):
    """Log restart event"""
    timestamp = datetime.now().isoformat()
    status = 'SUCCESS' if success else 'FAILED'
    
    os.makedirs(os.path.dirname(RESTART_LOG), exist_ok=True)
    with open(RESTART_LOG, 'a') as f:
        f.write(f"{timestamp}|{run_id}|{status}\n")

def main():
    """Main watchdog execution"""
    
    # Check if process is running
    process_running = is_process_running()
    
    # Check if it should be running
    should_run, run_id = should_be_running()
    
    if should_run and not process_running:
        # DEAD PROCESS WITH ACTIVE RUN - RESTART!
        log_message(f"🚨 ALERT: Scraper process dead but run {run_id} is incomplete!")
        log_message(f"📍 Process status: Not running")
        log_message(f"📍 Active run: {run_id}")
        
        # Attempt restart
        success = restart_scraper()
        
        # Log and notify
        log_restart(run_id, success)
        send_restart_notification(run_id, success)
        
        sys.exit(0 if success else 1)
    
    elif not should_run and not process_running:
        # No active run, process not running - normal state
        log_message(f"✅ No active run, process correctly stopped")
        sys.exit(0)
    
    elif process_running:
        # Process is running (either with or without active run)
        if should_run:
            log_message(f"✅ Process running, active run: {run_id}")
        else:
            log_message(f"✅ Process running (no active incomplete run)")
        sys.exit(0)
    
    else:
        # Edge case
        log_message(f"⚠️  Unexpected state")
        sys.exit(0)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log_message(f"❌ Watchdog error: {e}")
        sys.exit(1)

