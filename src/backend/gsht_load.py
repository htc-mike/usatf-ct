"""
gsht_load.py — Sync PostgreSQL DB → Google Sheet.

Creates any missing tabs, then reloads data from the DB.

Usage:
    python gsht_load.py              # reload all tables
    python gsht_load.py --ref        # reference tables only (events, age_grade, members)
    python gsht_load.py --events     # event result tables only
"""

import argparse
import pandas as pd
import data_db as db
import data_gsht as gsht


def _reload_tab(tab_name: str, df: pd.DataFrame):
    """Overwrite a tab with fresh data (clears first, then writes header + rows)."""
    sh = gsht._open_sheet()
    ws = sh.worksheet(tab_name)
    ws.clear()
    if not df.empty:
        rows = [df.columns.tolist()] + df.fillna('').astype(str).values.tolist()
        ws.update(rows)
    print(f"  {tab_name}: {len(df)} row(s)")


def load_reference_tables():
    print("Loading reference tables...")
    _reload_tab(gsht.TAB_EVENTS,    pd.DataFrame(db.get_events()))
    _reload_tab(gsht.TAB_AGE_GRADE, db.get_age_grade_data())
    _reload_tab(gsht.TAB_MEMBERS,   db.get_members())


def load_event_tables():
    print("Loading event tables...")
    _reload_tab(gsht.TAB_RESULTS,           db.get_all_results())
    _reload_tab(gsht.TAB_INDIVIDUAL,        db.get_individuals())
    _reload_tab(gsht.TAB_INDIVIDUAL_POINTS, db.get_individual_points())
    _reload_tab(gsht.TAB_TEAM_INDIVIDUAL,   db.get_team_individuals())
    _reload_tab(gsht.TAB_TEAM_POINTS,       db.get_team_points())


def main():
    parser = argparse.ArgumentParser(description="Sync DB → Google Sheet")
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--ref',    action='store_true', help='Reference tables only (events, age_grade, members)')
    group.add_argument('--events', action='store_true', help='Event result tables only')
    args = parser.parse_args()

    print("Ensuring all tabs exist...")
    gsht.create_all_tabs()
    print()

    if args.ref:
        load_reference_tables()
    elif args.events:
        load_event_tables()
    else:
        load_reference_tables()
        print()
        load_event_tables()

    print("\nDone.")


if __name__ == '__main__':
    main()
