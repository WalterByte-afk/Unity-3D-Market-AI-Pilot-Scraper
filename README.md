# Unity Asset Store 3D Scraper

This scraper extracts the first 12 assets from the Unity Asset Store 3D category and writes a JSON file `Unity_3D_Market_Intel.json` containing a `market_analysis` header and an `assets` list.

Setup

1. Create a Python virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```

Run

```bash
python scraper.py
```

Output

- `Unity_3D_Market_Intel.json` — JSON file with `market_analysis` header and `assets` (prices as floats).

Notes

- The script uses heuristic selectors for Unity Asset Store cards and includes a human-like scrolling routine to trigger lazy-loading. If the site markup changes, you may need to update selectors inside `scraper.py`.
