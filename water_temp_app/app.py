import streamlit as st
from modules import format_data, flag_compile, review, report, annual

st.set_page_config(page_title="Water Temp QAQC", layout="wide")

pages = {
    "Format Data": format_data.app,
    "Flag & Compile": flag_compile.app,
    "Review Data": review.app,
    "Generate Report": report.app,
    "Annual Report": annual.app
}

st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", list(pages.keys()))

pages[selection]()
