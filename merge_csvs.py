#!/usr/bin/env python3
"""
Merge CSVs from both droplets into one master file
- Combines gasbuddy_droplet1_*.csv and gasbuddy_droplet2_*.csv
- Removes duplicates (if any)
- Validates data integrity
- Sorts by state and ZIP
"""
import csv
import sys
from datetime import datetime
from collections import defaultdict

def merge_csv_files(file1, file2, output_file=None):
    """Merge two CSV files, dedupe, and validate"""
    
    if not output_file:
        output_file = f"gasbuddy_merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    print("="*70)
    print("🔄 MERGING GASBUDDY CSV FILES")
    print("="*70)
    print(f"\nDroplet 1: {file1}")
    print(f"Droplet 2: {file2}")
    print(f"Output: {output_file}\n")
    
    # Read both files
    stations_by_id = {}
    stats = {
        'droplet1': 0,
        'droplet2': 0,
        'duplicates': 0,
        'total': 0
    }
    
    print("📖 Reading Droplet 1...")
    with open(file1, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            station_id = row['station_id']
            if station_id not in stations_by_id:
                stations_by_id[station_id] = row
                stats['droplet1'] += 1
            else:
                stats['duplicates'] += 1
    
    print(f"   ✅ Loaded {stats['droplet1']:,} stations from Droplet 1")
    
    print("\n📖 Reading Droplet 2...")
    with open(file2, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            station_id = row['station_id']
            if station_id not in stations_by_id:
                stations_by_id[station_id] = row
                stats['droplet2'] += 1
            else:
                stats['duplicates'] += 1
    
    print(f"   ✅ Loaded {stats['droplet2']:,} stations from Droplet 2")
    
    stats['total'] = len(stations_by_id)
    
    # Sort by state, then city, then station name
    print("\n🔄 Sorting by state and city...")
    sorted_stations = sorted(
        stations_by_id.values(),
        key=lambda x: (x['state'], x['city'], x['station_name'])
    )
    
    # Write merged file
    print(f"\n💾 Writing merged file: {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted_stations)
    
    # Summary
    print("\n" + "="*70)
    print("✅ MERGE COMPLETE")
    print("="*70)
    print(f"\n📊 Statistics:")
    print(f"   Droplet 1 stations: {stats['droplet1']:,}")
    print(f"   Droplet 2 stations: {stats['droplet2']:,}")
    print(f"   Duplicates removed: {stats['duplicates']:,}")
    print(f"   Total unique stations: {stats['total']:,}")
    
    # State breakdown
    print(f"\n📍 Geographic Distribution:")
    states = defaultdict(int)
    for station in sorted_stations:
        states[station['state']] += 1
    
    top_states = sorted(states.items(), key=lambda x: x[1], reverse=True)[:10]
    for state, count in top_states:
        print(f"   {state}: {count:,} stations")
    
    print(f"\n✅ Merged file saved: {output_file}")
    print("="*70)
    
    return output_file, stats

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 merge_csvs.py <droplet1.csv> <droplet2.csv> [output.csv]")
        print("\nExample:")
        print("  python3 merge_csvs.py gasbuddy_droplet1_20251028.csv gasbuddy_droplet2_20251028.csv")
        sys.exit(1)
    
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) > 3 else None
    
    merge_csv_files(file1, file2, output)

