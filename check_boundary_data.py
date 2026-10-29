
from pathlib import Path

ROOT = Path(__file__).resolve().parent

print("Searching the project for geographic boundary files...\n")

extensions = {".shp", ".gpkg", ".geojson", ".json", ".gdb", ".zip"}

found = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if path.suffix.lower() in extensions:
        # Ignore the large Python virtual environment.
        if ".venv" in path.parts:
            continue

        found.append(path)

if found:
    for path in found:
        print(path.relative_to(ROOT))
else:
    print("No geographic boundary files found.")
    print("We may need to obtain an administrative boundary dataset.")
