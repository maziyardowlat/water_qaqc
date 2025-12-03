import streamlit as st
import pandas as pd
from utils import file_manager
import os
import re

def app():
    st.header("Format Raw Data")

    # Project Directory Selection
    st.sidebar.subheader("Settings")
    current_dir = file_manager.get_project_dir()
    new_dir = st.sidebar.text_input("Project Directory", value=current_dir)
    if new_dir != current_dir:
        if file_manager.set_project_dir(new_dir):
            st.sidebar.success(f"Directory set to: {new_dir}")
        else:
            st.sidebar.error("Invalid directory path")

    # File Upload
    uploaded_file = st.file_uploader("Choose CSV File", type=['csv', 'txt'])
    
    if uploaded_file is not None:
        # Skip Rows
        skip_rows = st.number_input("Rows to Skip", min_value=0, value=1)
        
        try:
            # Read CSV
            # Reset file pointer to 0 before reading again if needed, but pandas handles it usually
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, skiprows=skip_rows)
            
            # Filter "Logged" rows (from R script logic)
            # R: df[apply(df, 1, function(row) !any(row == "Logged")), , drop = FALSE]
            # Python equivalent: remove rows where any column has value "Logged"
            # We need to be careful with types, so convert to string first for check
            mask = df.astype(str).apply(lambda x: x.str.contains("Logged", case=False, na=False)).any(axis=1)
            df = df[~mask]
            
            st.subheader("Data Preview")
            st.dataframe(df.head())

            # Column Selection
            all_columns = df.columns.tolist()
            selected_columns = st.multiselect("Select Columns to Keep", all_columns, default=all_columns)
            
            if selected_columns:
                df_selected = df[selected_columns].copy()
                
                # Column Renaming
                st.subheader("Rename Columns")
                st.info("Select 'timestamp' and 'wtmp' for the appropriate columns.")
                col_map = {}
                standard_options = ['timestamp', 'wtmp']
                
                for col in selected_columns:
                    # Options: Original Name, timestamp, wtmp
                    # We use a list so the original name is the default (first item)
                    options = [col] + [opt for opt in standard_options if opt != col]
                    new_name = st.selectbox(f"Column: {col}", options=options, key=f"rename_{col}")
                    col_map[col] = new_name
                
                df_selected.rename(columns=col_map, inplace=True)
                
                # Timezone Conversion Helper
                st.subheader("Timezone Conversion")
                apply_tz_conversion = st.checkbox("Convert Timestamp to UTC?")
                if apply_tz_conversion:
                    tz_offset = st.number_input("Source Timezone Offset (e.g., -7 for PDT)", value=-7.0, step=0.5)
                    timestamp_col = 'timestamp' # We just renamed it
                    
                    if st.checkbox("Preview Conversion"):
                        try:
                            # Convert to datetime if not already
                            temp_ts = pd.to_datetime(df_selected[timestamp_col])
                            # Subtract offset to get UTC (e.g. if -7, we add 7 hours to get UTC? No, if local is -7, UTC is local - (-7) = local + 7)
                            # Wait, usually offset is defined as UTC + offset = Local.
                            # So Local - offset = UTC.
                            # Example: PDT is UTC-7. 10:00 UTC-7 is 17:00 UTC.
                            # 10:00 - (-7) = 17:00. Correct.
                            preview_ts = temp_ts - pd.Timedelta(hours=tz_offset)
                            st.write("Original (first 5):")
                            st.write(df_selected[timestamp_col].head())
                            st.write("Converted to UTC (first 5):")
                            st.write(preview_ts.head())
                        except Exception as e:
                            st.error(f"Error converting timestamp: {e}")
                
                # Metadata Inputs
                st.subheader("Metadata")
                
                # Auto-extract metadata from filename
                default_station = ""
                default_serial = ""
                if uploaded_file:
                    try:
                        # Assumption: filename format is Station_raw_Serial_Date...
                        # Split by '_raw_' to separate Station and the rest
                        parts = re.split(r'_raw_', uploaded_file.name, flags=re.IGNORECASE)
                        
                        if len(parts) > 1:
                            default_station = parts[0]
                            # The rest is Serial_Date...
                            # Split by '_' to get Serial
                            rest_parts = parts[1].split('_')
                            if len(rest_parts) > 0:
                                default_serial = rest_parts[0]
                    except Exception:
                        pass

                col1, col2 = st.columns(2)
                with col1:
                    # Use filename-based key to ensure updates when file changes
                    station_code = st.text_input("Station Code", value=default_station, key=f"station_{uploaded_file.name}")
                    logger_serial = st.text_input("Logger Serial Number", value=default_serial, key=f"serial_{uploaded_file.name}")
                with col2:
                    # Link UTC Offset to Source Timezone Offset if enabled
                    default_offset = 0.0
                    if apply_tz_conversion and 'tz_offset' in locals():
                        default_offset = float(tz_offset)
                        
                    utc_offset = st.number_input("UTC Offset", value=default_offset)
                    data_id = st.number_input("Data ID", value=0)
                
                # Save Button
                if st.button("Save Formatted Data"):
                    if not station_code or not logger_serial:
                        st.error("Please provide Station Code and Logger Serial Number.")
                    else:
                        # Add metadata columns
                        df_selected['station_code'] = station_code
                        df_selected['logger_serial'] = logger_serial
                        df_selected['utc_offset'] = utc_offset
                        df_selected['data_id'] = data_id
                        
                        # Apply Timezone Conversion if selected
                        if apply_tz_conversion:
                            try:
                                # Ensure timestamp col is selected
                                if 'timestamp_col' in locals():
                                    df_selected[timestamp_col] = pd.to_datetime(df_selected[timestamp_col]) - pd.Timedelta(hours=tz_offset)
                                    st.info(f"Converted {timestamp_col} to UTC using offset {tz_offset}")
                            except Exception as e:
                                st.error(f"Failed to convert timezone: {e}")
                                return # Stop saving if conversion fails
                        
                        # Construct filename
                        # Format: StationCode_formatted_LoggerSerial.csv (or similar)
                        filename = f"{station_code}_formatted_{logger_serial}.csv"
                        
                        saved_path = file_manager.save_data(df_selected, filename)
                        st.success(f"Data saved to {saved_path}")
                        st.dataframe(df_selected.head())

        except Exception as e:
            st.error(f"Error reading file: {e}")
