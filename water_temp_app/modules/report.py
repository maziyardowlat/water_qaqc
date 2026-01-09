import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import file_manager
import os

def app():
    st.header("Generate QAQC Report")

    # 1. Select Tidy Data File
    st.subheader("1. Select Tidy Data")
    # Look for files in 02_Tidy
    tidy_files = file_manager.list_files(subfolder="01_Data/02_Tidy", pattern=".csv")
    # Filter out any lingering notes/json files just in case (though we stopped making them)
    tidy_files = [f for f in tidy_files if not f.endswith("_notes.csv") and not f.endswith("_metadata.json")]
    if not tidy_files:
        st.warning("No data found in Tidy folder.")
        return

    selected_file = st.selectbox("Choose File", tidy_files)
    
    if selected_file:
        df = file_manager.load_data(selected_file, subfolder="01_Data/02_Tidy")
        if df is not None:
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # FIX: Coerce temperature to numeric (handles "NAN" strings)
            if 'wtmp' in df.columns:
                df['wtmp'] = pd.to_numeric(df['wtmp'], errors='coerce')
            
            st.subheader(f"Report for {selected_file}")

            # Summary Stats
            st.markdown("### Summary Statistics")
            total_records = len(df)
            st.write(f"**Total Records:** {total_records}")
            
            if 'wtmp_flag' in df.columns:
                flag_counts = df['wtmp_flag'].value_counts()
                st.write("**Flag Distribution:**")
                st.bar_chart(flag_counts)
                
                pass_count = flag_counts.get('P', 0)
                pass_percent = (pass_count / total_records) * 100
                st.write(f"**Pass Rate:** {pass_percent:.2f}%")
            
            if 'wtmp' in df.columns:
                st.write("**Temperature Stats (All Data):**")
                st.write(df['wtmp'].describe())
                
                st.write("**Temperature Stats (Passed Data Only):**")
                pass_df = df[df['wtmp_flag'] == 'P']
                st.write(pass_df['wtmp'].describe())

            # Final Plot
            st.markdown("### Final Time Series")
            
            # Create a combined Line + Scatter plot similar to Review/Flag modules
            fig = go.Figure()
            
            # 1. Add Line (All data) - Gray background line for connectivity
            fig.add_trace(go.Scatter(
                x=df['timestamp'], 
                y=df['wtmp'], 
                mode='lines',
                name='Temperature',
                line=dict(color='gray', width=1),
                hoverinfo='skip' # Skip hover on the line, focus on points
            ))
            
            # 2. Add markers for each flag type
            colors = {
                'P': 'green', 'S': 'red', 'E': 'purple', 
                'T': 'orange', 'B': 'blue', 'M': 'darkred', 'V': 'pink',
                'D': 'brown', 'N': 'gray', 'A': 'black'
            }
            
            # Get all unique flags present in the data
            present_flags = df['wtmp_flag'].unique()
            
            for flag in present_flags:
                subset = df[df['wtmp_flag'] == flag]
                color = colors.get(flag, 'black') # Default to black if unknown
                
                fig.add_trace(go.Scatter(
                    x=subset['timestamp'],
                    y=subset['wtmp'],
                    mode='markers',
                    name=f"Flag: {flag}",
                    marker=dict(color=color, size=6)
                ))

            fig.update_layout(
                title=f"Water Temperature Time Series - {selected_file}",
                xaxis_title="Timestamp",
                yaxis_title="Water Temperature",
                hovermode="closest"
            )
            
            st.plotly_chart(fig, use_container_width=True)

            # Export
            # Streamlit doesn't easily generate PDF without extra libs like WeasyPrint which might be hard to install.
            # We'll stick to HTML or just the view for now.

            # Export HTML Report
            if st.button("Generate HTML Report"):
                try:
                    # 1. Prepare Content
                    station = df['station_code'].iloc[0] if 'station_code' in df.columns else "Unknown"
                    serial = df['logger_serial'].iloc[0] if 'logger_serial' in df.columns else "Unknown"
                    utc_offset = df['utc_offset'].iloc[0] if 'utc_offset' in df.columns else "Unknown"
                    data_id = df['data_id'].iloc[0] if 'data_id' in df.columns else "Unknown"
                    date_str = pd.Timestamp.now().strftime("%Y-%m-%d")

                    # Calculate Dates
                    record_start = df['timestamp'].min().strftime("%Y-%m-%d %H:%M:%S")
                    record_end = df['timestamp'].max().strftime("%Y-%m-%d %H:%M:%S")

                    # Get Field Times (Try to retrieve from session state if available)
                    field_in = "N/A"
                    field_out = "N/A"
                    prev_field_in = "N/A"
                    prev_field_out = "N/A"
                    
                    # Try to load metadata from JSON sidecar
                    # LOAD METADATA (Session State + Manual Override)
                    # We prioritize session state, but allow user to edit/fill in if missing.
                    
                    default_field_in = "N/A"
                    default_field_out = "N/A"
                    default_prev_in = "N/A"
                    default_prev_out = "N/A"
                    default_start = record_start
                    default_end = record_end
                    
                    if 'qaqc_metadata' in st.session_state:
                         meta = st.session_state['qaqc_metadata']
                         default_field_in = str(meta.get('field_in', "N/A"))
                         default_field_out = str(meta.get('field_out', "N/A"))
                         default_prev_in = str(meta.get('prev_field_in', "N/A"))
                         default_prev_out = str(meta.get('prev_field_out', "N/A"))
                         default_start = str(meta.get('record_start', record_start))
                         default_end = str(meta.get('record_end', record_end))
                         st.success("Loaded metadata from Session Memory.")
                    else:
                         st.info("MetaData absent from memory (new session). Please enter details below.")
                    
                    with st.expander("Edit Report Metadata (Field Times)", expanded=True):
                         col_m1, col_m2 = st.columns(2)
                         with col_m1:
                            field_in = st.text_input("Field Time In", value=default_field_in)
                            prev_field_in = st.text_input("Prev Visit In", value=default_prev_in)
                            record_start = st.text_input("Record Start", value=default_start)
                         with col_m2:
                            field_out = st.text_input("Field Time Out", value=default_field_out)
                            prev_field_out = st.text_input("Prev Visit Out", value=default_prev_out)
                            record_end = st.text_input("Record End", value=default_end)
                    
                    # Metadata HTML Block
                    
                    # Metadata HTML Block
                    metadata_html = f"""
                    <h3>Metadata</h3>
                    <p>
                    <b>Station Code:</b> {station}<br>
                    <b>Logger Serial Number:</b> {serial}<br>
                    <b>UTC Offset:</b> {utc_offset}<br>
                    <b>Data ID:</b> {data_id}<br>
                    <b>Field time-in:</b> {field_in}<br>
                    <b>Field time-out:</b> {field_out}<br>
                    <b>Previous field time-in:</b> {prev_field_in}<br>
                    <b>Previous field time-out:</b> {prev_field_out}<br>
                    <b>Record Start Date:</b> {record_start}<br>
                    <b>Record End Date:</b> {record_end}
                    </p>
                    """
                    
                    # Flag Summary Table
                    if 'wtmp_flag' in df.columns:
                        flag_counts = df['wtmp_flag'].value_counts().reset_index()
                        flag_counts.columns = ['flag_symbol', 'flag_count']
                        
                        # Define flag names
                        flag_names = {
                            'P': 'Pass',
                            'N': 'No QAQC',
                            'B': 'Below ice',
                            'S': 'Spike',
                            'E': 'Outside sensor limits',
                            'T': 'Above threshold 35',
                            'D': 'Duplicate timestamp',
                            'M': 'Missing value',
                            'V': 'Visit',
                            'A': 'Air/Dewatered'
                        }
                        
                        flag_counts['flag_name'] = flag_counts['flag_symbol'].map(flag_names).fillna('Unknown')
                        flag_counts['flag_prop'] = (flag_counts['flag_count'] / total_records) * 100
                        
                        # Ensure all standard flags are present even if count is 0
                        for sym, name in flag_names.items():
                            if sym not in flag_counts['flag_symbol'].values:
                                new_row = pd.DataFrame({'flag_symbol': [sym], 'flag_count': [0], 'flag_name': [name], 'flag_prop': [0.0]})
                                flag_counts = pd.concat([flag_counts, new_row], ignore_index=True)
                        
                        # Sort by some logical order or just symbol
                        # User example order: P, N, B, S, E, T, D, M, V, A
                        order = ['P', 'N', 'B', 'S', 'E', 'T', 'D', 'M', 'V', 'A']
                        flag_counts['order'] = flag_counts['flag_symbol'].map({k: i for i, k in enumerate(order)})
                        flag_counts = flag_counts.sort_values('order').drop(columns=['order'])

                        # Create HTML Table
                        table_html = """
                        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 50%;">
                        <thead>
                            <tr style="background-color: #f2f2f2;">
                                <th>flag_symbol</th>
                                <th>flag_name</th>
                                <th>flag_count</th>
                                <th>flag_prop</th>
                            </tr>
                        </thead>
                        <tbody>
                        """
                        for _, row in flag_counts.iterrows():
                            table_html += f"""
                            <tr>
                                <td style="text-align: center;">{row['flag_symbol']}</td>
                                <td>{row['flag_name']}</td>
                                <td style="text-align: right;">{row['flag_count']}</td>
                                <td style="text-align: right;">{row['flag_prop']:.9f}</td>
                            </tr>
                            """
                        table_html += "</tbody></table>"
                    else:
                        table_html = "<p>No flag data available.</p>"

                    # Plot HTML
                    plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    
                    # Notes with Edit Capability
                    default_notes = "No notes entered in session."
                    if 'qaqc_notes' in st.session_state:
                        default_notes = st.session_state['qaqc_notes']
                    elif 'qaqc_notes' in df.columns: # Clean CSV shouldn't have it, but for legacy support
                         unique = df['qaqc_notes'].dropna().unique()
                         if len(unique) > 0: default_notes = str(unique[0])

                    with st.expander("Edit QAQC Notes", expanded=True):
                        notes_content = st.text_area("Notes", value=default_notes)
                    
                    # Full HTML
                    full_html = f"""
                    <html>
                    <head><title>QAQC Report - {station}</title></head>
                    <body style="font-family: Arial, sans-serif; margin: 40px;">
                        <h1>Water Temperature QAQC Report</h1>
                        <hr>
                        {metadata_html}
                        <hr>
                        <h3>Flag Summary</h3>
                        {table_html}
                        <hr>
                        <h3>Time Series Plot</h3>
                        {plot_html}
                        <hr>
                        <h3>QAQC Notes</h3>
                        <p>{notes_content}</p>
                    </body>
                    </html>
                    """
                    
                    # Save
                    report_name = selected_file.replace(".csv", "_report.html")
                    # Save to 01_Data root or Tidy? User example was in 01_Data root but let's keep it in Tidy for now or root?
                    # User path: water_temp_app/01_Data/01FW001_qaqcReport_21731726_20250610.html
                    # So it seems to be in 01_Data.
                    
                    project_dir = file_manager.get_project_dir()
                    report_path = os.path.join(project_dir, "03_Reports", "02_QAQC", report_name)
                    os.makedirs(os.path.dirname(report_path), exist_ok=True)
                    
                    with open(report_path, "w") as f:
                        f.write(full_html)
                        
                    st.success(f"Report saved to: {report_path}")
                    
                    # Store path in session state for the persistent button
                    st.session_state['generated_report_path'] = report_path
                    
                except Exception as e:
                    st.error(f"Failed to generate report: {e}")

            # Persistent Open Button (Outside the generate block)
            if 'generated_report_path' in st.session_state:
                report_path = st.session_state['generated_report_path']
                if st.button("Open Report Now"):
                    import subprocess
                    import sys
                    try:
                        if sys.platform == 'darwin': # macOS
                            subprocess.run(['open', report_path], check=True)
                        elif sys.platform == 'win32': # Windows
                            os.startfile(report_path)
                        else: # Linux
                            subprocess.run(['xdg-open', report_path], check=True)
                    except Exception as e:
                        st.error(f"Could not open file automatically: {e}")
                        st.info(f"Please open this file manually: {report_path}")

            st.info("You can also print this page to PDF using your browser's print function.")

