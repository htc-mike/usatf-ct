from postgres_db import PostgresDB
import os
import pandas as pd

TBL_INDIVIDUAL = 'usatf.individual'
TBL_INDIVIDUAL_POINTS = 'usatf.individual_points'
TBL_TEAM_INDIVIDUAL = 'usatf.team_individual'
TBL_TEAM_POINTS = 'usatf.team_points'
TBL_RESULTS = 'usatf.results'

# Tab name constants — mirrors data_gsht for drop-in compatibility with api.py
TAB_EVENTS            = 'events'
TAB_AGE_GRADE         = 'age_grade'
TAB_MEMBERS           = 'members'
TAB_RESULTS           = 'results'
TAB_INDIVIDUAL        = 'individual'
TAB_INDIVIDUAL_POINTS = 'individual_points'
TAB_TEAM_INDIVIDUAL   = 'team_individual'
TAB_TEAM_POINTS       = 'team_points'

_TAB_TO_TABLE: dict[str, str] = {
    TAB_EVENTS:            'usatf.events',
    TAB_AGE_GRADE:         'usatf.age_grade',
    TAB_MEMBERS:           'usatf.members',
    TAB_RESULTS:           'usatf.results',
    TAB_INDIVIDUAL:        'usatf.individual',
    TAB_INDIVIDUAL_POINTS: 'usatf.individual_points',
    TAB_TEAM_INDIVIDUAL:   'usatf.team_individual',
    TAB_TEAM_POINTS:       'usatf.team_points',
}

db = PostgresDB.from_env()


def _read_tab(tab_name: str) -> pd.DataFrame:
    """Drop-in replacement for data_gsht._read_tab — reads from Postgres instead."""
    table = _TAB_TO_TABLE.get(tab_name)
    if not table:
        return pd.DataFrame()
    return db.select_df(f"SELECT * FROM {table}")

def main():
    pass

def get_event(id:int):
    return db.select_df(f"SELECT * FROM usatf.events WHERE id = {id}")

def get_events():
    return db.select_dict("SELECT id, name, date::text AS date, location, dist_mi::float AS dist_mi, tab_name, col_name, url FROM usatf.events")

def get_age_grade_data():
    return db.select_df("SELECT * FROM usatf.age_grade")

def get_members():
    return db.select_df("SELECT * FROM usatf.members")

def get_results(event_id:int):
    return db.select_df(f"SELECT * FROM usatf.results WHERE event_id = {event_id}")

def get_all_results():
    return db.select_df("SELECT * FROM usatf.results ORDER BY event_id, place")

def get_individuals():
    return db.select_df("SELECT * FROM usatf.individual ORDER BY event_id")

def get_individual_points():
    return db.select_df("SELECT * FROM usatf.individual_points ORDER BY event_id, division, gender, rank")

def get_team_individuals():
    return db.select_df("SELECT * FROM usatf.team_individual ORDER BY event_id, division, gender, rank")

def get_team_points():
    return db.select_df("SELECT * FROM usatf.team_points ORDER BY event_id, division, gender, rank")

def get_team_event_division_gender_totals():
    return db.select_df("SELECT * FROM usatf.v_team_event_division_gender_totals")

def get_team_totals():
    return db.select_df("SELECT * FROM usatf.v_team_totals")

def load_members(df):
    db.insert_df(df, 'usatf.members')        

def load_results(event_id:int, df):
    df['event_id'] = event_id   
    db.insert_df(df, TBL_RESULTS)

def delete_results(event_id:int):
    db.execute(f"DELETE FROM usatf.results WHERE event_id = {event_id}")

def load_individuals(df):
    db.insert_df(df, TBL_INDIVIDUAL)

def delete_individuals(event_id:int):
    db.execute(f"DELETE FROM usatf.individual WHERE event_id = {event_id}")

def load_individual_points(df):
    db.insert_df(df, TBL_INDIVIDUAL_POINTS)

def delete_individual_points(event_id:int):
    db.execute(f"DELETE FROM usatf.individual_points WHERE event_id = {event_id}")

def load_team_individuals(df):
    db.insert_df(df, TBL_TEAM_INDIVIDUAL)

def delete_team_individuals(event_id:int):
    db.execute(f"DELETE FROM usatf.team_individual WHERE event_id = {event_id}")

def load_team_points(df):
    db.insert_df(df, TBL_TEAM_POINTS)

def truncate_event_tables():
    db.execute("TRUNCATE TABLE usatf.individual")
    db.execute("TRUNCATE TABLE usatf.individual_points")
    db.execute("TRUNCATE TABLE usatf.team_individual")
    db.execute("TRUNCATE TABLE usatf.team_points")

def delete_event_tables(event_id:int):
    db.execute(f"DELETE FROM usatf.individual WHERE event_id = {event_id}")
    db.execute(f"DELETE FROM usatf.individual_points WHERE event_id = {event_id}")
    db.execute(f"DELETE FROM usatf.team_individual WHERE event_id = {event_id}")
    db.execute(f"DELETE FROM usatf.team_points WHERE event_id = {event_id}")

if __name__ == "__main__":
    main()