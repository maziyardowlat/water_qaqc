#!/usr/bin/env python3
"""
fix_manta_dates.py
------------------
Fixes incorrectly parsed dates in the Manta Masterfile CSV.

Problem Description:
--------------------
Starting around 2024-07-01, the date format in the source data changed from YYYY-MM-DD to DD/MM/YY.
However, when parsed incorrectly, the DD/MM/YY format was interpreted as MM/DD/YY.

This affects the FIRST 12 DAYS of EVERY MONTH from July 2024 onwards:
  - 01/07/24 (July 1st) was parsed as 2024-01-07 (January 7th)
  - 02/07/24 (July 2nd) was parsed as 2024-02-07 (February 7th)
  - ...
  - 12/07/24 (July 12th) was parsed as 2024-12-07 (December 7th)
  - 13/07/24 (July 13th) was correctly parsed as 2024-07-13

This pattern repeats EVERY MONTH:
  - 01/08/24 (Aug 1st) was parsed as 2024-01-08 (January 8th)
  - 11/12/25 (Dec 11th) was parsed as 2025-11-12 → but stored as 2025-12-11 (wrong)
  
The key insight: for days 1-12, the day and month are SWAPPED.

Solution:
---------
After 2024-06-30 (the last correctly formatted date), scan through the data.
When we detect a date that appears to be out of chronological order (jumps backwards),
and the day is between 1-12, swap the day and month to correct it.

Author: Auto-generated for BiocBot data pipeline
"""

import pandas as pd
from datetime import datetime, timedelta
import os
import sys


