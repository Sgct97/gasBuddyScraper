#!/usr/bin/env python3
"""
Enterprise Health Monitor for GasBuddy Scraper
Checks all critical system metrics and sends email alerts on issues
Run via cron every 5 minutes
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

# Thresholds
MEMORY_THRESHOLD = 80  # Alert if memory usage > 80%
DISK_THRESHOLD = 90    # Alert if disk usage > 90%
MIN_RATE = 1.5         # Alert if scraping rate < 1.5 ZIP/s
STALL_MINUTES = 10     # Alert if no progress for 10 minutes

# Paths
LOG_DIR = '/opt/gasbuddy/logs'
HEALTH_LOG = f'/opt/gasbuddy/health_check_droplet{DROPLET_ID}.log'
LAST_ALERT_FILE = f'/opt/gasbuddy/last_alert_droplet{DROPLET_ID}.txt'

# Alert cooldown (don't spam emails)
ALERT_COOLDOWN_MINUTES = 30

class HealthStatus:
    """Track health check results"""
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.info = {}
        self.critical = False
    
    def add_issue(self, message, critical=True):
        """Add a health issue"""
        if critical:
            self.issues.append(message)
            self.critical = True
        else:
            self.warnings.append(message)
    
    def add_info(self, key, value):
        """Add informational metric"""
        self.info[key] = value
    
    def is_healthy(self):
        """Check if system is healthy"""
        return len(self.issues) == 0

def get_process_status():
    """Check if scraper process is running"""
    try:
        result = subprocess.run(
            f'pgrep -f "python3.*production_scraper_droplet{DROPLET_ID}"',
            shell=True,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except:
        return False

def get_memory_usage():
    """Get current memory usage percentage"""
    try:
        result = subprocess.run(
            "free | grep Mem | awk '{print ($3/$2) * 100.0}'",
            shell=True,
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except:
        return 0

def get_disk_usage():
    """Get disk usage percentage for /opt"""
    try:
        result = subprocess.run(
            "df /opt | tail -1 | awk '{print $5}' | sed 's/%//'",
            shell=True,
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except:
        return 0

def get_current_rate():
    """Get current scraping rate from logs"""
    try:
        log_file = f'{LOG_DIR}/scraper_run.log'
        if not os.path.exists(log_file):
            return None
        
        # Get last rate from log
        result = subprocess.run(
            f"tail -10 {log_file} | grep 'Rate:' | tail -1 | grep -o '[0-9.]*ZIP/s' | grep -o '[0-9.]*'",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.stdout.strip():
            return float(result.stdout.strip())
        return None
    except:
        return None

def check_progress_stall():
    """Check if scraper has stalled (no progress in last N minutes)"""
    try:
        current_run_file = f'/opt/gasbuddy/current_run_droplet{DROPLET_ID}.txt'
        if not os.path.exists(current_run_file):
            return False, "No active run"
        
        with open(current_run_file, 'r') as f:
            run_id = f.read().strip()
        
        completed_file = f'/opt/gasbuddy/runs/completed_{run_id}_droplet{DROPLET_ID}.txt'
        
        if not os.path.exists(completed_file):
            return False, "No progress file"
        
        # Check last modification time
        mod_time = os.path.getmtime(completed_file)
        minutes_since = (time.time() - mod_time) / 60
        
        if minutes_since > STALL_MINUTES:
            return True, f"No progress for {minutes_since:.1f} minutes"
        
        return False, f"Last progress: {minutes_since:.1f} minutes ago"
    except Exception as e:
        return False, f"Error checking: {e}"

def get_error_count():
    """Count errors in recent logs"""
    try:
        log_file = f'{LOG_DIR}/scraper_run.log'
        if not os.path.exists(log_file):
            return 0
        
        result = subprocess.run(
            f"tail -100 {log_file} | grep -i 'error\\|failed\\|exception' | wc -l",
            shell=True,
            capture_output=True,
            text=True
        )
        return int(result.stdout.strip())
    except:
        return 0

def should_send_alert():
    """Check if enough time has passed since last alert"""
    if not os.path.exists(LAST_ALERT_FILE):
        return True
    
    try:
        with open(LAST_ALERT_FILE, 'r') as f:
            last_alert_time = float(f.read().strip())
        
        minutes_since = (time.time() - last_alert_time) / 60
        return minutes_since >= ALERT_COOLDOWN_MINUTES
    except:
        return True

def record_alert():
    """Record that an alert was sent"""
    with open(LAST_ALERT_FILE, 'w') as f:
        f.write(str(time.time()))

def format_alert_email(status):
    """Generate HTML email for health alert"""
    
    issue_list = '\n'.join(f'<li style="color: #d32f2f; margin: 10px 0;">{issue}</li>' for issue in status.issues)
    warning_list = '\n'.join(f'<li style="color: #f57c00; margin: 10px 0;">{warning}</li>' for warning in status.warnings)
    
    info_rows = '\n'.join(
        f'<tr><td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>{key}</strong></td>'
        f'<td style="padding: 8px; border-bottom: 1px solid #ddd;">{value}</td></tr>'
        for key, value in status.info.items()
    )
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
            .header {{ background-color: #d32f2f; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .critical {{ background-color: #ffebee; padding: 15px; border-left: 4px solid #d32f2f; margin: 20px 0; }}
            .warnings {{ background-color: #fff3e0; padding: 15px; border-left: 4px solid #f57c00; margin: 20px 0; }}
            .metrics {{ background-color: #f5f5f5; padding: 15px; margin: 20px 0; }}
            table {{ width: 100%; border-collapse: collapse; }}
            ul {{ margin: 10px 0; padding-left: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 {DROPLET_NAME} Health Alert</h1>
        </div>
        
        <div class="content">
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>Droplet:</strong> {DROPLET_NAME}</p>
            
            {'<div class="critical"><h3>🔴 Critical Issues</h3><ul>' + issue_list + '</ul></div>' if status.issues else ''}
            
            {'<div class="warnings"><h3>⚠️ Warnings</h3><ul>' + warning_list + '</ul></div>' if status.warnings else ''}
            
            <div class="metrics">
                <h3>📊 System Metrics</h3>
                <table>
                    {info_rows}
                </table>
            </div>
            
            <h3>🔧 Recommended Actions</h3>
            <ul>
                <li>SSH into {DROPLET_NAME}: <code>ssh root@{status.info.get('IP', 'DROPLET_IP')}</code></li>
                <li>Check logs: <code>tail -100 /opt/gasbuddy/logs/scraper_run.log</code></li>
                <li>Check process: <code>pgrep -f production_scraper</code></li>
                <li>Restart if needed: <code>cd /opt/gasbuddy && ./watchdog.py</code></li>
            </ul>
        </div>
    </body>
    </html>
    """
    
    return html

