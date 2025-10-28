#!/usr/bin/env python3
"""
Split all_us_zips.txt into two equal halves for dual-droplet architecture.
Ensures clean split with no overlap or gaps.
"""

def split_zip_list():
    """Split ZIP codes into two files for droplet 1 and droplet 2."""
    
    # Read all ZIPs
    with open('all_us_zips.txt', 'r') as f:
        all_zips = [line.strip() for line in f if line.strip()]
    
    total = len(all_zips)
    midpoint = total // 2
    
    # Split into two halves
    droplet1_zips = all_zips[:midpoint]
    droplet2_zips = all_zips[midpoint:]
    
    # Write droplet 1 ZIPs
    with open('droplet1_zips.txt', 'w') as f:
        for zip_code in droplet1_zips:
            f.write(f"{zip_code}\n")
    
    # Write droplet 2 ZIPs
    with open('droplet2_zips.txt', 'w') as f:
        for zip_code in droplet2_zips:
            f.write(f"{zip_code}\n")
    
    # Verification
    print("=" * 60)
    print("ZIP CODE SPLIT VERIFICATION")
    print("=" * 60)
    print(f"\n📊 Total US ZIPs: {total:,}")
    print(f"\n🔵 Droplet 1: {len(droplet1_zips):,} ZIPs")
    print(f"   Range: {droplet1_zips[0]} to {droplet1_zips[-1]}")
    print(f"   File: droplet1_zips.txt")
    print(f"\n🟢 Droplet 2: {len(droplet2_zips):,} ZIPs")
    print(f"   Range: {droplet2_zips[0]} to {droplet2_zips[-1]}")
    print(f"   File: droplet2_zips.txt")
    
    # Check for overlap
    set1 = set(droplet1_zips)
    set2 = set(droplet2_zips)
    overlap = set1 & set2
    
    if overlap:
        print(f"\n❌ ERROR: {len(overlap)} overlapping ZIPs found!")
        print(f"   First few: {list(overlap)[:5]}")
    else:
        print(f"\n✅ No overlap - clean split confirmed")
    
    # Check for gaps
    combined = set1 | set2
    if len(combined) == total:
        print(f"✅ All {total:,} ZIPs accounted for - no gaps")
    else:
        print(f"❌ ERROR: {total - len(combined)} ZIPs missing!")
    
    print("\n" + "=" * 60)
    print("✅ ZIP split complete and verified")
    print("=" * 60)

if __name__ == "__main__":
    split_zip_list()

