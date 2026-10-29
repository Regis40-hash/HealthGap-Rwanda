
from pathlib import Path
import pandas as pd

# Load the same analysis file used by HealthGap Rwanda.
root = Path(__file__).resolve().parent
csv_path = root / "outputs" / "geographic_access_analysis.csv"
df = pd.read_csv(csv_path, dtype={"sector_code": str})

# Ensure score inputs are numeric.
for col in ["nearest_feature_distance_km", "estimated_population"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

distance = df["nearest_feature_distance_km"]
population = df["estimated_population"]

valid_distance = distance.notna()
valid_population = population.notna()
scoreable = valid_distance & valid_population

# Reproduce the dashboard's score calculation.
distance_max = distance[valid_distance].max()
population_min = population[valid_population].min()
population_max = population[valid_population].max()

df["priority_score"] = float("nan")

if (
    pd.notna(distance_max)
    and distance_max > 0
    and pd.notna(population_min)
    and population_max > population_min
):
    distance_score = distance / distance_max * 100
    population_score = (
        (population - population_min)
        / (population_max - population_min)
        * 100
    )

    df.loc[scoreable, "priority_score"] = (
        0.60 * distance_score[scoreable]
        + 0.40 * population_score[scoreable]
    )

# Apply the dashboard's provisional priority bands.
df["priority_band"] = "Not scored"
scored = df["priority_score"].notna()

df.loc[
    scored & (df["priority_score"] >= 70), "priority_band"
] = "Higher priority"

df.loc[
    scored
    & (df["priority_score"] >= 40)
    & (df["priority_score"] < 70),
    "priority_band",
] = "Moderate priority"

df.loc[
    scored & (df["priority_score"] < 40), "priority_band"
] = "Lower priority"

# 1. Basic data and score integrity checks.
print("\n=== DATA VALIDATION ===")
print(f"Rows: {len(df)}")
print(f"Unique sector codes: {df['sector_code'].nunique()}")
print(f"Duplicate sector codes: {df['sector_code'].duplicated().sum()}")
print(f"Missing distances: {distance.isna().sum()}")
print(f"Missing populations: {population.isna().sum()}")
print(f"Scored sectors: {df['priority_score'].notna().sum()}")

scores = df["priority_score"].dropna()
print(f"Scores within 0-100: {scores.between(0, 100).all()}")
print(f"Missing-input sectors incorrectly scored: "
      f"{df.loc[~scoreable, 'priority_score'].notna().sum()}")

print("\n=== PRIORITY BAND COUNTS ===")
print(df["priority_band"].value_counts().to_string())

# 2. Inspect the highest-ranked sectors.
columns = [
    "sector_code",
    "province",
    "district",
    "sector",
    "estimated_population",
    "mapped_feature_count",
    "nearest_feature_distance_km",
    "priority_score",
    "priority_band",
]

columns = [c for c in columns if c in df.columns]

print("\n=== TOP 10 SCREENING PRIORITIES ===")
print(
    df.sort_values("priority_score", ascending=False)[columns]
    .head(10)
    .round({"priority_score": 1, "nearest_feature_distance_km": 2})
    .to_string(index=False)
)

# 3. Show sectors with no mapped features in their own sector.
print("\n=== SECTORS WITH ZERO MAPPED FEATURES ===")
zero_features = df[df["mapped_feature_count"] == 0]

if zero_features.empty:
    print("No sectors have a mapped-feature count of zero.")
else:
    print(
        zero_features.sort_values(
            "priority_score", ascending=False, na_position="last"
        )[columns]
        .head(10)
        .round({"priority_score": 1, "nearest_feature_distance_km": 2})
        .to_string(index=False)
    )

# Save a separate validation output; the original CSV is unchanged.
out_path = root / "outputs" / "priority_score_validation.csv"
df[columns].to_csv(out_path, index=False)
print(f"\nValidation results saved to: {out_path}")
