import vnstock

# Inspect EOD history data
q = vnstock.Quote("VCI", "FPT")
df = q.history(start="2025-01-01", end="2025-01-10", interval="1D")
print("EOD Columns:")
print(df.columns.tolist())
print("\nFirst 5 rows:")
print(df.head())
print("\nDtypes:")
print(df.dtypes)
