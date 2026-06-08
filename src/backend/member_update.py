import os
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from postgres_db import PostgresDB

load_dotenv()

SHEET_ID  = "1DwfSCPW9l2D7wM_GAwz31_h6Qxm3egoK24vD91RvCBk"
SHEET_TAB = "Age-grade"
SCOPES    = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

def get_gspread_client() -> gspread.Client:
    creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH")
    if not creds_path:
        raise ValueError("GOOGLE_SHEETS_CREDENTIALS_PATH not set in .env")
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)

def main():
    db = PostgresDB.from_env()

    print("Reading Google Sheet...")
    df_sheet = read_sheet()
    if df_sheet is None or df_sheet.empty:
        print("No data read from sheet.")
        return
    print(f"  {len(df_sheet)} rows from sheet.")

    print("Loading members from DB...")
    df_members = db.select_df("SELECT first_name, last_name, team FROM usatf.members")
    df_members['_key']      = make_key(df_members, 'first_name', 'last_name', 'team')
    df_members['_name_key'] = make_name_key(df_members, 'first_name', 'last_name')

    df_sheet['_key']      = make_key(df_sheet, 'first_name', 'last_name', 'team')
    df_sheet['_name_key'] = make_name_key(df_sheet, 'first_name', 'last_name')

    # Rows where first+last+team all match — nothing to do
    missing_mask = ~df_sheet['_key'].isin(df_members['_key'])
    df_missing = df_sheet[missing_mask].copy()
    print(f"  {len(df_missing)} rows not matched by name+team.")

    if df_missing.empty:
        print("Nothing to update.")
        return

    # Split missing into: name matches but team changed vs. truly new
    team_changed_mask = df_missing['_name_key'].isin(df_members['_name_key'])
    df_team_changed = df_missing[team_changed_mask].copy()
    df_truly_missing = df_missing[~team_changed_mask].copy()

    # Update team for name-matched rows
    if not df_team_changed.empty:
        print(f"  {len(df_team_changed)} member(s) with changed team — updating...")
        assert db.conn is not None
        cursor = db.conn.cursor()
        for _, row in df_team_changed.iterrows():
            cursor.execute(
                "UPDATE usatf.members SET team = %s "
                "WHERE LOWER(first_name) = %s AND LOWER(last_name) = %s",
                (
                    str(row['team']).strip(),
                    str(row['first_name']).strip().lower(),
                    str(row['last_name']).strip().lower(),
                )
            )
            old_team = df_members.loc[
                df_members['_name_key'] == row['_name_key'], 'team'
            ].iloc[0]
            print(f"    ~ {row['first_name']} {row['last_name']} | '{old_team}' -> '{row['team']}'")
        db.conn.commit()

    df_missing = df_truly_missing
    print(f"  {len(df_missing)} truly new name(s) not found in usatf.members.")

    if df_missing.empty:
        print("No new members to insert.")
        return

    print("Searching usatf.results for age & sex...")
    df_results = db.select_df(
        "SELECT LOWER(first_name) AS first_name_lower, "
        "       LOWER(last_name)  AS last_name_lower, "
        "       sex, age "
        "FROM usatf.results "
        "WHERE first_name IS NOT NULL AND last_name IS NOT NULL"
    )

    rows_to_insert = []
    not_found = []

    for _, row in df_missing.iterrows():
        fn = str(row['first_name']).strip().lower()
        ln = str(row['last_name']).strip().lower()

        match = df_results[
            (df_results['first_name_lower'] == fn) &
            (df_results['last_name_lower'] == ln)
        ]

        if match.empty:
            not_found.append(f"{row['first_name']} {row['last_name']} ({row['team']})")
            continue

        # Use most-frequent sex and most-recent (last) age
        sex = match['sex'].mode().iloc[0] if not match['sex'].mode().empty else None
        age = int(match['age'].iloc[-1]) if pd.notna(match['age'].iloc[-1]) else None

        rows_to_insert.append({
            'first_name': str(row['first_name']).strip(),
            'last_name':  str(row['last_name']).strip(),
            'sex':        sex,
            'age':        age,
            'team':       str(row['team']).strip(),
        })

    if rows_to_insert:
        df_insert = pd.DataFrame(rows_to_insert)
        db.insert_df(df_insert, 'usatf.members')
        print(f"  Inserted {len(df_insert)} new member(s).")
        for r in rows_to_insert:
            print(f"    + {r['first_name']} {r['last_name']} | {r['team']} | sex={r['sex']} age={r['age']}")
    else:
        print("  No insertable rows found in results.")

    if not_found:
        print(f"\n  {len(not_found)} name(s) not found in usatf.results either:")
        for name in not_found:
            print(f"    ? {name}")


def read_sheet(tab: str = SHEET_TAB) -> pd.DataFrame | None:
    """Fetch a tab from Google Sheets as a DataFrame using gspread."""
    try:
        gc = get_gspread_client()
        sh = gc.open_by_key(SHEET_ID)
        ws = sh.worksheet(tab)
        data = ws.get_all_records()
    except Exception as e:
        print(f"Failed to read sheet tab '{tab}': {e}")
        return None

    if not data:
        print(f"Tab '{tab}' is empty.")
        return None

    df = pd.DataFrame(data)

    # Normalize column names: First -> first_name, Last -> last_name
    rename = {}
    for col in df.columns:
        lc = col.strip().lower()
        if lc == 'first':
            rename[col] = 'first_name'
        elif lc == 'last':
            rename[col] = 'last_name'
        elif lc == 'team':
            rename[col] = 'team'
    df = df.rename(columns=rename)

    if not {'first_name', 'last_name', 'team'}.issubset(df.columns):
        print(f"Unexpected sheet columns: {list(df.columns)}")
        return None

    df = df[['first_name', 'last_name', 'team']].copy()
    df = df.dropna(subset=['first_name', 'last_name', 'team'])
    df = df[df['first_name'].astype(str).str.strip() != '']
    return df.reset_index(drop=True)


def make_key(df: pd.DataFrame, first_col: str, last_col: str, team_col: str) -> pd.Series:
    """Build a lowercase composite key: first_name|last_name|team."""
    return (
        df[first_col].str.strip().str.lower() + '|' +
        df[last_col].str.strip().str.lower()  + '|' +
        df[team_col].str.strip().str.lower()
    )


def make_name_key(df: pd.DataFrame, first_col: str, last_col: str) -> pd.Series:
    """Build a lowercase name-only key: first_name|last_name."""
    return (
        df[first_col].str.strip().str.lower() + '|' +
        df[last_col].str.strip().str.lower()
    )


if __name__ == '__main__':
    main()
