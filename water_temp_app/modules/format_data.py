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

    # File Source Selection
    file_source = st.radio("File Source", ["Upload File", "Select from Server (OneDrive)"], horizontal=True)
    
    uploaded_file = None
    server_file_path = None
    
    if file_source == "Upload File":
        uploaded_file = st.file_uploader("Choose CSV or Excel File", type=['csv', 'txt', 'xlsx'])
    else:
        # Server Selection Logic
        import glob
        
        # Try to guess station code from current project dir
        default_station_code = ""
        current_project_dir = file_manager.get_project_dir()
        if "02_Stations" in current_project_dir:
            # Assume folder name starts with station code
            folder_name = os.path.basename(current_project_dir)
            default_station_code = folder_name.split("_")[0] if "_" in folder_name else folder_name

        col_server1, col_server2 = st.columns(2)
        with col_server1:
            username_input = st.text_input("Username (for OneDrive Path)", value="dowlataba")
        with col_server2:
            station_code_input = st.text_input("Enter Station Code to Search", value=default_station_code)
        
        if station_code_input and username_input:
            # We need to find the base "02_Stations" directory.
            # If current_project_dir is inside 02_Stations, we can go up.
            # Otherwise, we might need to ask the user or rely on the standard path if it exists.
            
            base_stations_dir = None
            
            if "02_Stations" in current_project_dir:
                # Split path at 02_Stations and keep the first part + 02_Stations
                parts = current_project_dir.split("02_Stations")
                base_stations_dir = os.path.join(parts[0], "02_Stations")
            else:
                # Construct from Username
                # Path: /Users/{username}/OneDrive - UNBC/NHG Field - Data Management/02_Stations
                user_onedrive_path = os.path.join("/Users", username_input, "OneDrive - UNBC", "NHG Field - Data Management")
                base_stations_dir = os.path.join(user_onedrive_path, "02_Stations")
                
                # Check if User/OneDrive path exists
                if not os.path.exists(user_onedrive_path):
                    st.error(f"Could not find OneDrive folder for user '{username_input}'. Expected path: {user_onedrive_path}")
                    base_stations_dir = None # Prevent further checks
                elif not os.path.exists(base_stations_dir):
                    st.error(f"Found OneDrive folder, but '02_Stations' directory is missing in: {user_onedrive_path}")
                    base_stations_dir = None
                
            if base_stations_dir and os.path.exists(base_stations_dir):
                # Search for station folder
                search_pattern = os.path.join(base_stations_dir, f"{station_code_input}*")
                matching_folders = glob.glob(search_pattern)
                
                if matching_folders:
                    station_folder = matching_folders[0]
                    # Look for raw files in 01_Data/01_Raw
                    raw_dir = os.path.join(station_folder, "01_Data", "01_Raw")
                    
                    if os.path.exists(raw_dir):
                        raw_files = [f for f in os.listdir(raw_dir) if f.endswith(".csv") or f.endswith(".txt") or f.endswith(".xlsx")]
                        if raw_files:
                            selected_filename = st.selectbox("Select Raw File", raw_files)
                            server_file_path = os.path.join(raw_dir, selected_filename)
                            st.success(f"Selected: {selected_filename}")
                            
                            # Update project dir to this station if not already
                            if current_project_dir != station_folder:
                                if st.button(f"Switch Project Directory to {os.path.basename(station_folder)}"):
                                    file_manager.set_project_dir(station_folder)
                                    st.rerun()
                        else:
                            st.warning(f"No CSV/TXT files found in {raw_dir}")
                    else:
                        st.warning(f"Raw data directory not found: {raw_dir}")
                else:
                    st.error(f"Station folder starting with '{station_code_input}' not found in: {base_stations_dir}")
            
    
    if uploaded_file is not None or server_file_path is not None:
        # Skip Rows
        skip_rows = st.number_input("Rows to Skip", min_value=0, value=1)
        
        try:
            # Read Data
            if uploaded_file is not None:
                file_name_for_meta = uploaded_file.name
                # Reset file pointer
                uploaded_file.seek(0)
                
                if file_name_for_meta.endswith('.xlsx'):
                    df = pd.read_excel(uploaded_file, skiprows=skip_rows)
                else:
                    # Try CSV, but handle potential "renamed xlsx" issue
                    try:
                        df = pd.read_csv(uploaded_file, skiprows=skip_rows, low_memory=False)
                    except (UnicodeDecodeError, pd.errors.ParserError):
                         # Fallback for renamed files
                         uploaded_file.seek(0)
                         df = pd.read_excel(uploaded_file, skiprows=skip_rows)
                         st.warning("File read as Excel despite extension. Please rename to .xlsx for clarity.")

            else:
                # Server file
                file_name_for_meta = os.path.basename(server_file_path)
                if file_name_for_meta.endswith('.xlsx'):
                    df = pd.read_excel(server_file_path, skiprows=skip_rows)
                else:
                    try:
                         df = pd.read_csv(server_file_path, skiprows=skip_rows, low_memory=False)
                    except (UnicodeDecodeError, pd.errors.ParserError):
                         df = pd.read_excel(server_file_path, skiprows=skip_rows)
                         st.warning("File read as Excel despite extension. Please rename to .xlsx for clarity.")
            
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
                # Use file_name_for_meta which is set above
                try:
                    # Assumption: filename format is Station_raw_Serial_Date...
                    # Split by '_raw_' to separate Station and the rest
                    parts = re.split(r'_raw_', file_name_for_meta, flags=re.IGNORECASE)
                    
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
                    station_code = st.text_input("Station Code", value=default_station, key=f"station_{file_name_for_meta}")
                    logger_serial = st.text_input("Logger Serial Number", value=default_serial, key=f"serial_{file_name_for_meta}")
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
                        # Sanitize inputs to prevent filename issues
                        station_code = str(station_code).replace("/", "_").replace("\\", "_")
                        logger_serial = str(logger_serial).replace("/", "_").replace("\\", "_")

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
                        
                        # Save to Session State instead of file
                        st.session_state['formatted_df'] = df_selected
                        st.session_state['formatted_filename'] = f"{station_code}_formatted_{logger_serial}.csv" # Keep name for reference
                        
                        st.success(f"Data formatted and ready in memory. Please proceed to 'Flag & Compile' immediately.")
                        st.info("Note: No intermediate file is saved.")
                        st.dataframe(df_selected.head())

        except Exception as e:
            st.error(f"Error reading file: {e}")
