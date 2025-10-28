#!/usr/bin/env python3
"""
Archive Old Data - Storage Management
Moves old CSVs to archive directory and optionally compresses
Cleans up old logs and temporary files
Run monthly via cron or manually
"""
import os
import shutil
import gzip
from datetime import datetime, timedelta
import subprocess

# Configuration
ARCHIVE_AGE_DAYS = 90  # Archive CSVs older than 90 days
COMPRESS_AGE_DAYS = 30  # Compress CSVs older than 30 days
DELETE_LOGS_DAYS = 30  # Delete logs older than 30 days
BASE_DIR = '/opt/gasbuddy'

# Directories
DATA_DIR = os.path.join(BASE_DIR, 'data')
MERGED_DIR = os.path.join(BASE_DIR, 'merged')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
RUNS_DIR = os.path.join(BASE_DIR, 'runs')
ARCHIVE_DIR = os.path.join(BASE_DIR, 'archive')

def get_directory_size(path):
    """Get total size of directory in MB"""
    try:
        result = subprocess.run(
            f'du -sm {path}',
            shell=True,
            capture_output=True,
            text=True
        )
        return int(result.stdout.split()[0])
    except:
        return 0

def get_file_age_days(filepath):
    """Get age of file in days"""
    mod_time = os.path.getmtime(filepath)
    age = datetime.now() - datetime.fromtimestamp(mod_time)
    return age.days

