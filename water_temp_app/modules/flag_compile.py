import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from utils import file_manager
import os
import pdfplumber
import re
from datetime import datetime, timedelta

def extract_times_from_pdf(pdf_file):
    times = {}
    text = ""
    try:
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        return times

    # Regex for Time-in and Time-out
    # User example: "Time-in 14:46 (-7 GMT)"
    time_in_match = re.search(r"Time-in\s*[:]?\s*(\d{1,2}:\d{2})", text, re.IGNORECASE)
    time_out_match = re.search(r"Time-out\s*[:]?\s*(\d{1,2}:\d{2})", text, re.IGNORECASE)
    
    # Regex for Date
    # Prioritize "Date:" or "Visit Date:" label
    date_match = re.search(r"(?:Date|Visit Date)\s*[:]?\s*(\d{4}-\d{2}-\d{2})", text, re.IGNORECASE)
    if not date_match:
        date_match = re.search(r"(?:Date|Visit Date)\s*[:]?\s*(\d{1,2}/\d{1,2}/\d{2,4})", text, re.IGNORECASE)
    
    # Fallback to any date if no label found (but this might pick up print dates)
    if not date_match:
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", text) # YYYY-MM-DD
    if not date_match:
        date_match = re.search(r"(\d{1,2}/\d{1,2}/\d{2,4})", text) # MM/DD/YYYY
    
    if time_in_match:
        times['in'] = time_in_match.group(1)
    if time_out_match:
        times['out'] = time_out_match.group(1)
    if date_match:
        times['date'] = date_match.group(1)
        
    return times

