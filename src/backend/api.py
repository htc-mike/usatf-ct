"""
api.py — FastAPI REST API for USATF-CT Grand Prix.

Data access is abstracted through data_gsht.py (Google Sheets backend).
To switch data sources, update the import below and replace `ds.*` calls.

Run with:
    uvicorn api:app --reload --port 8001
"""
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import data_db as ds  # <-- swap this import to change data source

app = FastAPI(title="USATF-CT Grand Prix API", version="1.0.0")

# ---------------------------------------------------------------------------
# In-memory TTL cache
# ---------------------------------------------------------------------------

CACHE_TTL: float = float("inf")  # session-long; set to 0 to disable, or a number of seconds

_cache: dict[str, tuple[float, Any]] = {}


def cached_endpoint(ttl: float = CACHE_TTL):
    """Decorator: cache successful endpoint responses in memory for `ttl` seconds."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if ttl <= 0:
                return func(*args, **kwargs)
            key = f"{func.__name__}|{args}|{sorted(kwargs.items())}"
            entry = _cache.get(key)
            if entry is not None:
                ts, data = entry
                if time.time() - ts < ttl:
                    return data
            result = func(*args, **kwargs)
            _cache[key] = (time.time(), result)
            return result
        return wrapper
    return decorator

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# members.division uses 2-letter codes: gender prefix (M/F) + division initial
# (O=Open, M=Masters, G=Grandmasters, S=Seniors, V=Veteran).
# This map decodes them to the canonical division names used everywhere else.
MEMBER_DIV_TO_DIVISION: dict[str, str] = {
    "MO": "Open",          "FO": "Open",
    "MM": "Masters",       "FM": "Masters",
    "MG": "Grandmasters",  "FG": "Grandmasters",
    "MS": "Seniors",       "FS": "Seniors",
    "MV": "Veteran",       "FV": "Veteran",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_event_map() -> dict:
    """Return {str(event_id): event_name} from the events tab."""
    try:
        events = ds._read_tab(ds.TAB_EVENTS)
        if not events.empty:
            return dict(zip(events["id"].astype(str), events["name"]))
    except Exception:
        pass
    return {}


def _add_event_name(df: pd.DataFrame) -> pd.DataFrame:
    event_map = _get_event_map()
    df["event_name"] = (
        df["event_id"].astype(str).map(event_map).fillna("")  # type: ignore[arg-type]
        if (event_map and "event_id" in df.columns)
        else ""
    )
    return df


def _add_division_from_age(df: pd.DataFrame, age_col: str = "age") -> pd.DataFrame:
    """
    Add a 'division' column representing the runner's primary (highest) eligible
    age division.  A 55-year-old → 'Grandmasters'; a 38-year-old → 'Open'.
    """
    if age_col not in df.columns:
        df["division"] = ""
        return df
    df = df.copy()
    ages = pd.to_numeric(df[age_col], errors="coerce")

    def _primary(age):
        if pd.isna(age):
            return ""
        if age >= 70:
            return "Veteran"
        if age >= 60:
            return "Seniors"
        if age >= 50:
            return "Grandmasters"
        if age >= 40:
            return "Masters"
        return "Open"

    df["division"] = ages.apply(_primary)  # type: ignore[union-attr]
    return df


def _add_pace(df: pd.DataFrame) -> pd.DataFrame:
    """Add pace_per_mile column (mm:ss) derived from time_in_millis and event dist_mi."""
    if "time_in_millis" not in df.columns or "event_id" not in df.columns:
        return df
    events = ds.get_events()
    dist_map = {int(ev["id"]): float(ev["dist_mi"]) for ev in events if ev.get("dist_mi")}

    def _fmt(s):
        if s != s or s is None:  # NaN
            return ""
        m, sec = divmod(int(s), 60)
        return f"{m}:{sec:02d}"

    millis = pd.to_numeric(df["time_in_millis"], errors="coerce")
    dist   = df["event_id"].map(dist_map)  # type: ignore[arg-type]
    df["pace"] = (millis / 1000 / dist).apply(_fmt)  # type: ignore[operator,union-attr]
    return df


def _to_records(df: pd.DataFrame) -> list:
    """Serialize DataFrame rows: NaN → '', whole-number floats → int, dates → ISO str."""
    import datetime
    records = df.fillna("").to_dict("records")
    for row in records:
        for k, v in row.items():
            if isinstance(v, float) and v.is_integer():
                row[k] = int(v)
            elif isinstance(v, (datetime.date, datetime.datetime)):
                row[k] = v.isoformat()
            elif hasattr(v, 'isoformat'):  # pd.Timestamp and similar
                row[k] = v.isoformat()
    return records


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------

@app.get("/api/cache/clear")
def clear_cache():
    """Flush the in-memory cache (useful after a data update)."""
    _cache.clear()
    return {"cleared": True}


@app.get("/api/events")
@cached_endpoint()
def get_events():
    """All Grand Prix events, with has_results flag."""
    try:
        events = ds.get_events()
        try:
            results_df = ds._read_tab(ds.TAB_RESULTS)
            if not results_df.empty and "event_id" in results_df.columns:
                ids_with_results = set(
                    results_df["event_id"].dropna().astype(int).tolist()
                )
            else:
                ids_with_results = set()
        except Exception:
            ids_with_results = set()
        for ev in events:
            ev["has_results"] = int(ev["id"]) in ids_with_results
        return events
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/results")
@cached_endpoint()
def get_results():
    """
    Raw race results for all events.
    Augmented with event_name, team, and division (via members lookup).
    """
    try:
        df = ds._read_tab(ds.TAB_RESULTS)
        if df.empty:
            return []
        if "place" in df.columns:
            df["place"] = pd.to_numeric(df["place"], errors="coerce")
        if "event_id" in df.columns:
            df["event_id"] = pd.to_numeric(df["event_id"], errors="coerce")
        sort_cols = [c for c in ("event_id", "place") if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, na_position="last").reset_index(drop=True)
        df = _add_event_name(df)

        df = _add_pace(df)

        members = ds.get_members()
        if not members.empty:
            members = members.copy()
            members["full_name"] = (
                members["first_name"].str.strip() + " " + members["last_name"].str.strip()
            )
            df["team"] = (
                df["name"].map(dict(zip(members["full_name"], members["team"]))).fillna("")  # type: ignore[arg-type]
            )
            decoded_div = members["division"].map(MEMBER_DIV_TO_DIVISION).fillna(members["division"])  # type: ignore[arg-type]
            df["division"] = (
                df["name"]
                .map(dict(zip(members["full_name"], decoded_div)))  # type: ignore[arg-type]
                .fillna("")
            )
        else:
            df["team"] = ""
            df = _add_division_from_age(df, "age")
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/individual")
@cached_endpoint()
def get_individual():
    """
    Per-event individual standings with all division rank columns.
    Augmented with event_name and primary division derived from age.
    """
    try:
        df = ds.get_individuals()
        if df.empty:
            return []
        int_cols = [
            c for c in df.columns
            if c.endswith("_rank") or c in ("overall_race_rank", "age_grade_rank", "age", "event_id")
        ]
        for col in int_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        sort_cols = [c for c in ("event_id", "overall_race_rank") if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols, na_position="last").reset_index(drop=True)
        df = _add_event_name(df)
        df = _add_division_from_age(df, "age")
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/individual-points")
@cached_endpoint()
def get_individual_points():
    """Individual points awarded per event/division/gender."""
    try:
        df = ds.get_individual_points()
        if df.empty:
            return []
        df["event_id"] = pd.to_numeric(df["event_id"], errors="coerce")
        for col in ("rank", "points", "age"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = _add_event_name(df)
        df = _add_pace(df)
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team-individual")
@cached_endpoint()
def get_team_individual():
    """
    Scoring team members per event/division/gender.
    Shows which runners contributed to each team's score.
    """
    try:
        df = ds.get_team_individuals()
        if df.empty:
            return []
        df = _add_event_name(df)
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team-event-division-gender-totals")
@cached_endpoint()
def get_team_event_division_gender_totals():
    """
    Team totals and rank per event/division/gender.
    Mirrors v_team_event_division_gender_totals.
    """
    try:
        df = ds.get_team_event_division_gender_totals()
        if df.empty:
            return []
        df = _add_event_name(df)
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team-points")
@cached_endpoint()
def get_team_points():
    """Raw team points rows per event/division/gender/rank."""
    try:
        df = ds.get_team_points()
        if df.empty:
            return []
        df = _add_event_name(df)
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/individual-season-totals")
@cached_endpoint()
def get_individual_season_totals(limit: int = 50):
    """
    Season total points per runner per division, ranked by total points desc.
    Useful for the individual leaderboard on the home page.
    """
    try:
        df = ds.get_individual_points()
        if df.empty:
            return []
        df["points"] = pd.to_numeric(df["points"], errors="coerce").fillna(0)  # type: ignore[union-attr]
        df["age"]    = pd.to_numeric(df["age"],    errors="coerce")
        totals: pd.DataFrame = (
            df.groupby(["runner", "gender", "team"])
            .agg(total_points=("points", "sum"), events=("event_id", "nunique"), age=("age", "max"))
            .reset_index()
        )
        totals = _add_division_from_age(totals, "age")
        totals["rank"] = (
            totals.groupby("gender")["total_points"]
            .rank(method="min", ascending=False)
            .astype(int)
        )
        totals = totals.sort_values("total_points", ascending=False).reset_index(drop=True)
        totals["total_points"] = totals["total_points"].astype(int)
        return _to_records(totals.head(limit))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/team-totals")
@cached_endpoint()
def get_team_totals():
    """Season total points and rank per team (all events combined)."""
    try:
        df = ds.get_team_totals()
        if df.empty:
            return []
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/members")
@cached_endpoint()
def get_members():
    """All registered members with age-derived division, full_name, and races_participated."""
    try:
        df = ds.get_members()
        if df.empty:
            return []
        df = df.copy()
        if "age" in df.columns:
            df["age"] = pd.to_numeric(df["age"], errors="coerce")
        if "first_name" in df.columns and "last_name" in df.columns:
            df["full_name"] = (
                df["first_name"].str.strip() + " " + df["last_name"].str.strip()
            )
        # Derive division from age per USATF rules (highest eligible division)
        df = _add_division_from_age(df, "age")
        # Count distinct events each member has appeared in via results
        try:
            results_df = ds._read_tab(ds.TAB_RESULTS)
            if not results_df.empty and "name" in results_df.columns and "event_id" in results_df.columns:
                race_counts = (
                    results_df.groupby("name")["event_id"]
                    .nunique()
                    .reset_index()
                    .rename(columns={"name": "full_name", "event_id": "races_participated"})
                )
                df = df.merge(race_counts, on="full_name", how="left")
                df["races_participated"] = (
                    pd.to_numeric(df["races_participated"], errors="coerce").fillna(0).astype(int)
                )
            else:
                df["races_participated"] = 0
        except Exception:
            df["races_participated"] = 0
        sort_cols = [c for c in ("last_name", "first_name") if c in df.columns]
        if sort_cols:
            df = df.sort_values(sort_cols).reset_index(drop=True)
        return _to_records(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
