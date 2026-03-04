import vnstock
import json

comp = vnstock.Company("VCI", "TCB")
profile = comp.overview()
print("Profile Columns:")
print(profile.columns.tolist())
print("\nProfile Data (First Row):")
print(profile.iloc[0].to_dict())