def app():
    st.header("Flag & Compile Data")

    # 1. Select Formatted Data (From Session State)
    st.subheader("1. Select Formatted Data")
    
    df = None
    selected_file = "Session Data"
    
    if 'formatted_df' in st.session_state:
        df = st.session_state['formatted_df']
        selected_file = st.session_state.get('formatted_filename', "Session Data")
        st.success(f"Loaded data from previous step: {selected_file}")
    else:
        # Legacy fallback
        formatted_files = file_manager.list_files(subfolder="01_Data/01_Raw_Formatted", pattern=".csv")
        if formatted_files:
             st.info("No data in session. You can select a previously formatted file (Legacy Mode).")
             selected_file = st.selectbox("Choose File", formatted_files)
             if selected_file:
                 df = file_manager.load_data(selected_file, subfolder="01_Data/01_Raw_Formatted")
        else:
            st.warning("No formatted data found in session. Please go to 'Format Data' and run the formatting step.")
            return

    if df is not None:
        if df is not None:
            # Ensure timestamp is datetime
            if 'timestamp' in df.columns:
                # Use format='mixed' to handle various formats and silence warnings
                # Try parsing with explicit formats to avoid ambiguity (e.g. YY-MM-DD vs DD-MM-YY)
                try:
                    # Try 2-digit year first (common in raw logger files: 24-08-14)
                    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%y-%m-%d %H:%M:%S', errors='raise')
                except (ValueError, TypeError):
                    try:
                        # Try 4-digit year (ISO: 2024-08-14)
                        df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S', errors='raise')
                    except (ValueError, TypeError):
                        # Fallback to mixed/coerce if explicit formats fail
                        df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed', errors='coerce')
            else:
                st.error("Column 'timestamp' not found in file.")
                return

            # Round to nearest 15 minutes to align with grid
            df['timestamp'] = df['timestamp'].dt.round('15min')

            st.write(f"Loaded {len(df)} rows.")
            
            # 2. User Inputs for QAQC
            st.subheader("2. QAQC Parameters")
            col1, col2 = st.columns(2)
            with col1:
                spike_threshold = st.number_input("Spike Threshold (deg C)", value=0.8, disabled=True)
                roll_diff_threshold = st.number_input("Rolling Diff Threshold (deg C)", value=1.5, disabled=True)
                stdev_threshold = st.number_input("Standard Deviation Threshold", value=2.0, disabled=True)
            with col2:
                min_temp = st.number_input("Min Temperature", value=-20.0, disabled=True)
                max_temp = st.number_input("Max Temperature", value=50.0, disabled=True)
                high_temp_threshold = st.number_input("High Temp Warning", value=35.0, disabled=True)
                diurnal_threshold = st.number_input("Diurnal Range Threshold", value=10.0, disabled=True)

            # Calculate default Visit Times from data
            default_in_val = "2025-09-18 17:27"
            default_out_val = "2025-09-18 17:37"
            
            if not df.empty and 'timestamp' in df.columns:
                try:
                    last_ts = df['timestamp'].max()
                    # User requested: "take the last time recorded, then subtract an hour"
                    # "field time out would be the last data point recorded"
                    default_out_dt = last_ts
                    default_in_dt = last_ts - pd.Timedelta(hours=1)
                    
                    default_out_val = default_out_dt.strftime("%Y-%m-%d %H:%M")
                    default_in_val = default_in_dt.strftime("%Y-%m-%d %H:%M")
                except Exception as e:
                    pass

            # 3. Missing Data Padding & Processing Mode
            # Moved up to allow historical data to inform Previous Visit Times
            st.subheader("3. Missing Data Padding")
            
            # Processing Mode Selection (Matches R script logic)
            st.markdown("#### Processing Mode")
            processing_mode = st.radio(
                "Select how to handle historical data overlap:", 
                options=["First Data Set", "Sequential", "Logger Swap"],
                index=1, # Default to Sequential
                help="First Data Set: No historical padding. Sequential: Matches Station & Serial. Logger Swap: Matches Station only."
            )
            
            enable_padding = st.checkbox("Fill Missing Timestamps", value=True)
            
            # Calculate default start date from Historical Data
            default_pad_start = ""
            hist_end = None # Initialize
            
            # Try to find historical files in 02_Tidy based on mode
            if processing_mode in ["Sequential", "Logger Swap"]:
                try:
                    # Get station and serial from current dataframe
                    current_station = df['station_code'].iloc[0] if 'station_code' in df.columns else ""
                    current_serial = df['logger_serial'].iloc[0] if 'logger_serial' in df.columns else ""
                    
                    if current_station:
                        # List all tidy files
                        tidy_files = file_manager.list_files(subfolder="01_Data/02_Tidy", pattern=".csv")
                        
                        # Filter logic based on mode
                        if processing_mode == "Logger Swap":
                            # Relaxed: Match Station Code only
                            matching_files = [f for f in tidy_files if f.startswith(f"{current_station}_tidy_")]
                        else: # Sequential
                            # Strict: Match Station Code AND Serial Number
                            matching_files = [f for f in tidy_files if f.startswith(f"{current_station}_tidy_") and str(current_serial) in f]
                        
                        if matching_files:
                            # Sort by date extracted from filename, then by filename
                            def extract_date_key(f):
                                # Extract date from end of filename (YYYYMMDD)
                                match = re.search(r"_(\d{8})\.csv$", f)
                                date_val = match.group(1) if match else "00000000"
                                return (date_val, f)

                            matching_files.sort(key=extract_date_key)
                            latest_file = matching_files[-1]
                            
                            # Load the last few rows of the latest file to get the end date
                            hist_df = file_manager.load_data(latest_file, subfolder="01_Data/02_Tidy")
                            if hist_df is not None and 'timestamp' in hist_df.columns:
                                hist_df['timestamp'] = pd.to_datetime(hist_df['timestamp'])
                                hist_end = hist_df['timestamp'].max()
                                
                                # Always set start date based on historical end + 15 mins
                                # This handles both gaps (padding) and overlaps (trimming)
                                default_start_dt = hist_end + pd.Timedelta(minutes=15)
                                default_pad_start = default_start_dt.strftime("%Y-%m-%d %H:%M:%S")
                                
                                # We need current_start_check to be defined before using it
                                current_start_check = df['timestamp'].min()
                                
                                if hist_end < current_start_check:
                                    st.info(f"Auto-detected start from historical file ({latest_file}): {default_pad_start}")
                                else:
                                    st.warning(f"Historical file ({latest_file}) overlaps with current data. Start date set to {default_pad_start} to trim overlap.")
                        else:
                            st.warning(f"No historical files found for mode: {processing_mode}")
                            
                except Exception as e:
                    # print(e) # Debug
                    pass

            if enable_padding:
                col_pad1, col_pad2 = st.columns(2)
                with col_pad1:
                    pad_interval = st.text_input("Interval (e.g., '15min')", value="15min")
                with col_pad2:
                    # Use dynamic key to force update when mode changes
                    pad_start = st.text_input(
                        "Record Start Date", 
                        value=default_pad_start, 
                        key=f"pad_start_{processing_mode}",
                        help="Auto-filled based on Processing Mode. Manually enter to override."
                    )

            # Visit Times (for V flag)
            st.subheader("Field Visit Times")
            
            # PDF Upload for Current Visit
            visit_pdf = st.file_uploader("open pdf to populate fieldtimes", type="pdf", key="visit_pdf")
            convert_utc = st.checkbox("convert it to UTC", value=False, key="convert_utc_visit")
            
            if visit_pdf:
                try:
                    extracted = extract_times_from_pdf(visit_pdf)
                    
                    # Determine Date base
                    base_date_str = default_in_val.split(" ")[0] if default_in_val else pd.Timestamp.now().strftime("%Y-%m-%d")
                    if 'date' in extracted:
                        try:
                            d = pd.to_datetime(extracted['date'])
                            base_date_str = d.strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    # Process Time In
                    if 'in' in extracted:
                        dt_in_str = f"{base_date_str} {extracted['in']}"
                        if convert_utc:
                            try:
                                dt_obj = pd.to_datetime(dt_in_str)
                                dt_obj += pd.Timedelta(hours=7)
                                default_in_val = dt_obj.strftime("%Y-%m-%d %H:%M")
                            except:
                                default_in_val = dt_in_str
                        else:
                            default_in_val = dt_in_str
                            
                    # Process Time Out
                    if 'out' in extracted:
                        dt_out_str = f"{base_date_str} {extracted['out']}"
                        if convert_utc:
                            try:
                                dt_obj = pd.to_datetime(dt_out_str)
                                dt_obj += pd.Timedelta(hours=7)
                                default_out_val = dt_obj.strftime("%Y-%m-%d %H:%M")
                            except:
                                default_out_val = dt_out_str
                        else:
                            default_out_val = dt_out_str
                            
                    st.success("Times extracted from PDF!")
                except Exception as e:
                    st.error(f"Failed to extract from PDF: {e}")
            visit_col1, visit_col2 = st.columns(2)
            with visit_col1:
                datetime_in = st.text_input("Datetime In (YYYY-MM-DD HH:MM)", value=default_in_val)
            with visit_col2:
                datetime_out = st.text_input("Datetime Out (YYYY-MM-DD HH:MM)", value=default_out_val)
            
            # Previous Visit Times (for V flag on historical overlap)
            st.subheader("Previous Field Visit Times (Optional)")
            
            prev_in_val = ""
            prev_out_val = ""

            # PDF Upload for Previous Visit
            prev_visit_pdf = st.file_uploader("open pdf to populate fieldtimes", type="pdf", key="prev_visit_pdf")
            prev_convert_utc = st.checkbox("convert it to UTC", value=False, key="convert_utc_prev")
            
            if prev_visit_pdf:
                try:
                    extracted = extract_times_from_pdf(prev_visit_pdf)
                    
                    # Determine Date base
                    base_date_str = prev_in_val.split(" ")[0] if prev_in_val else pd.Timestamp.now().strftime("%Y-%m-%d")
                    if 'date' in extracted:
                        try:
                            d = pd.to_datetime(extracted['date'])
                            base_date_str = d.strftime("%Y-%m-%d")
                        except:
                            pass
                    
                    # Process Time In
                    if 'in' in extracted:
                        dt_in_str = f"{base_date_str} {extracted['in']}"
                        if prev_convert_utc:
                            try:
                                dt_obj = pd.to_datetime(dt_in_str)
                                dt_obj += pd.Timedelta(hours=7)
                                prev_in_val = dt_obj.strftime("%Y-%m-%d %H:%M")
                            except:
                                prev_in_val = dt_in_str
                        else:
                            prev_in_val = dt_in_str
                            
                    # Process Time Out
                    if 'out' in extracted:
                        dt_out_str = f"{base_date_str} {extracted['out']}"
                        if prev_convert_utc:
                            try:
                                dt_obj = pd.to_datetime(dt_out_str)
                                dt_obj += pd.Timedelta(hours=7)
                                prev_out_val = dt_obj.strftime("%Y-%m-%d %H:%M")
                            except:
                                prev_out_val = dt_out_str
                        else:
                            prev_out_val = dt_out_str
                            
                    st.success("Times extracted from PDF!")
                except Exception as e:
                    st.error(f"Failed to extract from PDF: {e}")

            st.info("Use this to flag data from a previous visit if it overlaps with this dataset.")
            
            # Auto-fill logic for No FastField Form
            no_fastfield = st.checkbox("No FastField Form (Auto-fill from Historical Data)")
            
            if no_fastfield:
                if hist_end is not None:
                    # Logic: 
                    # Base = hist_end + 15 mins (Start of new record)
                    # Prev In = Base - 1 hour
                    # Prev Out = Prev In + 1 hour 45 mins
                    
                    base_dt = hist_end + pd.Timedelta(minutes=15)
                    auto_prev_in = base_dt - pd.Timedelta(hours=1)
                    auto_prev_out = auto_prev_in + pd.Timedelta(hours=1, minutes=45)
                    
                    prev_in_val = auto_prev_in.strftime("%Y-%m-%d %H:%M")
                    prev_out_val = auto_prev_out.strftime("%Y-%m-%d %H:%M")
                    st.success(f"Auto-filled Previous Visit Times based on historical end: {hist_end}")
                else:
                    st.warning("No historical data found to auto-fill.")

            prev_col1, prev_col2 = st.columns(2)
            with prev_col1:
                prev_datetime_in = st.text_input("Prev Datetime In (YYYY-MM-DD HH:MM)", value=prev_in_val)
            with prev_col2:
                prev_datetime_out = st.text_input("Prev Datetime Out (YYYY-MM-DD HH:MM)", value=prev_out_val)

            # 4. Run QAQC
            if st.button("Run QAQC"):
                try:
                    # Convert visit times
                    dt_in = pd.to_datetime(datetime_in)
                    dt_out = pd.to_datetime(datetime_out)
                    
                    # Sort by timestamp
                    df = df.sort_values('timestamp')
                    # Apply Padding / Trimming
                    if enable_padding:
                        # Determine start/end
                        current_start = df['timestamp'].min()
                        current_end = df['timestamp'].max()
                        
                        # Determine start/end
                        current_start = df['timestamp'].min()
                        current_end = df['timestamp'].max()
                        
                        # Determine start/end
                        current_start = df['timestamp'].min()
                        current_end = df['timestamp'].max()
                        
                        if pad_start:
                            start_dt = pd.to_datetime(pad_start)
                            
                            # TRIM: If start_dt is LATER than current_start, filter out earlier data
                            # This prevents overlap with historical data
                            if start_dt > current_start:
                                st.info(f"Trimming data before {start_dt} to prevent overlap.")
                                df = df[df['timestamp'] >= start_dt].copy()
                                current_start = start_dt # Update current start
                            
                            # PAD: If start_dt is EARLIER than current_start, extend range
                            elif start_dt < current_start:
                                st.info(f"Padding data from {start_dt} to {current_start}")
                                current_start = start_dt
                        
                        # Create full range
                        full_range = pd.date_range(start=current_start, end=current_end, freq=pad_interval)
                        
                        # Use merge instead of reindex to handle potential duplicates from rounding
                        df_grid = pd.DataFrame({'timestamp': full_range})
                        df = pd.merge(df_grid, df, on='timestamp', how='left')
                        
                        # Mark missing values
                        # If wtmp is NaN and wtmp_flag is NaN (newly created row), set flag to 'M'
                        # We need to be careful not to overwrite existing flags if they exist
                        # But reindex creates NaNs for all columns.
                        
                        # Identify rows that were added (wtmp is NaN)
                        # We assume if wtmp is NaN, it's missing. 
                        # But original data might have NaN wtmp.
                        # Let's use the fact that 'station_code' would also be NaN for new rows
                        
                        new_rows_mask = df['station_code'].isna()
                        df.loc[new_rows_mask, 'wtmp_flag'] = 'M'
                        
                        # Fill metadata for new rows
                        # We can forward fill or back fill, or just use the values from the dataframe
                        # Since we might have trimmed, we should take values from the first valid row
                        if not df.empty:
                            # Find first valid row to copy metadata from
                            valid_row = df.dropna(subset=['station_code']).iloc[0]
                            for col in ['station_code', 'utc_offset', 'logger_serial', 'data_id']:
                                if col in df.columns:
                                    df[col] = df[col].fillna(valid_row[col])
                    
                    # QAQC Logic
                    # 1. Flag 'N' (Not QAQC'd) - Initialize
                    if 'wtmp_flag' not in df.columns:
                        df['wtmp_flag'] = 'N'
                    
                    # Identify duplicates (timestamps appearing more than once)
                    # This happens if multiple raw rows rounded to the same 15min interval
                    duplicate_mask = df.duplicated(subset=['timestamp'], keep=False)
                    df.loc[duplicate_mask, 'wtmp_flag'] = 'D'
                    
                    # Fill NaNs in flag with 'N' (except 'M's we just made and 'D's)
                    # Note: 'M' rows have NaN wtmp_flag initially? 
                    # Wait, earlier we did: df.loc[new_rows_mask, 'wtmp_flag'] = 'M'
                    # So 'M' is already set.
                    # 'D' is now set.
                    # The rest are NaN.
                    df['wtmp_flag'] = df['wtmp_flag'].fillna('N')
                    
                    # Ensure wtmp is numeric (handle strings/mixed types from bad loads)
                    if 'wtmp' in df.columns:
                        df['wtmp'] = pd.to_numeric(df['wtmp'], errors='coerce')

                    # Calculate Stats
                    df['t_change'] = df['wtmp'].diff().abs().fillna(0)
                    df['t_change_lead'] = df['wtmp'].diff(-1).abs().fillna(0)
                    
                    # Rolling means
                    df['roll_mean_right'] = df['wtmp'].rolling(window=5, min_periods=1).mean()
                    df['diff_right'] = (df['wtmp'] - df['roll_mean_right']).abs()
                    
                    # Rolling mean left (reverse, roll, reverse)
                    df['roll_mean_left'] = df['wtmp'].iloc[::-1].rolling(window=5, min_periods=1).mean().iloc[::-1]
                    df['diff_left'] = (df['wtmp'] - df['roll_mean_left']).abs()
                    
                    # Rolling SD
                    df['stdev_right'] = df['wtmp'].rolling(window=2, min_periods=1).std()
                    df['stdev_left'] = df['wtmp'].iloc[::-1].rolling(window=2, min_periods=1).std().iloc[::-1]

                    # Initialize Flag Column
                    df['wtmp_flag'] = 'P' # Default Pass

                    # Apply Flags logic (Priority order matters, usually Error > Spike > Pass)
                    
                    # Spikes
                    spike_mask = (
                        (df['t_change'] >= spike_threshold) | 
                        (df['t_change_lead'] >= spike_threshold) |
                        (df['diff_right'] >= roll_diff_threshold) |
                        (df['diff_left'] >= roll_diff_threshold) |
                        (df['stdev_right'] >= stdev_threshold) |
                        (df['stdev_left'] >= stdev_threshold)
                    )
                    df.loc[spike_mask, 'wtmp_flag'] = 'S'
                    
                    # Error Range
                    error_mask = (df['wtmp'] < min_temp) | (df['wtmp'] > max_temp)
                    df.loc[error_mask, 'wtmp_flag'] = 'E'
                    
                    # High Temp
                    high_mask = (df['wtmp'] >= high_temp_threshold)
                    df.loc[high_mask, 'wtmp_flag'] = 'T'
                    
                    # Below Ice
                    ice_mask = (df['wtmp'] < 0.0)
                    df.loc[ice_mask, 'wtmp_flag'] = 'B'
                    
                    # Diurnal Range Check (Flag 'A' for Air/Dewatered)
                    # Group by date
                    df['date'] = df['timestamp'].dt.date
                    daily_stats = df.groupby('date')['wtmp'].agg(['max', 'min'])
                    daily_stats['range'] = daily_stats['max'] - daily_stats['min']
                    
                    # Identify bad days
                    bad_days = daily_stats[daily_stats['range'] > diurnal_threshold].index
                    
                    if not bad_days.empty:
                        # Create mask for all rows where date is in bad_days
                        diurnal_mask = df['date'].isin(bad_days)
                        df.loc[diurnal_mask, 'wtmp_flag'] = 'A'
                        st.warning(f"Flagged {len(bad_days)} days as 'A' (Air/Dewatered) due to diurnal range > {diurnal_threshold}C")
                    
                    # Drop temporary date column
                    df = df.drop(columns=['date'])
                    
                    # Missing (M)
                    missing_mask = df['wtmp'].isna()
                    df.loc[missing_mask, 'wtmp_flag'] = 'M'
                    
                    # Visit (V)
                    # Match R logic: timestamp > dt_in (Strict inequality for start)
                    visit_mask = (df['timestamp'] > dt_in) & (df['timestamp'] <= dt_out)
                    df.loc[visit_mask, 'wtmp_flag'] = 'V'

                    # Previous Visit (V)
                    if prev_datetime_in and prev_datetime_out:
                        try:
                            prev_dt_in = pd.to_datetime(prev_datetime_in)
                            prev_dt_out = pd.to_datetime(prev_datetime_out)
                            # Match R logic: timestamp > prev_dt_in
                            prev_visit_mask = (df['timestamp'] > prev_dt_in) & (df['timestamp'] <= prev_dt_out)
                            
                            # Create mask for rows that are in range AND not M
                            apply_prev_mask = prev_visit_mask & (df['wtmp_flag'] != 'M')
                            df.loc[apply_prev_mask, 'wtmp_flag'] = 'V'
                            st.info(f"Applied 'V' flag for previous visit: {prev_dt_in} to {prev_dt_out}")
                        except Exception as e:
                            st.warning(f"Could not parse Previous Visit times: {e}")
                    
                    st.success("QAQC Complete!")
                    
                    # Store in session state
                    st.session_state['qaqc_df'] = df
                    st.session_state['qaqc_file'] = selected_file
                    
                    # Store metadata for report
                    st.session_state['qaqc_metadata'] = {
                        'field_in': datetime_in,
                        'field_out': datetime_out,
                        'prev_field_in': prev_datetime_in,
                        'prev_field_out': prev_datetime_out,
                        'record_start': df['timestamp'].min().strftime("%Y-%m-%d %H:%M:%S"),
                        'record_end': df['timestamp'].max().strftime("%Y-%m-%d %H:%M:%S")
                    }
                        
                except Exception as e:
                    st.error(f"Error during QAQC: {e}")

            # Check if results exist in session state
            if 'qaqc_df' in st.session_state and st.session_state.get('qaqc_file') == selected_file:
                df_qaqc = st.session_state['qaqc_df']
                
                # Plot
                st.subheader("Data Visualization")
                
                # Create a combined Line + Scatter plot
                fig = go.Figure()
                
                # 1. Add Line (All data)
                fig.add_trace(go.Scatter(
                    x=df_qaqc['timestamp'], 
                    y=df_qaqc['wtmp'], 
                    mode='lines',
                    name='Temperature',
                    line=dict(color='gray', width=1)
                ))
                
                colors = {
                    'P': 'green', 'S': 'red', 'E': 'purple', 
                    'T': 'orange', 'B': 'blue', 'M': 'darkred', 'V': 'pink',
                    'D': 'brown', 'A': 'black'
                }
                
                for flag, color in colors.items():
                    subset = df_qaqc[df_qaqc['wtmp_flag'] == flag]
                    if not subset.empty:
                        fig.add_trace(go.Scatter(
                            x=subset['timestamp'],
                            y=subset['wtmp'],
                            mode='markers',
                            name=f"Flag: {flag}",
                            marker=dict(color=color, size=6)
                        ))

                fig.update_layout(
                    title=f"Water Temperature QAQC - {selected_file}",
                    xaxis_title="Timestamp",
                    yaxis_title="Water Temperature",
                    hovermode="x unified"
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Save
                if st.button("Save Flagged Data"):
                    # Save to 02_Tidy or similar
                    # Filename: Station_tidy_Serial_Date.csv
                    station = df_qaqc['station_code'].iloc[0] if 'station_code' in df_qaqc.columns else "Unknown"
                    serial = df_qaqc['logger_serial'].iloc[0] if 'logger_serial' in df_qaqc.columns else "Unknown"

                    # Sanitize filename components to prevent filesystem errors (e.g. if serial is "n/a")
                    station = str(station).replace("/", "_").replace("\\", "_")
                    serial = str(serial).replace("/", "_").replace("\\", "_")
                    date_str = pd.Timestamp.now().strftime("%Y%m%d")
                    
                    save_name = f"{station}_tidy_{serial}_{date_str}.csv"
                    
                    # Store metadata in Session State ONLY
                    st.session_state['qaqc_metadata'] = {
                        'field_in': datetime_in,
                        'field_out': datetime_out,
                        'prev_field_in': prev_datetime_in,
                        'prev_field_out': prev_datetime_out,
                        'record_start': df_qaqc['timestamp'].min().strftime("%Y-%m-%d %H:%M:%S"),
                        'record_end': df_qaqc['timestamp'].max().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Filter columns to match standard tidy format (NO EXTRA METADATA COLUMNS)
                    cols_to_save = ['data_id', 'station_code', 'timestamp', 'utc_offset', 'logger_serial', 'wtmp', 'wtmp_flag']
                    
                    # Ensure we only try to select columns that actually exist
                    final_cols = [c for c in cols_to_save if c in df_qaqc.columns]
                    df_to_save = df_qaqc[final_cols].copy()

                    # FIX: Replace Temperature with "NAN" where flag is 'M'
                    if 'wtmp' in df_to_save.columns and 'wtmp_flag' in df_to_save.columns:
                        # Ensure wtmp is object data type so it can hold the string "NAN"
                        df_to_save['wtmp'] = df_to_save['wtmp'].astype(object)
                        m_mask = df_to_save['wtmp_flag'] == 'M'
                        df_to_save.loc[m_mask, 'wtmp'] = "NAN"
                    
                    saved_path = file_manager.save_data(df_to_save, save_name, subfolder="01_Data/02_Tidy")
                    st.success(f"Saved to {saved_path}")
                    
                    # Store the saved filename to link metadata in Report module
                    st.session_state['last_saved_tidy_file'] = save_name
                    
                    # Note: No longer saving metadata JSON sidecar as per user request.
                    st.info("Metadata stored in Session Memory. Proceed to Review/Report in THIS SESSION.")