def fix_manta_dates(input_path, output_path=None, backup=True):
    """
    Fix incorrectly parsed dates in the Manta Masterfile.
    
    The issue: From July 2024 onwards, for the first 12 days of each month,
    the day and month values are swapped (DD/MM was parsed as MM/DD).
    
    Parameters:
    -----------
    input_path : str
        Path to the input CSV file (Manta Masterfile.csv)
    output_path : str, optional
        Path for the corrected output file. If None, overwrites input file.
    backup : bool, default True
        If True, creates a backup of the original file before modifying.
        
    Returns:
    --------
    dict
        Summary of corrections made:
        - 'rows_corrected': number of rows with date corrections
        - 'corrections_by_month': breakdown of corrections per actual month
    """
    
    # Validate input file exists
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
    
    # Set output path if not provided
    if output_path is None:
        output_path = input_path
    
    print(f"Reading CSV from: {input_path}")
    
    # Read the CSV file
    df = pd.read_csv(input_path, low_memory=False)
    
    # Ensure 'Datetime' column exists
    if 'Datetime' not in df.columns:
        raise ValueError("CSV file must have a 'Datetime' column")
    
    # Store original row count
    original_count = len(df)
    print(f"Total rows: {original_count}")
    
    # Parse Datetime column
    df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
    
    # Find the index of the last 2024-06-30 entry (last correctly formatted date)
    last_june_mask = (df['Datetime'].dt.year == 2024) & \
                     (df['Datetime'].dt.month == 6) & \
                     (df['Datetime'].dt.day == 30)
    
    last_june_indices = df[last_june_mask].index.tolist()
    
    if not last_june_indices:
        print("Warning: Could not find 2024-06-30 entries. The data may already be corrected.")
        return {'rows_corrected': 0, 'corrections_by_month': {}}
    
    # Get the last index of June 30, 2024
    last_june_idx = max(last_june_indices)
    print(f"Last 2024-06-30 entry at index: {last_june_idx}")
    
    # Track corrections
    corrections_made = 0
    corrections_by_month = {}  # Track corrected month counts
    samples_before_after = []  # Store samples for debugging
    
    # Process all rows after June 30, 2024
    print(f"Processing rows from index {last_june_idx + 1} to end of file...")
    print("Looking for dates where day ≤ 12 that need swapping...")
    
    # Track the last CORRECTED date to maintain proper chronological order
    # Start with the last known good date
    last_good_dt = df.loc[last_june_idx, 'Datetime']
    
    for idx in range(last_june_idx + 1, len(df)):
        dt = df.loc[idx, 'Datetime']
        
        if pd.isna(dt):
            continue
        
        current_day = dt.day
        current_month = dt.month
        
        # Only dates with day 1-12 AND month 1-12 could have the swap issue
        if current_day <= 12 and current_month <= 12:
            # Create the hypothetically corrected date (swap day and month)
            try:
                swapped_dt = dt.replace(month=current_day, day=current_month)
            except ValueError:
                # Invalid date after swap (e.g., trying to create Feb 30th) - skip
                # Update last_good_dt and continue
                last_good_dt = dt
                continue
            
            # Check if swapping is needed using multiple heuristics:
            # 1. If the current date is BEFORE July 2024 (impossible after June 30, 2024)
            # 2. If swapping produces a date closer to last_good_dt
            
            july_2024 = datetime(2024, 7, 1)
            
            # Heuristic 1: Date goes backwards to before July 2024
            if dt < july_2024 and swapped_dt >= july_2024:
                # This date is clearly wrong (went back in time before the problem started)
                needs_swap = True
            else:
                # Heuristic 2: Compare distances to last good date
                # The correct date should be close to last_good_dt (within ~1 day for 30-min data)
                diff_to_current = abs((dt - last_good_dt).total_seconds())
                diff_to_swapped = abs((swapped_dt - last_good_dt).total_seconds())
                
                # Swap if: swapped is closer AND swapped is within 1 day of last good date
                needs_swap = (diff_to_swapped < diff_to_current and 
                              diff_to_swapped <= 86400)  # 1 day in seconds
            
            if needs_swap:
                # Perform the swap
                if len(samples_before_after) < 20:
                    samples_before_after.append({
                        'idx': idx,
                        'before': dt.strftime('%Y-%m-%d %H:%M:%S'),
                        'after': swapped_dt.strftime('%Y-%m-%d %H:%M:%S')
                    })
                
                # Track by corrected month
                month_key = f"{swapped_dt.year}-{swapped_dt.month:02d}"
                corrections_by_month[month_key] = corrections_by_month.get(month_key, 0) + 1
                
                # Update the DataFrame
                df.loc[idx, 'Datetime'] = swapped_dt
                corrections_made += 1
                
                # Update last_good_dt with the CORRECTED date
                last_good_dt = swapped_dt
            else:
                # No swap needed, update last_good_dt with current date
                last_good_dt = dt
        else:
            # Day > 12, no swap possible, update last_good_dt
            last_good_dt = dt
    
    print(f"\nCorrections made: {corrections_made}")
    
    if samples_before_after:
        print("\nSample corrections:")
        for sample in samples_before_after[:10]:
            print(f"  Row {sample['idx']}: {sample['before']} → {sample['after']}")
    
    if corrections_made > 0:
        print(f"\nCorrections by month:")
        for month, count in sorted(corrections_by_month.items()):
            print(f"  {month}: {count} rows")
        
        # Create backup if requested
        if backup and output_path == input_path:
            backup_path = input_path.replace('.csv', '_backup.csv')
            print(f"\nCreating backup at: {backup_path}")
            # Read original and save backup
            df_backup = pd.read_csv(input_path, low_memory=False)
            df_backup.to_csv(backup_path, index=False)
        
        # Format the Datetime column back to string format for CSV
        df['Datetime'] = df['Datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Save the corrected data
        print(f"Saving corrected data to: {output_path}")
        df.to_csv(output_path, index=False)
        
        return {
            'rows_corrected': corrections_made,
            'corrections_by_month': corrections_by_month
        }
    else:
        print("No corrections needed. Data may already be fixed.")
        return {
            'rows_corrected': 0,
            'corrections_by_month': {}
        }


def preview_corrections(input_path, num_samples=20):
    """
    Preview the corrections that would be made without modifying the file.
    
    Parameters:
    -----------
    input_path : str
        Path to the input CSV file
    num_samples : int
        Number of sample corrections to display
        
    Returns:
    --------
    pd.DataFrame
        DataFrame showing before/after for sample rows
    """
    
    print(f"Previewing corrections for: {input_path}")
    
    df = pd.read_csv(input_path)
    df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
    
    # Find last June 30, 2024 entry
    last_june_mask = (df['Datetime'].dt.year == 2024) & \
                     (df['Datetime'].dt.month == 6) & \
                     (df['Datetime'].dt.day == 30)
    last_june_indices = df[last_june_mask].index.tolist()
    
    if not last_june_indices:
        print("No correction needed - could not find 2024-06-30 entries")
        return None
    
    last_june_idx = max(last_june_indices)
    
    # Collect samples using the same logic as fix_manta_dates
    samples = []
    
    for idx in range(last_june_idx + 1, len(df)):
        if len(samples) >= num_samples:
            break
            
        dt = df.loc[idx, 'Datetime']
        
        if pd.isna(dt):
            continue
        
        current_day = dt.day
        current_month = dt.month
        
        if current_day <= 12 and current_month <= 12:
            try:
                swapped_dt = dt.replace(month=current_day, day=current_month)
            except ValueError:
                continue
            
            if swapped_dt >= datetime(2024, 7, 1):
                if idx > last_june_idx + 1:
                    prev_dt = df.loc[idx - 1, 'Datetime']
                    if pd.notna(prev_dt):
                        diff_to_current = abs((dt - prev_dt).total_seconds())
                        diff_to_swapped = abs((swapped_dt - prev_dt).total_seconds())
                        
                        if diff_to_swapped < diff_to_current and diff_to_swapped <= 86400:
                            samples.append({
                                'Row Index': idx,
                                'Original Date': dt.strftime('%Y-%m-%d %H:%M:%S'),
                                'Corrected Date': swapped_dt.strftime('%Y-%m-%d %H:%M:%S'),
                            })
    
    if samples:
        preview_df = pd.DataFrame(samples)
        print("\n=== Preview of Sample Corrections ===")
        print(preview_df.to_string(index=False))
        
        # Count total corrections
        total_corrections = 0
        for idx in range(last_june_idx + 1, len(df)):
            dt = df.loc[idx, 'Datetime']
            if pd.isna(dt):
                continue
            current_day = dt.day
            current_month = dt.month
            if current_day <= 12 and current_month <= 12:
                try:
                    swapped_dt = dt.replace(month=current_day, day=current_month)
                except ValueError:
                    continue
                if swapped_dt >= datetime(2024, 7, 1) and idx > last_june_idx + 1:
                    prev_dt = df.loc[idx - 1, 'Datetime']
                    if pd.notna(prev_dt):
                        diff_to_current = abs((dt - prev_dt).total_seconds())
                        diff_to_swapped = abs((swapped_dt - prev_dt).total_seconds())
                        if diff_to_swapped < diff_to_current and diff_to_swapped <= 86400:
                            total_corrections += 1
        
        print(f"\nTotal rows that would be corrected: {total_corrections}")
        return preview_df
    else:
        print("No corrections needed.")
        return None


def analyze_date_jumps(input_path, num_jumps=30):
    """
    Analyze the CSV for suspicious date jumps after June 30, 2024.
    Helps diagnose the date swapping pattern.
    
    Parameters:
    -----------
    input_path : str
        Path to the input CSV file
    num_jumps : int
        Number of suspicious jumps to display
    """
    
    print(f"Analyzing date jumps in: {input_path}")
    
    df = pd.read_csv(input_path)
    df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')
    
    # Find last June 30, 2024 entry
    last_june_mask = (df['Datetime'].dt.year == 2024) & \
                     (df['Datetime'].dt.month == 6) & \
                     (df['Datetime'].dt.day == 30)
    last_june_indices = df[last_june_mask].index.tolist()
    
    if not last_june_indices:
        print("Could not find 2024-06-30 entries")
        return
    
    last_june_idx = max(last_june_indices)
    
    print(f"\nAnalyzing rows after index {last_june_idx}...")
    print("\nSuspicious date jumps (where time difference > 1 day):\n")
    
    jumps_found = 0
    prev_dt = df.loc[last_june_idx, 'Datetime']
    
    for idx in range(last_june_idx + 1, len(df)):
        if jumps_found >= num_jumps:
            break
            
        dt = df.loc[idx, 'Datetime']
        
        if pd.isna(dt) or pd.isna(prev_dt):
            prev_dt = dt
            continue
        
        diff_seconds = (dt - prev_dt).total_seconds()
        diff_days = abs(diff_seconds) / 86400
        
        # Flag any jump greater than 1 day (suspicious)
        if diff_days > 1:
            print(f"Row {idx}: {prev_dt.strftime('%Y-%m-%d %H:%M')} → {dt.strftime('%Y-%m-%d %H:%M')} (jump: {diff_days:.1f} days)")
            
            # Show what swapping would produce
            if dt.day <= 12 and dt.month <= 12:
                try:
                    swapped = dt.replace(month=dt.day, day=dt.month)
                    print(f"         If swapped: {swapped.strftime('%Y-%m-%d %H:%M')}")
                except ValueError:
                    pass
            
            jumps_found += 1
        
        prev_dt = dt
    
    print(f"\nFound {jumps_found} suspicious jumps (showing first {num_jumps})")


if __name__ == '__main__':
    """
    Main script execution.
    
    Usage:
        python fix_manta_dates.py                    # Preview corrections
        python fix_manta_dates.py --analyze          # Analyze date jumps
        python fix_manta_dates.py --fix              # Apply corrections with backup
        python fix_manta_dates.py --fix --no-backup  # Apply corrections without backup
    """
    
    # Default path to the Manta Masterfile
    default_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        '01_Data', 'manta', 'Manta Masterfile.csv'
    )
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        if '--analyze' in sys.argv:
            # Analyze mode - show date jumps
            analyze_date_jumps(default_path)
        elif '--fix' in sys.argv:
            # Apply the fix
            backup = '--no-backup' not in sys.argv
            result = fix_manta_dates(default_path, backup=backup)
            print("\n=== Correction Summary ===")
            print(f"Total rows corrected: {result['rows_corrected']}")
            if result['corrections_by_month']:
                print("\nBy month:")
                for month, count in sorted(result['corrections_by_month'].items()):
                    print(f"  {month}: {count} rows")
        else:
            print(f"Usage: python {sys.argv[0]} [--preview] [--analyze] [--fix] [--no-backup]")
            print("  (no args)   : Preview corrections without modifying the file")
            print("  --analyze   : Analyze date jumps to diagnose the issue")
            print("  --fix       : Apply corrections to the file")
            print("  --no-backup : Don't create a backup (use with --fix)")
    else:
        # Preview mode (default)
        preview_corrections(default_path)