def compress_file(filepath):
    """Compress a file with gzip"""
    try:
        with open(filepath, 'rb') as f_in:
            with gzip.open(f'{filepath}.gz', 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Verify compressed file exists and remove original
        if os.path.exists(f'{filepath}.gz'):
            os.remove(filepath)
            return True
        return False
    except Exception as e:
        print(f"  ❌ Failed to compress {filepath}: {e}")
        return False

def archive_old_csvs():
    """Move old CSVs to archive directory"""
    print("="*70)
    print("📦 ARCHIVING OLD CSVs")
    print("="*70)
    print()
    
    archived_count = 0
    compressed_count = 0
    
    # Process data directory
    for directory in [DATA_DIR, MERGED_DIR]:
        if not os.path.exists(directory):
            continue
        
        print(f"Processing: {directory}")
        
        for filename in os.listdir(directory):
            if not filename.endswith('.csv') and not filename.endswith('.csv.gz'):
                continue
            
            filepath = os.path.join(directory, filename)
            age_days = get_file_age_days(filepath)
            
            # Extract date from filename (YYYYMMDD format)
            try:
                # gasbuddy_droplet1_20251028_140530.csv -> 20251028
                date_str = filename.split('_')[2] if 'droplet' in filename else filename.split('_')[1]
                year = date_str[:4]
                month = date_str[4:6]
            except:
                year = 'unknown'
                month = 'unknown'
            
            # Create archive directory structure
            archive_subdir = os.path.join(ARCHIVE_DIR, year, month)
            os.makedirs(archive_subdir, exist_ok=True)
            
            # Archive files older than threshold
            if age_days > ARCHIVE_AGE_DAYS:
                dest_path = os.path.join(archive_subdir, filename)
                
                if not os.path.exists(dest_path):
                    shutil.move(filepath, dest_path)
                    print(f"  📦 Archived: {filename} ({age_days} days old)")
                    archived_count += 1
                else:
                    print(f"  ⚠️  Skipped (already archived): {filename}")
            
            # Compress files older than compression threshold (in archive)
            elif age_days > COMPRESS_AGE_DAYS and filename.endswith('.csv'):
                if compress_file(filepath):
                    print(f"  🗜️  Compressed: {filename} ({age_days} days old)")
                    compressed_count += 1
        
        print()
    
    print(f"✅ Archived: {archived_count} files")
    print(f"✅ Compressed: {compressed_count} files")
    print()

def cleanup_old_logs():
    """Delete logs older than threshold"""
    print("="*70)
    print("🧹 CLEANING UP OLD LOGS")
    print("="*70)
    print()
    
    if not os.path.exists(LOGS_DIR):
        print("  No logs directory found")
        print()
        return
    
    deleted_count = 0
    
    for filename in os.listdir(LOGS_DIR):
        filepath = os.path.join(LOGS_DIR, filename)
        
        if not os.path.isfile(filepath):
            continue
        
        age_days = get_file_age_days(filepath)
        
        if age_days > DELETE_LOGS_DAYS:
            os.remove(filepath)
            print(f"  🗑️  Deleted log: {filename} ({age_days} days old)")
            deleted_count += 1
    
    print()
    print(f"✅ Deleted: {deleted_count} log files")
    print()

def cleanup_old_runs():
    """Archive old run metadata"""
    print("="*70)
    print("🗂️  ARCHIVING OLD RUN METADATA")
    print("="*70)
    print()
    
    if not os.path.exists(RUNS_DIR):
        print("  No runs directory found")
        print()
        return
    
    archived_count = 0
    
    for filename in os.listdir(RUNS_DIR):
        filepath = os.path.join(RUNS_DIR, filename)
        
        if not os.path.isfile(filepath):
            continue
        
        age_days = get_file_age_days(filepath)
        
        # Archive run metadata older than 90 days
        if age_days > ARCHIVE_AGE_DAYS:
            # Extract date from filename
            try:
                date_str = filename.split('_')[1]  # Get YYYYMMDD
                year = date_str[:4]
                month = date_str[4:6]
            except:
                year = 'unknown'
                month = 'unknown'
            
            archive_subdir = os.path.join(ARCHIVE_DIR, year, month, 'runs')
            os.makedirs(archive_subdir, exist_ok=True)
            
            dest_path = os.path.join(archive_subdir, filename)
            
            if not os.path.exists(dest_path):
                shutil.move(filepath, dest_path)
                print(f"  📦 Archived: {filename}")
                archived_count += 1
    
    print()
    print(f"✅ Archived: {archived_count} run metadata files")
    print()

def show_disk_usage():
    """Display current disk usage"""
    print("="*70)
    print("💾 DISK USAGE SUMMARY")
    print("="*70)
    print()
    
    for directory in [DATA_DIR, MERGED_DIR, LOGS_DIR, RUNS_DIR, ARCHIVE_DIR]:
        if os.path.exists(directory):
            size_mb = get_directory_size(directory)
            size_gb = size_mb / 1024
            print(f"  {os.path.basename(directory):20s}: {size_gb:6.2f} GB ({size_mb:,} MB)")
    
    # Total /opt/gasbuddy usage
    if os.path.exists(BASE_DIR):
        total_mb = get_directory_size(BASE_DIR)
        total_gb = total_mb / 1024
        print(f"  {'='*20}")
        print(f"  {'TOTAL':20s}: {total_gb:6.2f} GB ({total_mb:,} MB)")
    
    # Overall disk usage
    try:
        result = subprocess.run(
            "df /opt | tail -1",
            shell=True,
            capture_output=True,
            text=True
        )
        parts = result.stdout.split()
        disk_total = int(parts[1]) // (1024 * 1024)  # Convert to GB
        disk_used = int(parts[2]) // (1024 * 1024)
        disk_pct = parts[4]
        
        print()
        print(f"  /opt partition: {disk_used} GB / {disk_total} GB ({disk_pct})")
    except:
        pass
    
    print()

def main():
    """Run storage management"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*18 + "STORAGE MANAGEMENT & ARCHIVING" + " "*20 + "║")
    print("╚" + "="*68 + "╝")
    print()
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Show initial disk usage
    show_disk_usage()
    
    # Run cleanup tasks
    archive_old_csvs()
    cleanup_old_logs()
    cleanup_old_runs()
    
    # Show final disk usage
    print("="*70)
    print("📊 FINAL DISK USAGE")
    print("="*70)
    print()
    show_disk_usage()
    
    # Summary
    print("="*70)
    print("✅ STORAGE MANAGEMENT COMPLETE")
    print("="*70)
    print()
    print("Actions taken:")
    print(f"  ✅ CSVs older than {ARCHIVE_AGE_DAYS} days → archived")
    print(f"  ✅ CSVs older than {COMPRESS_AGE_DAYS} days → compressed")
    print(f"  ✅ Logs older than {DELETE_LOGS_DAYS} days → deleted")
    print(f"  ✅ Run metadata older than {ARCHIVE_AGE_DAYS} days → archived")
    print()
    print("Archive location: /opt/gasbuddy/archive/YYYY/MM/")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

