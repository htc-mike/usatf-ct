"""
export_data.py — Generate static JSON files for GitHub Pages deployment.

Run this locally whenever data changes, then commit and push:

    python src/backend/export_data.py

Output goes to src/frontend/public/data/*.json
Vite copies public/ into dist/ at build time, so the files are served at:
    https://htc-mike.github.io/usatf-ct/data/<name>.json
"""

import json
import sys
from pathlib import Path

# Make sure the backend package is importable
sys.path.insert(0, str(Path(__file__).parent))

# Import the same functions used by api.py
import api as _api

OUTPUT_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data"


def export(name: str, data) -> None:
    out = OUTPUT_DIR / f"{name}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  wrote {out.relative_to(Path(__file__).parent.parent.parent)} ({len(data)} rows)")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("Exporting data to", OUTPUT_DIR)

    endpoints = [
        ("events",                           _api.get_events),
        ("results",                          _api.get_results),
        ("individual",                       _api.get_individual),
        ("individual-points",                _api.get_individual_points),
        ("individual-season-totals",         lambda: _api.get_individual_season_totals(limit=200)),
        ("team-individual",                  _api.get_team_individual),
        ("team-event-division-gender-totals",_api.get_team_event_division_gender_totals),
        ("team-points",                      _api.get_team_points),
        ("team-totals",                      _api.get_team_totals),
    ]

    ok = True
    for name, fn in endpoints:
        try:
            data = fn()
            export(name, data)
        except Exception as exc:
            print(f"  ERROR exporting {name}: {exc}", file=sys.stderr)
            ok = False

    if ok:
        print("Done — commit src/frontend/public/data/ and push to deploy.")
    else:
        print("Finished with errors — check output above.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
