"""
data_gsht.py — Google Sheets mirror of data_db.py.

Reads and writes the same logical tables to a dedicated Google Sheet.
Each DB table maps to a tab of the same name (without the schema prefix).
Sheet: https://docs.google.com/spreadsheets/d/1duaxxGoDG4F7_YLrqPrtH88O-nbUCMsudrcHmYLowsY
"""

import os
import gspread
from gspread.utils import ValueInputOption
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

SHEET_ID = "1duaxxGoDG4F7_YLrqPrtH88O-nbUCMsudrcHmYLowsY"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

TAB_EVENTS            = "events"
TAB_AGE_GRADE         = "age_grade"
TAB_MEMBERS           = "members"
TAB_RESULTS           = "results"
TAB_INDIVIDUAL        = "individual"
TAB_INDIVIDUAL_POINTS = "individual_points"
TAB_TEAM_INDIVIDUAL   = "team_individual"
TAB_TEAM_POINTS       = "team_points"

_sheet: gspread.Spreadsheet | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_client() -> gspread.Client:
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
    if not creds_path:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH not set in .env")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)  # type: ignore[attr-defined]


def _open_sheet() -> gspread.Spreadsheet:
    global _sheet
    if _sheet is None:
        _sheet = _get_client().open_by_key(SHEET_ID)
    return _sheet


def _read_tab(tab_name: str) -> pd.DataFrame:
    """Read a tab and return as DataFrame with inferred numeric types."""
    ws = _open_sheet().worksheet(tab_name)
    data = ws.get_all_values()
    if not data or len(data) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(data[1:], columns=data[0])
    for col in df.columns:
        non_empty = df[col].astype(str).str.strip() != ''
        converted = pd.to_numeric(df[col].replace('', float('nan')), errors='coerce')
        if non_empty.any() and converted[non_empty].notna().all():  # type: ignore[index]
            df[col] = converted
    return df


def _append_df(tab_name: str, df: pd.DataFrame):
    """Append DataFrame rows. If the tab is empty, writes the header row first."""
    ws = _open_sheet().worksheet(tab_name)
    existing = ws.get_all_values()
    rows = df.fillna('').astype(str).values.tolist()
    if not existing:
        ws.update([df.columns.tolist()] + rows)
    else:
        ws.append_rows(rows, value_input_option=ValueInputOption.user_entered)


def _clear_tab_data(tab_name: str):
    """Clear all data rows, preserving the header row."""
    ws = _open_sheet().worksheet(tab_name)
    data = ws.get_all_values()
    if not data:
        return
    ws.clear()
    ws.update([data[0]])


def _delete_rows_by_event(tab_name: str, event_id: int):
    """Remove all rows where the event_id column matches, preserving the header.
    Reads the full tab, filters in memory, then rewrites — faster than row-by-row deletion."""
    ws = _open_sheet().worksheet(tab_name)
    data = ws.get_all_values()
    if not data or len(data) < 2:
        return
    headers = data[0]
    try:
        col_idx = headers.index('event_id')
    except ValueError:
        return
    kept = [row for row in data[1:]
            if len(row) <= col_idx or str(row[col_idx]) != str(event_id)]
    ws.clear()
    ws.update([headers] + kept)


# ---------------------------------------------------------------------------
# Read functions
# ---------------------------------------------------------------------------

def get_event(id: int) -> pd.DataFrame:
    df = _read_tab(TAB_EVENTS)
    if df.empty:
        return df
    return df[df['id'] == id].reset_index(drop=True)  # type: ignore[return-value]


def get_events() -> list[dict]:
    return _read_tab(TAB_EVENTS).to_dict('records')


def get_age_grade_data() -> pd.DataFrame:
    return _read_tab(TAB_AGE_GRADE)


def get_members() -> pd.DataFrame:
    return _read_tab(TAB_MEMBERS)


def get_results(event_id: int) -> pd.DataFrame:
    df = _read_tab(TAB_RESULTS)
    if df.empty:
        return df
    return df[df['event_id'] == event_id].reset_index(drop=True)  # type: ignore[return-value]


def get_individuals() -> pd.DataFrame:
    return _read_tab(TAB_INDIVIDUAL)


def get_individual_points() -> pd.DataFrame:
    return _read_tab(TAB_INDIVIDUAL_POINTS)


def get_team_individuals() -> pd.DataFrame:
    return _read_tab(TAB_TEAM_INDIVIDUAL)


def get_team_points() -> pd.DataFrame:
    return _read_tab(TAB_TEAM_POINTS)


def get_team_totals() -> pd.DataFrame:
    """Mirrors v_team_totals: total_points and team_rank per team across all events."""
    df = get_team_points()
    if df.empty:
        return df
    df['team_points'] = pd.to_numeric(df['team_points'], errors='coerce').fillna(0)  # type: ignore[arg-type]
    totals: pd.DataFrame = (
        df.groupby('team')['team_points']
        .sum()
        .reset_index()  # type: ignore[union-attr]
        .rename(columns={'team_points': 'total_points'})
        .sort_values('total_points', ascending=False)
        .reset_index(drop=True)
    )
    totals['team_rank'] = range(1, len(totals) + 1)
    return totals


