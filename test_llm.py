import pandas as pd
from llm_filter import filter_xray_with_llm
import os

print("Creating dummy Excel file...")
df = pd.DataFrame({
    "ASIN": ["B0111", "B0222", "B0333"],
    "Product Title": ["Cordless Jump Rope for adults", "Heavy Battle Rope 1.5 inch", "Cordless jump rope kids"],
    "Brand": ["BrandA", "BrandB", "BrandC"]
})
test_file = "test_xray.xlsx"
df.to_excel(test_file, index=False)

print("Calling filter_xray_with_llm...")
output_path = filter_xray_with_llm(test_file, "Must be a cordless jump rope for adults")
print("Returned path:", output_path)

if os.path.exists("llm_debug.txt"):
    with open("llm_debug.txt", "r") as f:
        print("\n--- llm_debug.txt ---")
        print(f.read())
else:
    print("\nNo llm_debug.txt found.")
