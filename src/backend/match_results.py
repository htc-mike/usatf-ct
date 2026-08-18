from unicodedata import name

import pandas as pd, csv
import numpy as np
from datetime import datetime
import os
import data_db as data
import utils

usatf_divisions = [
    {
        "name":"Open",
        "age":16,
        "runners": 5,
        "counts_for_team_points": True,
     },
    {
        "name":"Masters",
        "age":40,
        "runners": 3,
        "counts_for_team_points": True,
     },
    {
        "name":"Grandmasters",
        "age":50,
        "runners": 3,
        "counts_for_team_points": True,
     },
    {
        "name":"Seniors",
        "age":60,
        "runners": 3,
        "counts_for_team_points": True,
     },
    {
        "name":"Veteran",  # individual points only — no team points
        "age":70,
        "runners": 3,
        "counts_for_team_points": False,
     },
]

team_place_points = {
    1: 11,
    2: 9,
    3: 8,
    4: 7,
    5: 6,
    6: 5,
    7: 4,
    8: 3,
}

def main():

    load_file = False
    event_id = None
    results_file = "sneeker.4.miler.csv"

    if load_file:
        load_file_match_results(event_id, results_file)
        df = data.get_results(event_id)
        if not df.empty:
            match_results(event_id, df) # return df_results
    elif event_id:
        reprocess_event(event_id)
    else:
        reprocess_all_events()

def reprocess_event(event_id:int):
    data.delete_event_tables(event_id)
    df = data.get_results(event_id)
    if not df.empty:
        match_results(event_id, df)

def reprocess_all_events():
    data.truncate_event_tables()
    for event in data.get_events():
        print(f"Processing Event: {event['name']}")
        df = data.get_results(event['id'])
        if not df.empty:
            match_results(event['id'], df)


def load_file_match_results(event_id:int, results_file:str):
    ## first_name,last_name,name,place,sex,age,time,time_in_millis

    data.delete_results(event_id)
    data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    events_path = os.path.join(data_dir, results_file)
    df_results = pd.read_csv(events_path)
    data.load_results(event_id, df_results)


def match_results(event_id:int, df_results:pd.DataFrame):
    event = data.get_event(event_id)
    dist_mi = event['dist_mi'].iloc[0]
    event_name = event['name'].iloc[0]
    print(f"Processing Event: {event_name}, Distance: {dist_mi}")
    data.delete_event_tables(event_id)

    df_members = data.get_members()
    df_match = get_match_results(df_members, df_results)
    if df_match is None or df_match.empty:
        print("  No matches found.")
        return

    df_match['event_id'] = event_id
    df_match['dist_mi'] = dist_mi
    df_match["age_grade"] = df_match.apply(get_age_grade, axis=1)
    df_match = df_match.drop(columns=['dist_mi'])
    # assert df_match is not None
    df_match['age_grade_rank'] = pd.Series(df_match['age_grade']).rank(method='max', ascending=False).astype(int)

    df_match['gender_rank'] = df_match.groupby('gender')['time_in_millis'].rank().astype(int)

    # per-division overall ranks (creates columns like 'open_rank', 'masters_rank', ...)
    for division in usatf_divisions:
        col = f"{division['name'].lower()}_rank"
        mask = df_match['age'] >= division['age']
        df_match.loc[mask, col] = df_match.loc[mask, 'time_in_millis'] \
                                         .rank(method='min', ascending=True) \
                                         .astype(int)

    # per-division gender ranks (creates columns like 'open_m_rank', 'open_f_rank', ...)
    for division in usatf_divisions:
        for gender in ['M', 'F']:
            col = f"{division['name'].lower()}_{gender.lower()}_rank"
            mask = (df_match['age'] >= division['age']) & (df_match['gender'] == gender)
            df_match.loc[mask, col] = df_match.loc[mask, 'time_in_millis'] \
                                             .rank(method='min', ascending=True) \
                                             .astype(int)

    # Persist individual
    data.load_individuals(df_match)

    # calculate individual points by division and gender
    individual_points_df = compute_individual_scoring(df_match)
    if individual_points_df is not None and not individual_points_df.empty:
        # Persist individual points
        individual_points_df['event_id'] = event_id
        data.load_individual_points(individual_points_df)

    # Remove Unaffiliated team from the results
    df_match = df_match.loc[~df_match['team'].isin(['Unaffiliated', 'unaffiliated'])]
    df_match = df_match.sort_values(
        by=['time_in_millis', 'overall_race_rank'],
        ascending=[True, True],
    )
    df_match = df_match.drop_duplicates(subset=['runner'], keep='first').reset_index(drop=True)

    points_by_team_list = []
    for division in usatf_divisions:
        for gender in ['M', 'F']:
            mask = (df_match['age'] >= division['age']) & (df_match['gender'] == gender)
            df_div: pd.DataFrame = df_match.loc[mask]
            if df_div.empty:
                continue

            df = get_top_results(df_div, division['runners'])
            df['division'] = division['name']

            # Persist team individual (Veteran is still recorded for tracking)
            data.load_team_individuals(df)

            if not division.get('counts_for_team_points', True):
                continue

            # aggregate team place points
            points_by_team = aggregate_team_place_points(df)
            points_by_team['division'] = division['name']
            points_by_team['gender'] = gender
            points_by_team['event_id'] = event_id
            points_by_team['rank'] = range(1, len(points_by_team) + 1)
            points_by_team_list.append(points_by_team)

    if points_by_team_list:
        all_points = pd.concat(points_by_team_list, ignore_index=True)

        # Persist team points
        data.load_team_points(all_points)

