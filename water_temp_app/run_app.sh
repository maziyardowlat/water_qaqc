#!/bin/bash
# Create virtual environment if it doesn't exist
if [ ! -d "water_temp" ]; then
    echo "Creating virtual environment..."
    python3 -m venv water_temp
fi

# Activate virtual environment
source water_temp/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the app
echo "Starting app..."
streamlit run app.py
