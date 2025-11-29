import streamlit as st
import os
import pandas as pd

def get_project_dir():
    if 'project_dir' not in st.session_state:
        st.session_state.project_dir = os.getcwd()
    return st.session_state.project_dir

def set_project_dir(path):
    if os.path.isdir(path):
        st.session_state.project_dir = path
        return True
    return False

def save_data(df, filename, subfolder="01_Data/01_Raw_Formatted"):
    project_dir = get_project_dir()
    full_path = os.path.join(project_dir, subfolder)
    os.makedirs(full_path, exist_ok=True)
    file_path = os.path.join(full_path, filename)
    df.to_csv(file_path, index=False)
    return file_path

def load_data(filename, subfolder="01_Data/01_Raw_Formatted"):
    project_dir = get_project_dir()
    file_path = os.path.join(project_dir, subfolder, filename)
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

def list_files(subfolder="01_Data/01_Raw_Formatted", pattern=None):
    project_dir = get_project_dir()
    full_path = os.path.join(project_dir, subfolder)
    if not os.path.exists(full_path):
        return []
    files = os.listdir(full_path)
    if pattern:
        files = [f for f in files if pattern in f]
    return files