def aggregate_team_place_points(top_match_df, points_map=team_place_points):
    """
    Aggregate team place points from the get_top_results output (top_match_df).
    - Keeps one entry per (team, rank) so a team only earns points once per place.
    - Maps rank -> points using points_map and sums by team.
    Returns a DataFrame with ['team', 'team_points'] sorted descending.
    """
    pts_df = (
        top_match_df[['team', 'rank']]
        .drop_duplicates(subset=['team', 'rank'])
        .assign(points=lambda d: d['rank'].map(points_map).fillna(0).astype(int))
        .groupby('team', as_index=False)['points']
        .sum()
        .rename(columns={'points': 'team_points'})
        .sort_values('team_points', ascending=False)
        .reset_index(drop=True)
    )
    return pts_df

def get_top_results(df, top_n = 3):
    df.to_csv(f'data/top.csv', index=False)
    #
    # Filter runners by top 3 for each club and gender
    #
    # top_filtered_df = df.groupby(['team', 'gender'], group_keys=False).apply(lambda x: x.nsmallest(top_n, 'time_in_millis')).reset_index(drop=True)
    #
    top_filtered_df = (
        df
        .sort_values(['team', 'gender', 'time_in_millis'], ascending=[True, True, True])
        .groupby(['team', 'gender'], group_keys=False)
        .head(top_n)
        .reset_index(drop=True)
    )
    top_filtered_df.to_csv(f'data/top_filtered.csv', index=False)
    
    #
    # Aggregate time and runners by club and gender
    #
    # agg_df = top_filtered_df.groupby(['team', 'gender']).agg({"runner": pd.Series.nunique, "time_in_millis": np.sum})
    #
    agg_df = top_filtered_df.groupby(['team', 'gender'], as_index=False).agg(
        runnerCount=('runner', 'nunique'),
        team_time_in_millis=('time_in_millis', 'sum'),
    )
    agg_df = agg_df.rename(columns={'runner': 'runnerCount', 'time_in_millis': 'team_time_in_millis'})
    agg_df.to_csv(f'data/agg.csv', index=False)

    #
    # Filter our clubs that don't have the minimum 3 participants
    #
    agg_df = agg_df[agg_df['runnerCount'] == top_n]
    # agg_df.to_csv('data/202506/branford.5.miler.matches.top_3_df_group_count.csv')
    agg_df.drop('runnerCount', axis=1, inplace=True)
    agg_df.to_csv(f'data/agg_filtered.csv', index=False)

    #
    # Rank results by gender
    #
    agg_df['rank'] = agg_df.groupby('gender')['team_time_in_millis'].rank().astype(int)
    agg_df.to_csv(f'data/agg_ranked.csv', index=False)
    #
    # Format milliseconds for display as team time.
    #
    agg_df['team_time'] = pd.to_datetime(agg_df['team_time_in_millis'], unit='ms').dt.strftime('%H:%M:%S')

    #
    # Join aggregate club & gender to filtered runners.
    #
    top_match_df = pd.merge(
                agg_df,
                top_filtered_df,
                how="inner",
                left_on=['team', 'gender'],
                right_on=['team', 'gender'],
                )
    top_match_df.sort_values(by=['gender','rank'], inplace=True, ascending=True)
    top_match_df.to_csv(f'data/top_match_df.csv', index=False)

    top_match_df = top_match_df[[
        'event_id',
        'rank',
        'team',
        'gender',
        'team_time',
        'team_time_in_millis',
        'overall_race_rank',
        'runner',
        'age',
        'time',
        'time_in_millis'
    ]]
    return top_match_df

