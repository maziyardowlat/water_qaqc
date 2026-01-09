import streamlit as st
import pandas as pd
import plotly.express as px
from utils import file_manager
import os

def app():
    st.header("Review Data")

    # 1. Select Tidy Data File
    st.subheader("1. Select Tidy Data")
    
    # Debug Info
    current_dir = file_manager.get_project_dir()
    tidy_dir = os.path.join(current_dir, "01_Data/02_Tidy")
    st.caption(f"Looking for files in: {tidy_dir}")
    
    if st.button("Refresh File List"):
        st.rerun()

    tidy_files = file_manager.list_files(subfolder="01_Data/02_Tidy", pattern=".csv")
    if not tidy_files:
        st.warning("No tidy files found. Please go to 'Flag Compile' first.")
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
            
            st.write(f"Loaded {len(df)} rows.")

            # Check for required columns
            if 'wtmp_flag' not in df.columns:
                st.error("Selected file does not contain 'wtmp_flag' column. Is this a valid Tidy file?")
                return

            # 2. Interactive Plot
            st.subheader("2. Visual Review")
            
            # Filter by Flag
            all_flags = df['wtmp_flag'].unique().tolist()
            selected_flags = st.multiselect("Filter by Flag", all_flags, default=all_flags)
            
            filtered_df = df[df['wtmp_flag'].isin(selected_flags)]
            
            fig = px.scatter(filtered_df, x='timestamp', y='wtmp', color='wtmp_flag',
                             color_discrete_map={
                                 'P': 'green', 'S': 'red', 'E': 'purple', 
                                 'T': 'orange', 'B': 'blue', 'M': 'darkred', 'V': 'pink',
                                 'A': 'black'
                             },
                             title=f"Review: {selected_file}")
            st.plotly_chart(fig, use_container_width=True)

            # 3. Manual Editing
            st.subheader("3. Edit Flags")
            st.info("You can edit the 'wtmp_flag' column directly below.")
            
            # Use data_editor for editing
            # We'll show a subset of columns to make it easier
            cols_to_show = ['timestamp', 'wtmp', 'wtmp_flag']
            if 'station_code' in df.columns: cols_to_show.append('station_code')
            
            edited_df = st.data_editor(df[cols_to_show], num_rows="dynamic", key="editor")
            
            # Update the original dataframe with edits
            # Note: st.data_editor returns the edited dataframe. 
            # We need to merge it back if we only showed a subset, but here we can just use the index if it matches.
            # Or simpler: just let them edit the whole thing but hide columns? 
            # st.data_editor supports column configuration.
            
            # Let's just assume they edited 'edited_df'. We need to update 'df' with these changes.
            df.update(edited_df)

            # 4. Notes
            st.subheader("4. QAQC Notes")
            
            # Load existing notes from SESSION STATE
            existing_note = st.session_state.get('qaqc_notes', "")
            
            notes = st.text_area("Enter notes for this review session:", value=existing_note)
            
            if notes != existing_note:
                st.info("Notes modified. Will update Session State on save.")

            # 5. Save
            if st.button("Save Reviewed Data"):
                # Update Session State
                st.session_state['qaqc_notes'] = notes
                
                # Save back to Tidy folder (OVERWRITE)
                # Ensure no 'qaqc_notes' column is in df
                if 'qaqc_notes' in df.columns:
                    df = df.drop(columns=['qaqc_notes'])

                # FIX: Convert 'wtmp' back to object and replace NaN with "NAN" strings before saving
                # This ensures we don't lose the "NAN"s when overwriting
                df_to_save = df.copy()
                if 'wtmp' in df_to_save.columns:
                    df_to_save['wtmp'] = df_to_save['wtmp'].astype(object)
                    df_to_save['wtmp'] = df_to_save['wtmp'].fillna("NAN")

                save_name = selected_file
                
                saved_path = file_manager.save_data(df_to_save, save_name, subfolder="01_Data/02_Tidy", overwrite=True)
                st.success(f"Reviewed data saved (overwritten) to {saved_path}")
                st.info("Notes saved to Session Memory.")
