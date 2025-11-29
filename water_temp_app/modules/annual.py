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
                combined_df = combined_df.sort_values('timestamp')
                
                st.write(f"Combined {len(combined_df)} records.")
                
                # Handle Duplicates
                # Group by timestamp
                # Logic:
                # If 1 record -> keep
                # If >1 record:
                #   If all P -> Average
                #   If some P -> Keep P (Average P's if multiple)
                #   If no P -> Average and flag C (Caution)
                
                st.write("Handling duplicates...")
                
                def resolve_duplicates(group):
                    if len(group) == 1:
                        return group.iloc[0]
                    
                    # Multiple records
                    pass_records = group[group['wtmp_flag'] == 'P']
                    
                    if not pass_records.empty:
                        # Average the Pass records
                        avg_temp = pass_records['wtmp'].mean()
                        # Take the first metadata
                        result = pass_records.iloc[0].copy()
                        result['wtmp'] = avg_temp
                        result['wtmp_flag'] = 'P' # Or 'A' for Averaged
                        if len(pass_records) > 1:
                             result['wtmp_flag'] = 'A'
                        return result
                    else:
                        # No pass records
                        # Average all
                        avg_temp = group['wtmp'].mean()
                        result = group.iloc[0].copy()
                        result['wtmp'] = avg_temp
                        # If all were Missing, keep M, else C
                        if all(group['wtmp_flag'] == 'M'):
                            result['wtmp_flag'] = 'M'
                        else:
                            result['wtmp_flag'] = 'C'
                        return result

                # Apply logic (this might be slow for large datasets, but safe)
                # Optimization: only apply to duplicated timestamps
                dupes = combined_df.duplicated(subset=['timestamp'], keep=False)
                if dupes.any():
                    st.info(f"Found {dupes.sum()} duplicate timestamps. Resolving...")
                    
                    # Split into non-dupes and dupes
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
                
                # Stats
                st.write("**Annual Statistics (Daily Means):**")
                st.write(daily_df['wtmp'].describe())

