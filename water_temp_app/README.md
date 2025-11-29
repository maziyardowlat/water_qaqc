# Water Temperature QAQC App

This application converts the original R scripts into a unified Python Streamlit app.

## Features
1.  **Format Data**: Upload raw CSVs, filter "Logged" rows, rename columns, and add metadata.
2.  **Flag Compile**: Run QAQC checks (Spikes, Range, Rate of Change) and assign flags.
3.  **Review**: Interactively review data, edit flags, and add notes.
4.  **Report**: Generate summary statistics and plots for individual files.
5.  **Annual Report**: Compile multiple files, handle duplicates, and generate annual reports.

## Setup

1.  **Create and Activate Virtual Environment** (Recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the App**:
    ```bash
    streamlit run app.py
    ```

    *Alternatively, just run `./run_app.sh` which handles this for you.*

## Usage

-   **Project Directory**: On the sidebar, you can set the "Project Directory". The app will create `01_Data` folders inside this directory to store your files.
-   **Workflow**: Follow the tabs in order: Format -> Flag Compile -> Review -> Report -> Annual.

## Notes
-   The app abstracts away the hardcoded OneDrive paths. You can point it to any folder.
-   Missing `.Rmd` files from the original R code were replaced with built-in Streamlit reporting.
