import pandas as pd
df = pd.read_csv('results/master_railway_database.csv')
missing = df[df['Latitude'].isna()]['station'].unique()
print(f"Stations needing manual coordinates: {missing}")