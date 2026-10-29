
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
CENSUS = BASE / "data" / "census" / "PHC5_Public_microdata.dta"

print("HEALTHGAP RWANDA — CENSUS METADATA CHECK")

with pd.io.stata.StataReader(CENSUS) as reader:
    labels = reader.variable_labels()
    value_labels = reader.value_labels()

print("\n--- VARIABLE LABELS ---")
for col in ["ml01", "ml02", "ml03", "Pop_weight", "HH_weight"]:
    print(f"{col}: {labels.get(col, 'No label found')}")

print("\n--- GEOGRAPHY CODE LABELS ---")
for col in ["ml01", "ml02", "ml03"]:
    print(f"\n{col}:")
    mapping = value_labels.get(col, {})
    if mapping:
        for code, label in list(mapping.items())[:25]:
            print(f"  {code}: {label}")
    else:
        print("  No value-label mapping found.")

print("\nMetadata check complete.")