def get_team_event_division_gender_totals() -> pd.DataFrame:
    """Mirrors v_team_event_division_gender_totals: per-event/division/gender totals with rank."""
    df = get_team_points()
    if df.empty:
        return df
    df['team_points'] = pd.to_numeric(df['team_points'], errors='coerce').fillna(0)  # type: ignore[arg-type]
    df['event_id']    = pd.to_numeric(df['event_id'],    errors='coerce')
    totals: pd.DataFrame = (
        df.groupby(['event_id', 'division', 'gender', 'team'])['team_points']
        .sum()
        .reset_index()  # type: ignore[union-attr]
        .rename(columns={'team_points': 'total_points'})
    )
    totals['team_rank'] = (
        totals.groupby(['event_id', 'division', 'gender'])['total_points']
        .rank(method='min', ascending=False)
        .astype(int)
    )
    return totals.sort_values(
        ['event_id', 'division', 'gender', 'team_rank']
    ).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Write functions
# ---------------------------------------------------------------------------

def load_events(df: pd.DataFrame):
    _append_df(TAB_EVENTS, df)


def load_age_grade(df: pd.DataFrame):
    _append_df(TAB_AGE_GRADE, df)


def load_results(event_id: int, df: pd.DataFrame):
    df = df.copy()
    df['event_id'] = event_id
    _append_df(TAB_RESULTS, df)


def load_individuals(df: pd.DataFrame):
    _append_df(TAB_INDIVIDUAL, df)


def load_individual_points(df: pd.DataFrame):
    _append_df(TAB_INDIVIDUAL_POINTS, df)


def load_team_individuals(df: pd.DataFrame):
    _append_df(TAB_TEAM_INDIVIDUAL, df)


def load_team_points(df: pd.DataFrame):
    _append_df(TAB_TEAM_POINTS, df)


def load_members(df: pd.DataFrame):
    _append_df(TAB_MEMBERS, df)


# ---------------------------------------------------------------------------
# Maintenance functions
# ---------------------------------------------------------------------------

TAB_HEADERS: dict[str, list[str]] = {
    TAB_EVENTS: [
        'id', 'name', 'date', 'location', 'dist_mi', 'tab_name', 'col_name',
    ],
    TAB_AGE_GRADE: [
        'sex', 'age',
        '_1_00', '_3_11', '_3_73', '_4_00', '_4_97', '_5_00', '_6_21',
        '_7_46', '_9_32', '_10_00', '_12_43', '_13_10', '_15_53', '_18_64',
        '_26_20', '_31_07', '_50_00', '_62_14', '_93_21', '_100_00', '_124_27',
    ],
    TAB_MEMBERS: [
        'first_name', 'last_name', 'sex', 'age', 'team', 'division', 'created_at',
    ],
    TAB_RESULTS: [
        'event_id', 'first_name', 'last_name', 'name', 'place', 'sex', 'age',
        'time', 'time_in_millis',
    ],
    TAB_INDIVIDUAL: [
        'event_id', 'overall_race_rank', 'runner', 'gender', 'age', 'team',
        'time', 'time_in_millis', 'age_grade', 'age_grade_rank', 'gender_rank',
        'open_rank', 'masters_rank', 'grandmasters_rank', 'seniors_rank',
        'open_m_rank', 'open_f_rank', 'masters_m_rank', 'masters_f_rank',
        'grandmasters_m_rank', 'grandmasters_f_rank', 'seniors_m_rank', 'seniors_f_rank',
    ],
    TAB_INDIVIDUAL_POINTS: [
        'event_id', 'division', 'gender', 'rank', 'points', 'runner', 'team',
        'age', 'time', 'time_in_millis',
    ],
    TAB_TEAM_INDIVIDUAL: [
        'event_id', 'division', 'gender', 'rank', 'team', 'team_time',
        'team_time_in_millis', 'overall_race_rank', 'runner', 'age', 'time', 'time_in_millis',
    ],
    TAB_TEAM_POINTS: [
        'event_id', 'division', 'gender', 'rank', 'team', 'team_points',
    ],
}


def create_all_tabs():
    """Create any missing tabs and write their header row. Existing tabs are left untouched."""
    sh = _open_sheet()
    existing = {ws.title for ws in sh.worksheets()}
    created = []
    for tab_name, headers in TAB_HEADERS.items():
        if tab_name not in existing:
            ws = sh.add_worksheet(title=tab_name, rows=1000, cols=len(headers))
            ws.update([headers])
            created.append(tab_name)
            print(f"  Created tab: {tab_name}")
        else:
            print(f"  Tab already exists: {tab_name}")
    if not created:
        print("All tabs already exist — nothing created.")
    else:
        print(f"Created {len(created)} tab(s): {created}")


def truncate_event_tables():
    """Clear all data rows from the four event-related tabs (preserves headers)."""
    for tab in (TAB_INDIVIDUAL, TAB_INDIVIDUAL_POINTS, TAB_TEAM_INDIVIDUAL, TAB_TEAM_POINTS):
        _clear_tab_data(tab)


def delete_event_tables(event_id: int):
    """Delete all rows matching event_id from the four event-related tabs."""
    for tab in (TAB_INDIVIDUAL, TAB_INDIVIDUAL_POINTS, TAB_TEAM_INDIVIDUAL, TAB_TEAM_POINTS):
        _delete_rows_by_event(tab, event_id)
