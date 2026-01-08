import streamlit as st
import pandas as pd
import plotly.express as px
from utils import file_manager
import os

def app():
    st.header("Annual Report & Compilation")

    # 1. Select Files to Compile
    st.subheader("1. Select Files to Compile")
    all_files = file_manager.list_files(subfolder="01_Data/02_Tidy", pattern=".csv")
    
    if not all_files:
        st.warning("No files found.")
        return
        
    selected_files = st.multiselect("Choose files to merge (usually for one station)", all_files)
    
    if selected_files:
        if st.button("Compile & Generate Annual Report"):
            dfs = []
            for f in selected_files:
                d = file_manager.load_data(f, subfolder="01_Data/02_Tidy")
                if d is not None:
                    if 'timestamp' in d.columns:
                        d['timestamp'] = pd.to_datetime(d['timestamp'])
                    dfs.append(d)
            
            if dfs:
                # Merge
                combined_df = pd.concat(dfs, ignore_index=True)
                # Stable sort by timestamp then data_id (or another stable column)
                # This ensures that if we have duplicates, their relative order is deterministic
                # We sort by data_id descending to keeping the higher ID? Or ascending?
                # User said "stick to like 174... not swap". 
                # Let's sort by timestamp (asc) and data_id (asc). 
                # This way duplicate groups will always be ordered by data_id.
                if 'data_id' in combined_df.columns:
                     combined_df = combined_df.sort_values(['timestamp', 'data_id'])
                else:
                     # Fallback to simple sort if no data_id
                     combined_df = combined_df.sort_values('timestamp')
                
                st.write(f"Combined {len(combined_df)} records.")
                
                # Handle Duplicates
                # New Logic: Pick ONE, do not average, do not use 'C'.
                
                st.write("Handling duplicates (picking best record)...")
                
                def resolve_duplicates(group):
                    if len(group) == 1:
                        return group.iloc[0]
                    
                    # Multiple records
                    # Priority 1: 'P' (Pass) flag
                    pass_records = group[group['wtmp_flag'] == 'P']
                    
                    if not pass_records.empty:
                        # Pick the first one (deterministically due to sort)
                        return pass_records.iloc[0]
                    
                    # Priority 2: Any record
                    # Just pick the first one. Since we sorted by data_id, this will consistently
                    # pick the one with the lowest data_id (or based on sort order).
                    return group.iloc[0]

                # Apply logic
                dupes = combined_df.duplicated(subset=['timestamp'], keep=False)
                if dupes.any():
                    st.info(f"Found {dupes.sum()} duplicate timestamps. Resolving...")
                    
                    # Optimization: Groupby and apply is faster on smaller set, but we need to recombine carefully
                    # or just apply to the whole group if the valid ones are mixed in.
                    # Simplest way that preserves order:
                    
                    non_dupe_df = combined_df[~dupes]
                    dupe_df = combined_df[dupes]
                    
                    resolved_dupes = dupe_df.groupby('timestamp').apply(resolve_duplicates).reset_index(drop=True)
                    
                    final_df = pd.concat([non_dupe_df, resolved_dupes]).sort_values('timestamp')
                else:
                    final_df = combined_df
                
                st.success(f"Compilation Complete. Final records: {len(final_df)}")
                
                # Save Compiled
                station = final_df['station_code'].iloc[0] if 'station_code' in final_df.columns else "Unknown"
                year = pd.Timestamp.now().year
                save_name = f"{station}_compiled_{year}.csv"
                saved_path = file_manager.save_data(final_df, save_name, subfolder="01_Data/03_Compiled")
                st.write(f"Saved compiled data to {saved_path}")
                
                # Annual Plot
                st.subheader("Annual Temperature Plot")
                # Calculate daily means
                final_df['date'] = final_df['timestamp'].dt.date
                daily_df = final_df.groupby('date')['wtmp'].mean().reset_index()
                
                fig = px.line(daily_df, x='date', y='wtmp', title=f"Daily Mean Temperature - {station}")
                st.plotly_chart(fig, use_container_width=True)
                
                # --- Statistics Calculation ---
                
                # 1. Flag Summary
                st.subheader("Flag Summary")
                flag_counts = final_df['wtmp_flag'].value_counts()
                flag_props = final_df['wtmp_flag'].value_counts(normalize=True) * 100
                flag_summary = pd.DataFrame({'Count': flag_counts, 'Proportion (%)': flag_props})
                flag_summary['Proportion (%)'] = flag_summary['Proportion (%)'].map('{:.2f}'.format)
                st.write(flag_summary)

                # Helper for stats
                def get_temp_stats(data, label):
                    if data.empty:
                        return pd.DataFrame()
                    desc = data['wtmp'].describe(percentiles=[.05, .25, .50, .75, .95])
                    stats = {
                        'Metric': ['Mean', 'SD', 'Min', 'Max', 'Median', 'P05', 'P25', 'P75', 'P95', 'Count'],
                        'Value': [
                            desc['mean'], desc['std'], desc['min'], desc['max'], desc['50%'],
                            desc['5%'], desc['25%'], desc['75%'], desc['95%'], desc['count']
                        ]
                    }
                    df_stats = pd.DataFrame(stats)
                    df_stats.set_index('Metric', inplace=True)
                    df_stats.columns = [label]
                    return df_stats

                # 2. All Data Stats
                st.subheader("Temperature Statistics (All Data)")
                stats_all = get_temp_stats(final_df, "All Data")
                st.write(stats_all)

                # 3. Passed Data Stats
                st.subheader("Temperature Statistics (Passed Data Only)")
                passed_df = final_df[final_df['wtmp_flag'] == 'P']
                stats_passed = get_temp_stats(passed_df, "Passed Data")
                st.write(stats_passed)

                # Generate HTML Report
                try:
                    # Plot HTML
                    plot_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    
                    # Tables HTML
                    flag_html = flag_summary.to_html(classes='table table-striped')
                    stats_all_html = stats_all.to_html(classes='table table-striped')
                    stats_passed_html = stats_passed.to_html(classes='table table-striped')
                    
                    # Full HTML
                    full_html = f"""
                    <html>
                    <head>
                        <title>Annual Report - {station} {year}</title>
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
                            h1, h2, h3 {{ color: #2c3e50; }}
                            hr {{ border: 1px solid #eee; margin: 20px 0; }}
                            table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #ddd; }}
                            th {{ background-color: #f2f2f2; }}
                            .section {{ margin-bottom: 40px; }}
                        </style>
                    </head>
                    <body>
                        <h1>Annual Water Temperature Report</h1>
                        <h2>Station: {station}</h2>
                        <h2>Year: {year}</h2>
                        <hr>
                        
                        <div class="section">
                            <h3>1. Flag Summary</h3>
                            {flag_html}
                        </div>

                        <div class="section">
                            <h3>2. Temperature Statistics (All Data)</h3>
                            {stats_all_html}
                        </div>

                        <div class="section">
                            <h3>3. Temperature Statistics (Passed Data Only)</h3>
                            {stats_passed_html}
                        </div>

                        <div class="section">
                            <h3>4. Annual Time Series Plot</h3>
                            {plot_html}
                        </div>
                    </body>
                    </html>
                    """
                    
                    # Save HTML
                    report_name = f"{station}_annualReport_{year}.html"
                    project_dir = file_manager.get_project_dir()
                    report_path = os.path.join(project_dir, "03_Reports", "03_Annual", report_name)
                    os.makedirs(os.path.dirname(report_path), exist_ok=True)
                    
                    with open(report_path, "w") as f:
                        f.write(full_html)
                        
                    st.success(f"Annual Report saved to: {report_path}")
                    
                    # Store path in session state
                    st.session_state['generated_annual_report_path'] = report_path
                    
                except Exception as e:
                    st.error(f"Failed to generate HTML report: {e}")

    # Persistent Open Button (Outside the generate block and selection block)
    if 'generated_annual_report_path' in st.session_state:
        report_path = st.session_state['generated_annual_report_path']
        if st.button("Open Annual Report Now"):
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

