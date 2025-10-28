#!/usr/bin/env python3
"""
Enterprise Monitoring System for GasBuddy Scraper
- Health checks
- Progress tracking
- Error detection
- Alerting
- Resource monitoring
"""
import os
import sys
import time
import json
import psutil
from datetime import datetime, timedelta
import subprocess

MONITOR_DIR = "/opt/gasbuddy"
LOG_FILE = f"{MONITOR_DIR}/logs/monitor_{datetime.now().strftime('%Y%m%d')}.log"
STATUS_FILE = f"{MONITOR_DIR}/status.json"
ALERT_FILE = f"{MONITOR_DIR}/alerts.json"

class Monitor:
    def __init__(self):
        self.status = self.load_status()
        self.alerts = []
    
    def load_status(self):
        """Load current status from file"""
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {
            'last_run': None,
            'last_success': None,
            'total_runs': 0,
            'total_failures': 0,
            'consecutive_failures': 0
        }
    
    def save_status(self):
        """Save status to file"""
        with open(STATUS_FILE, 'w') as f:
            json.dump(self.status, f, indent=2)
    
    def log(self, message, level="INFO"):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + "\n")
    
    def check_process_running(self):
        """Check if scraper is currently running"""
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'production_scraper.py' in ' '.join(cmdline):
                    return True, proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return False, None
    
    def check_resource_usage(self):
        """Check system resource usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        resources = {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3)
        }
        
        # Alert on high resource usage
        if cpu_percent > 90:
            self.alert(f"High CPU usage: {cpu_percent}%", "WARNING")
        if memory.percent > 90:
            self.alert(f"High memory usage: {memory.percent}%", "WARNING")
        if disk.percent > 90:
            self.alert(f"High disk usage: {disk.percent}%", "CRITICAL")
        
        return resources
    
    def check_progress(self):
        """Check scraping progress"""
        completed_file = f"{MONITOR_DIR}/completed_zips.txt"
        failed_file = f"{MONITOR_DIR}/failed_zips.txt"
        
        completed_count = 0
        failed_count = 0
        
        if os.path.exists(completed_file):
            with open(completed_file, 'r') as f:
                completed_count = len([line for line in f if line.strip()])
        
        if os.path.exists(failed_file):
            with open(failed_file, 'r') as f:
                failed_count = len([line for line in f if line.strip()])
        
        total_zips = 41487
        percent_complete = (completed_count / total_zips) * 100
        
        return {
            'completed': completed_count,
            'failed': failed_count,
            'total': total_zips,
            'percent_complete': round(percent_complete, 2)
        }
    
    def check_recent_csvs(self):
        """Check for recently generated CSV files"""
        data_dir = f"{MONITOR_DIR}/data"
        if not os.path.exists(data_dir):
            return []
        
        csvs = []
        for filename in os.listdir(data_dir):
            if filename.endswith('.csv'):
                filepath = os.path.join(data_dir, filename)
                stat = os.stat(filepath)
                csvs.append({
                    'filename': filename,
                    'size_mb': round(stat.st_size / (1024**2), 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        csvs.sort(key=lambda x: x['modified'], reverse=True)
        return csvs[:5]  # Return 5 most recent
    
    def check_logs_for_errors(self):
        """Check recent logs for errors"""
        log_dir = f"{MONITOR_DIR}/logs"
        if not os.path.exists(log_dir):
            return []
        
        errors = []
        today_log = f"{log_dir}/monitor_{datetime.now().strftime('%Y%m%d')}.log"
        
        if os.path.exists(today_log):
            with open(today_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-100:]:  # Check last 100 lines
                    if 'ERROR' in line or 'CRITICAL' in line or 'Failed' in line:
                        errors.append(line.strip())
        
        return errors[-10:]  # Return last 10 errors
    
    def alert(self, message, level="INFO"):
        """Create an alert"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message
        }
        self.alerts.append(alert)
        self.log(message, level)
        
        # Save alerts to file
        all_alerts = []
        if os.path.exists(ALERT_FILE):
            with open(ALERT_FILE, 'r') as f:
                try:
                    all_alerts = json.load(f)
                except:
                    pass
        
        all_alerts.append(alert)
        
        # Keep only last 100 alerts
        all_alerts = all_alerts[-100:]
        
        with open(ALERT_FILE, 'w') as f:
            json.dump(all_alerts, f, indent=2)
    
    def generate_report(self):
        """Generate comprehensive status report"""
        self.log("="*70)
        self.log("GASBUDDY SCRAPER - HEALTH CHECK")
        self.log("="*70)
        
        # Check if process is running
        is_running, pid = self.check_process_running()
        if is_running:
            self.log(f"✅ Scraper is running (PID: {pid})")
        else:
            self.log("⚠️  Scraper is not running")
        
        # Check resources
        self.log("\n📊 RESOURCE USAGE:")
        resources = self.check_resource_usage()
        self.log(f"   CPU: {resources['cpu_percent']}%")
        self.log(f"   Memory: {resources['memory_percent']}% ({resources['memory_available_gb']:.1f} GB available)")
        self.log(f"   Disk: {resources['disk_percent']}% ({resources['disk_free_gb']:.1f} GB free)")
        
        # Check progress
        self.log("\n📈 SCRAPING PROGRESS:")
        progress = self.check_progress()
        self.log(f"   Completed: {progress['completed']:,} / {progress['total']:,} ({progress['percent_complete']}%)")
        self.log(f"   Failed: {progress['failed']:,}")
        
        # Check recent CSVs
        self.log("\n💾 RECENT CSV FILES:")
        csvs = self.check_recent_csvs()
        if csvs:
            for csv in csvs[:3]:
                self.log(f"   {csv['filename']} ({csv['size_mb']} MB) - {csv['modified']}")
        else:
            self.log("   No CSV files found")
        
        # Check for recent errors
        self.log("\n⚠️  RECENT ERRORS:")
        errors = self.check_logs_for_errors()
        if errors:
            for error in errors[-5:]:
                self.log(f"   {error}")
        else:
            self.log("   No recent errors")
        
        # Status summary
        self.log("\n📋 STATUS SUMMARY:")
        self.log(f"   Last run: {self.status.get('last_run', 'Never')}")
        self.log(f"   Last success: {self.status.get('last_success', 'Never')}")
        self.log(f"   Total runs: {self.status.get('total_runs', 0)}")
        self.log(f"   Total failures: {self.status.get('total_failures', 0)}")
        self.log(f"   Consecutive failures: {self.status.get('consecutive_failures', 0)}")
        
        # Alerts
        if self.alerts:
            self.log(f"\n🚨 NEW ALERTS: {len(self.alerts)}")
            for alert in self.alerts:
                self.log(f"   [{alert['level']}] {alert['message']}")
        
        self.log("="*70)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'is_running': is_running,
            'pid': pid,
            'resources': resources,
            'progress': progress,
            'recent_csvs': csvs,
            'recent_errors': errors,
            'status': self.status,
            'alerts': self.alerts
        }

if __name__ == "__main__":
    monitor = Monitor()
    report = monitor.generate_report()
    
    # Exit with error code if critical issues found
    if monitor.status.get('consecutive_failures', 0) >= 3:
        sys.exit(1)
    
    sys.exit(0)

