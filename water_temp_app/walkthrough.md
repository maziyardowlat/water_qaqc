# Walkthrough - Water Temperature QAQC App

I have converted your R scripts into a unified Python application using Streamlit. This app provides a user-friendly GUI for the entire workflow, from formatting raw data to generating annual reports.

## Key Features

1.  **Unified GUI**: No need to run separate scripts. Everything is accessible via a sidebar navigation menu.
2.  **Project Directory Abstraction**: You can choose any folder on your computer to store your data. The app will automatically create the necessary subfolders (`01_Data/01_Raw_Formatted`, `01_Data/02_Tidy`, etc.).
3.  **Interactive Review**: The "Review" module allows you to zoom into plots, filter by flags, and even manually edit flags directly in the table.
4.  **Reporting**: Built-in reporting generates summary statistics and plots without needing external RMarkdown files.

## How to Run

1.  Open a terminal in the `water_temp_app` folder.
2.  Run the setup script (only needed once):
    ```bash
    pip install -r requirements.txt
    ```
3.  Start the app:
    ```bash
    streamlit run app.py
    ```
    Or simply run `./run_app.sh`.

## Workflow Overview

### 1. Format Data
-   Upload your raw CSV.
-   Set "Rows to Skip" and select columns to keep.
-   **Timezone Conversion**: If your data is not in UTC (e.g., PDT), check "Convert Timestamp to UTC?" and enter the offset (e.g., -7). You can preview the conversion before saving.
-   Enter metadata (Station Code, Logger Serial, etc.).
-   Click **Save Formatted Data**.

### 2. Flag Compile
-   Select the formatted file.
-   Adjust QAQC thresholds (Spike, Range, etc.).
-   Enter Field Visit times to flag data collected during visits.
-   Click **Run QAQC** to see the results and **Save Flagged Data** to save the "Tidy" file.

### 3. Review Data
-   Load a Tidy file.
-   Use the interactive plot to spot issues.
-   Edit the `wtmp_flag` column in the table if needed.
-   Add notes and click **Save Reviewed Data**.

### 4. Report & Annual
-   Generate single-file reports or compile multiple files into an annual dataset.
-   The "Annual" module handles duplicate timestamps using the logic from your R scripts (averaging passed data, flagging conflicts).

## Next Steps
-   Try running the app with your actual data.
-   If you need to adjust the QAQC logic, you can modify `modules/flag_compile.py`.