def perform_health_check():
    """Run complete health check"""
    status = HealthStatus()
    
    # 1. Check if process is running
    process_running = get_process_status()
    status.add_info('Process Running', '✅ Yes' if process_running else '❌ No')
    
    # Check if it SHOULD be running (is there an active run?)
    current_run_file = f'/opt/gasbuddy/current_run_droplet{DROPLET_ID}.txt'
    should_be_running = os.path.exists(current_run_file)
    
    if should_be_running and not process_running:
        status.add_issue(f"Scraper process is not running but run is active!", critical=True)
    
    # 2. Check memory usage
    memory_usage = get_memory_usage()
    status.add_info('Memory Usage', f'{memory_usage:.1f}%')
    if memory_usage > MEMORY_THRESHOLD:
        status.add_issue(f"Memory usage is high: {memory_usage:.1f}% (threshold: {MEMORY_THRESHOLD}%)", critical=True)
    
    # 3. Check disk usage
    disk_usage = get_disk_usage()
    status.add_info('Disk Usage', f'{disk_usage:.1f}%')
    if disk_usage > DISK_THRESHOLD:
        status.add_issue(f"Disk usage is high: {disk_usage:.1f}% (threshold: {DISK_THRESHOLD}%)", critical=True)
    
    # 4. Check scraping rate (only if running)
    if process_running:
        rate = get_current_rate()
        if rate is not None:
            status.add_info('Scraping Rate', f'{rate:.2f} ZIP/s')
            if rate < MIN_RATE:
                status.add_issue(f"Scraping rate is low: {rate:.2f} ZIP/s (minimum: {MIN_RATE} ZIP/s)", critical=False)
        else:
            status.add_info('Scraping Rate', 'Unknown')
    
    # 5. Check for stalled progress
    if process_running:
        is_stalled, stall_msg = check_progress_stall()
        status.add_info('Progress Status', stall_msg)
        if is_stalled:
            status.add_issue(f"Scraper appears stalled: {stall_msg}", critical=True)
    
    # 6. Check for errors in logs
    error_count = get_error_count()
    status.add_info('Recent Errors', str(error_count))
    if error_count > 10:
        status.add_issue(f"High error count in logs: {error_count} errors in last 100 lines", critical=False)
    
    # Get IP for recommendations
    try:
        import socket
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        status.add_info('IP', ip)
    except:
        status.add_info('IP', 'Unknown')
    
    return status

def main():
    """Main health check execution"""
    
    # Log check time
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Perform health check
    status = perform_health_check()
    
    # Log results
    os.makedirs(os.path.dirname(HEALTH_LOG), exist_ok=True)
    with open(HEALTH_LOG, 'a') as f:
        if status.is_healthy():
            f.write(f"[{timestamp}] ✅ HEALTHY - All checks passed\n")
            print(f"✅ {DROPLET_NAME} is healthy")
        else:
            f.write(f"[{timestamp}] ❌ UNHEALTHY - {len(status.issues)} issue(s), {len(status.warnings)} warning(s)\n")
            for issue in status.issues:
                f.write(f"  - {issue}\n")
            print(f"❌ {DROPLET_NAME} has issues!")
    
    # Send alert email if there are issues
    if not status.is_healthy():
        if should_send_alert():
            config = EmailConfig()
            if config.email_address:
                subject = f"🚨 {DROPLET_NAME} Health Alert"
                body_html = format_alert_email(status)
                
                print(f"📧 Sending alert email to {config.email_address}...")
                
                if send_email(config.email_address, subject, body_html, None, config):
                    print("✅ Alert email sent")
                    record_alert()
                else:
                    print("❌ Failed to send alert email")
            else:
                print("⚠️  Email not configured, skipping alert")
        else:
            print(f"⏳ Alert cooldown active (last alert < {ALERT_COOLDOWN_MINUTES} min ago)")
    
    # Exit with error code if critical issues
    sys.exit(1 if status.critical else 0)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        sys.exit(1)

