import pandas as pd
import os
import shutil

# Create a dummy dataframe
df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})

# Save as Excel
df.to_excel('test_file.xlsx', index=False)

# Copy to .csv to simulate the user's error
shutil.copy('test_file.xlsx', 'test_renamed.csv')

print("Created test files: test_file.xlsx, test_renamed.csv")

# Test 1: Explicit Excel Loading
try:
    print("\nTest 1: Reading test_file.xlsx...")
    df_loaded = pd.read_excel('test_file.xlsx')
    print("Success! Content:")
    print(df_loaded)
except Exception as e:
    print(f"Failed: {e}")

# Test 2: Fallback Loading
print("\nTest 2: Reading test_renamed.csv (Fallback Logic)...")
try:
    # Mimic the logic in format_data.py
    try:
        df_fallback = pd.read_csv('test_renamed.csv')
        print("Surprisingly read as CSV (unexpected for binary excel)!")
    except (UnicodeDecodeError, pd.errors.ParserError):
        print("caught expected CSV error, attempting fallback...")
        df_fallback = pd.read_excel('test_renamed.csv')
        print("Success! Fallback worked. Content:")
        print(df_fallback)
except Exception as e:
    print(f"Failed: {e}")

# Cleanup
os.remove('test_file.xlsx')
os.remove('test_renamed.csv')
print("\nCleanup complete.")
