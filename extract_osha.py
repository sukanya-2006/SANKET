import pandas as pd

# Load the massive OSHA CSV you just downloaded
df = pd.read_csv('January2015toNovember2025.csv', low_memory=False)

# Isolate the column with the incident descriptions and drop any blanks
narratives = df['Final Narrative'].dropna()

# Randomly sample exactly 30 reports
sampled_reports = narratives.sample(n=30, random_state=42)

# Save them to your osha data folder
sampled_reports.to_csv('data/osha/osha_real_reports.csv', index=False, header=['report_text'])

print("Successfully saved 30 real OSHA reports!")