def get_match_results(df_members, df_results) -> pd.DataFrame | None:
    # Columns from file:
    #     first_name,
    #     last_name,
    #     name,
    #     place,
    #     sex,
    #     age,
    #     time,
    #     time_in_millis

    # df_results = pd.read_csv(race_file)
    # df_members = pd.read_csv(member_file)

    # Create matching key: first letter of first_name + full last_name (both lowercase)
    df_members['first_name_lower'] = df_members['first_name'].apply(str.lower)
    df_members['last_name_lower'] = df_members['last_name'].apply(str.lower)
    df_members['match_key'] = df_members['first_name_lower'].str[0] + df_members['last_name_lower'].str[:4]

    # Duplicate rows with age+1 and append to allow matching at age+1
    if 'age' in df_members.columns:
        try:
            df_members_extra = df_members.copy()
            df_members_extra['age'] = df_members_extra['age'].astype(int) + 1
            df_members = pd.concat([df_members, df_members_extra], ignore_index=True)
        except Exception:
            pass
    
    df_results['first_name_lower'] = df_results['first_name'].apply(str.lower)
    df_results['last_name_lower'] = df_results['last_name'].apply(str.lower)
    df_results['age'] = df_results['age'].astype(int)
    df_results['match_key'] = df_results['first_name_lower'].str[0] + df_results['last_name_lower'].str[:4]

    # Ensure gender column exists in results (rename 'sex' if present)
    # if 'sex' in df_results.columns and 'gender' not in df_results.columns:
    #     df_results = df_results.rename(columns={'sex': 'gender'})

    # Primary match: sex + name + age (handles standard M/F runners)
    df_match = pd.merge(
                df_members,
                df_results,
                how="inner",
                left_on=['match_key', 'sex', 'age'],
                right_on=['match_key', 'sex', 'age'],
                )

    # Fallback: runners with non-standard race sex (NB, X, etc.) matched on name+age only.
    # Per rules, score in the gender on their USATF membership.
    df_results_alt = df_results[~df_results['sex'].isin(['M', 'F'])]
    if not df_results_alt.empty:
        df_fb = pd.merge(
                    df_members,
                    df_results_alt,
                    how="inner",
                    left_on=['match_key', 'age'],
                    right_on=['match_key', 'age'],
                    suffixes=('_x', '_y'),
                    )
        if not df_fb.empty:
            df_fb = df_fb.rename(columns={'sex_x': 'sex'}).drop(columns=['sex_y'], errors='ignore')
            df_match = pd.concat([df_match, df_fb], ignore_index=True)
    dupes = df_match[df_match.duplicated(subset=['name'], keep=False)]
    if not dupes.empty:
        print(f"  WARNING: {pd.Series(dupes['name']).nunique()} runner(s) matched multiple members (match_key collision):")
        for runner_name, grp in dupes.groupby('name'):
            print(f"    {runner_name}: matched {list(grp['first_name_x'] + ' ' + grp['last_name_x'])}")

    print(f'  Matches: {str(len(df_match.index))}')

    if len(df_match.index) == 0:
        return None
    else:
        df_match.sort_values(by=['place'], inplace=True, ascending=True)
        df_match = df_match.rename(columns={'name': 'runner'})
        df_match = df_match.rename(columns={'place': 'overall_race_rank'})
        # df_match = df_match.rename(columns={'time_in_millis': 'timeInMillis'})
        df_match = df_match.rename(columns={'sex': 'gender'})
        columns = [
            'overall_race_rank',
            'runner',
            'gender',
            'age',
            'team',
            'time',
            'time_in_millis',
        ]
        return df_match.loc[:, columns]

