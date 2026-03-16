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
                    # FIX: Coerce temperature to numeric (handles "NAN" strings)
                    if 'wtmp' in d.columns:
                        d['wtmp'] = pd.to_numeric(d['wtmp'], errors='coerce')
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
                
                # ============================================================
                # Handle Duplicates — Multi-Logger Averaging
                # Ported from R: WT_AnnualReport.R (lines 127-193)
                #
                # When two loggers overlap at the same timestamp, we resolve
                # duplicates using three cases:
                #
                # Case 1 — Both P:
                #   Average wtmp, concatenate logger_serial with ".",
                #   concatenate data_id with ".", flag = "AVG"
                #
                # Case 2 — One P, one not-P:
                #   Keep the P record as-is (no averaging, no concatenation).
                #   The non-P record is discarded.
                #
                # Case 3 — Neither P:
                #   Average wtmp (NA if both NA), concatenate logger_serial
                #   with "_", concatenate data_id with ".", flag = "C" (Caution).
                #   Exception: if both flags are "M", flag stays "M".
                # ============================================================
                
                st.write("Handling duplicate timestamps...")
                
                # --------------------------------------------------------
                # Step A: Same-logger dedup
                # When two tidy files from the same logger overlap, we get
                # exact duplicate rows (same serial, same timestamp).
                # Simple dedup: keep the first record, drop the rest.
                # --------------------------------------------------------
                before_dedup = len(combined_df)
                combined_df = combined_df.drop_duplicates(
                    subset=['timestamp', 'logger_serial'], keep='first'
                )
                same_logger_dupes = before_dedup - len(combined_df)
                if same_logger_dupes > 0:
                    st.info(f"Removed {same_logger_dupes} same-logger duplicate records.")
                
                # --------------------------------------------------------
                # Step B: Multi-logger averaging
                # After same-logger dedup, any remaining duplicates must be
                # from different loggers at the same timestamp.
                # (Matches R logic: n_distinct(logger_serial) > 1)
                # --------------------------------------------------------
                dupes_mask = combined_df.duplicated(subset=['timestamp'], keep=False)
                
                if dupes_mask.any():
                    dupe_count = dupes_mask.sum()
                    st.info(f"Found {dupe_count} records with multi-logger overlap. Resolving with averaging...")
                    
                    # Split into non-duplicate (unique timestamps) and duplicate groups
                    non_dupe_df = combined_df[~dupes_mask].copy()
                    dupe_df = combined_df[dupes_mask].copy()
                    
                    # --- Case 1: Both loggers passed (all flags == 'P') ---
                    # Average wtmp, concatenate serials with ".", data_ids with ".", flag = "AVG"
                    case1_groups = dupe_df.groupby('timestamp').filter(
                        lambda g: (g['wtmp_flag'] == 'P').all()
                    )
                    
                    if not case1_groups.empty:
                        case1_resolved = case1_groups.groupby('timestamp').agg(
                            wtmp=('wtmp', 'mean'),
                            logger_serial=('logger_serial', lambda x: '.'.join(str(s) for s in x)),
                            data_id=('data_id', lambda x: '.'.join(str(s) for s in x)),
                            # Carry forward metadata from the first record in each group
                            station_code=('station_code', 'first'),
                            utc_offset=('utc_offset', 'first'),
                        ).reset_index()
                        case1_resolved['wtmp_flag'] = 'AVG'
                    else:
                        case1_resolved = pd.DataFrame()
                    
                    # --- Case 2: One P, one (or more) not-P ---
                    # Keep the P record as-is, discard non-P records.
                    case2_groups = dupe_df.groupby('timestamp').filter(
                        lambda g: g['wtmp_flag'].eq('P').any() and not g['wtmp_flag'].eq('P').all()
                    )
                    
                    if not case2_groups.empty:
                        # Just keep the rows flagged 'P'; drop the rest
                        case2_resolved = case2_groups[case2_groups['wtmp_flag'] == 'P'].copy()
                        
                        # If multiple P records exist at the same timestamp, keep just the first
                        case2_resolved = case2_resolved.drop_duplicates(subset=['timestamp'], keep='first')
                    else:
                        case2_resolved = pd.DataFrame()
                    
                    # --- Case 3: Neither logger passed (no 'P' flags in group) ---
                    # Average wtmp (NA if both NA), concatenate serials with "_",
                    # data_ids with ".", flag = "C" (Caution). If both "M", flag = "M".
                    case3_groups = dupe_df.groupby('timestamp').filter(
                        lambda g: not g['wtmp_flag'].eq('P').any()
                    )
                    
                    if not case3_groups.empty:
                        def resolve_no_pass(group):
                            """Resolve a duplicate group where no records passed QAQC."""
                            # Average wtmp: NA if all NA, otherwise mean of available values
                            if group['wtmp'].isna().all():
                                avg_wtmp = pd.NA
                            else:
                                avg_wtmp = group['wtmp'].mean(skipna=True)
                            
                            # Determine flag: "M" if all flags are "M", otherwise "C" (Caution)
                            if (group['wtmp_flag'] == 'M').all():
                                flag = 'M'
                            else:
                                flag = 'C'
                            
                            # Build the resolved row from the first record's metadata
                            row = group.iloc[0].copy()
                            row['wtmp'] = avg_wtmp
                            row['wtmp_flag'] = flag
                            row['logger_serial'] = '_'.join(str(s) for s in group['logger_serial'])
                            row['data_id'] = '.'.join(str(s) for s in group['data_id'])
                            return row
                        
                        case3_resolved = case3_groups.groupby('timestamp').apply(
                            resolve_no_pass
                        ).reset_index(drop=True)
                    else:
                        case3_resolved = pd.DataFrame()
                    
                    # --- Combine all resolved records ---
                    resolved_parts = [non_dupe_df]
                    
                    # Track counts for user feedback
                    case_counts = []
                    if not case1_resolved.empty:
                        resolved_parts.append(case1_resolved)
                        case_counts.append(f"{len(case1_resolved)} averaged (AVG)")
                    if not case2_resolved.empty:
                        resolved_parts.append(case2_resolved)
                        case_counts.append(f"{len(case2_resolved)} kept P record")
                    if not case3_resolved.empty:
                        resolved_parts.append(case3_resolved)
                        case_counts.append(f"{len(case3_resolved)} averaged with caution (C)")
                    
                    final_df = pd.concat(resolved_parts, ignore_index=True).sort_values('timestamp')
                    
                    st.success(f"Multi-logger merge complete: {', '.join(case_counts)}")
                    
                    # Sanity check: no remaining duplicate timestamps
                    remaining_dupes = final_df.duplicated(subset=['timestamp'], keep=False).sum()
                    if remaining_dupes > 0:
                        st.error(f"WARNING: {remaining_dupes} duplicate timestamps remain after merge! Check data.")
                    else:
                        st.info("No remaining duplicate timestamps — merge successful.")
                else:
                    final_df = combined_df
                    st.info("No multi-logger overlap found — no averaging needed.")
                
                st.success(f"Compilation Complete. Final records: {len(final_df)}")
                
                # Save Compiled
                final_df_to_save = final_df.copy()
                if 'wtmp' in final_df_to_save.columns:
                     final_df_to_save['wtmp'] = final_df_to_save['wtmp'].astype(object)
                     final_df_to_save['wtmp'] = final_df_to_save['wtmp'].fillna("NAN")
                
                station = final_df['station_code'].iloc[0] if 'station_code' in final_df.columns else "Unknown"
                year = pd.Timestamp.now().year
                save_name = f"{station}_compiled_{year}.csv"
                saved_path = file_manager.save_data(final_df_to_save, save_name, subfolder="01_Data/03_Compiled")
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