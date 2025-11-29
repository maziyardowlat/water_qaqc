import streamlit as st
from modules import format_data, flag_compile, review, report, annual

st.set_page_config(page_title="Water Temp QAQC", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Format Data", "Flag Compile", "Review Data", "Generate Report", "Annual Report"])

if page == "Format Data":
    format_data.app()
elif page == "Flag Compile":
    flag_compile.app()
elif page == "Review Data":
    review.app()
elif page == "Generate Report":
    report.app()
elif page == "Annual Report":
    annual.app()