# def load_member_file(member_file = f'usatf.ct.team.members.2026.official.csv'):
#     data_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data")
#     members_path = os.path.join(data_dir, member_file)
#     df_members = pd.read_csv(members_path)
#     db.insert_df(df_members, 'usatf.members')        

def time_to_millis(row):
    return utils.time_to_millis(row['clock_time'])

def get_age_grade(row):
    return utils.get_age_grade(row['gender'], row['age'], row['dist_mi'], row['time_in_millis'])
    
def compute_individual_scoring(df_match, points_map=None, top_n=10):
    """
    Build a single dataset with division and gender as columns and assigns points based on rank.
    - df_match: matched members/results dataframe (must include age, gender, time_in_millis, runner, team, time)
    - points_map: mapping place -> points (defaults to USATF-CT Grand Prix mapping)
    - top_n: number of places to award per division/gender (default 10)
    Returns the combined DataFrame.
    """
    # defensive checks
    if df_match is None or df_match.empty:
        return pd.DataFrame(columns=[
            'division','gender','rank','points','runner','team','age','time','time_in_millis'
        ])

    if points_map is None:
        points_map = {1: 11, 2: 9, 3: 8, 4: 7, 5: 6, 6: 5, 7: 4, 8: 3, 9: 2, 10: 1}

    out_frames = []
    # ensure gender column exists and normalized
    if 'gender' not in df_match.columns:
        df_match['gender'] = ''
    genders = sorted(df_match['gender'].dropna().unique())

    for division in usatf_divisions:
        div_name = division['name']
        min_age = division['age']

        # eligible runners for this division (age >= min_age)
        df_div = df_match[df_match['age'] >= min_age].copy()
        if df_div.empty:
            continue

        # award points separately by gender
        for gender in genders:
            df_div_g = df_div[df_div['gender'] == gender].copy()
            if df_div_g.empty:
                continue

            df_div_g = df_div_g.sort_values(['time_in_millis', 'overall_race_rank'], ascending=[True, True]).reset_index(drop=True)
            df_div_g = df_div_g.drop_duplicates(subset=['runner'], keep='first')
            df_top = df_div_g.head(top_n).copy()
            if df_top.empty:
                continue

            df_top = df_top.reset_index(drop=True)
            df_top['rank'] = df_top.index + 1
            df_top['points'] = df_top['rank'].map(points_map).fillna(0).astype(int)
            df_top['division'] = div_name
            df_top['gender'] = gender

            out_df = df_top[
                [
                'event_id',
                'division',
                'gender',
                'rank',
                'points',
                'runner',
                'team',
                'age',
                'time',
                'time_in_millis'
                ]
            ].copy()

            out_frames.append(out_df)

    if not out_frames:
        return pd.DataFrame(columns=[
            'division','gender','rank','points','runner','team','age','time','time_in_millis'
        ])

    combined = pd.concat(out_frames, ignore_index=True)
    combined.sort_values(['division','gender','rank'], inplace=True, ascending=[True, True, True])

    return combined

if __name__ == '__main__':
    main()