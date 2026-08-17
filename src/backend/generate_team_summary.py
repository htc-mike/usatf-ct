"""
Generate a team summary markdown file for AI prompts.

Usage:
    python src/backend/generate_team_summary.py "Hartford TC"
    python src/backend/generate_team_summary.py "Hartford TC" --output data/summary/hartford-tc.md
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "frontend" / "public" / "data"
DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "summary"

DIVISION_ORDER = ["Open", "Masters", "Grandmasters", "Seniors", "Veteran"]
GENDER_ORDER = ["M", "F"]


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_json(name: str) -> list[dict]:
    path = DATA_DIR / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def gender_label(g: str) -> str:
    return {"M": "Male", "F": "Female"}.get(g, g)


DIVISION_PREFIX = {
    "Open": "open",
    "Masters": "masters",
    "Grandmasters": "grandmasters",
    "Seniors": "seniors",
    "Veteran": "veteran",
}


def primary_division(age) -> str:
    if age is None or age == "":
        return ""
    age = int(age)
    if age >= 70:
        return "Veteran"
    if age >= 60:
        return "Seniors"
    if age >= 50:
        return "Grandmasters"
    if age >= 40:
        return "Masters"
    return "Open"


def division_gender_rank(row: dict) -> str:
    """Rank within the runner's primary division and gender (e.g. masters_m_rank)."""
    div = row.get("division", "")
    gender = (row.get("gender") or row.get("sex") or "").lower()
    prefix = DIVISION_PREFIX.get(div)
    if not prefix or not gender:
        return "—"
    val = row.get(f"{prefix}_{gender}_rank", "")
    return str(val) if val not in ("", None) else "—"


def rank_by_division_gender(rows: list[dict], points_key: str = "total_points") -> dict[tuple, int]:
    """Assign min-rank within each division/gender by points descending."""
    by_group: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        by_group[(row["division"], row["gender"])].append(row)

    ranks: dict[tuple, int] = {}
    for group_rows in by_group.values():
        sorted_rows = sorted(
            group_rows,
            key=lambda x: (-x[points_key], x.get("runner", "")),
        )
        prev_pts = None
        prev_rank = 0
        for i, row in enumerate(sorted_rows, start=1):
            pts = row[points_key]
            if pts != prev_pts:
                prev_rank = i
                prev_pts = pts
            key = (row["runner"], row["gender"], row["team"], row["division"])
            ranks[key] = prev_rank
    return ranks


def events_with_results(events: list[dict]) -> list[dict]:
    return sorted(
        [e for e in events if e.get("has_results")],
        key=lambda e: e["date"],
    )


def division_gender_key(division: str, gender: str) -> tuple[str, str]:
    return division, gender


def pace_lookup(results: list[dict]) -> dict[tuple[int, str], str]:
    return {
        (r["event_id"], r["name"]): r.get("pace", "")
        for r in results
    }


def format_race_standings(rows: list[dict], team: str, paces: dict[tuple[int, str], str]) -> str:
    if not rows:
        return f"_No {team} finishers._\n"
    lines = [
        "| Place | Runner | Gender | Age | Division | Div/Gender Rank | Time | Pace |",
        "|------:|--------|--------|----:|----------|----------------:|------|------|",
    ]
    for r in sorted(rows, key=lambda x: x.get("overall_race_rank", 9999)):
        pace = paces.get((r["event_id"], r["runner"]), "")
        lines.append(
            f"| {r.get('overall_race_rank', '')} | {r['runner']} | {r.get('gender', '')} | "
            f"{r.get('age', '')} | {r.get('division', '')} | {division_gender_rank(r)} | "
            f"{r.get('time', '')} | {pace} |"
        )
    return "\n".join(lines) + "\n"


def format_team_standings_event(
    team_points: list[dict],
    team_individual: list[dict],
    event_id: int,
    team: str,
) -> str:
    sections: list[str] = []
    by_div_gender: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in team_points:
        if row["event_id"] == event_id:
            by_div_gender[division_gender_key(row["division"], row["gender"])].append(row)

    for division in DIVISION_ORDER:
        for gender in GENDER_ORDER:
            key = division_gender_key(division, gender)
            rows = by_div_gender.get(key, [])
            if not rows:
                continue
            rows = sorted(rows, key=lambda x: x["rank"])
            if not any(r["team"] == team for r in rows):
                continue

            sections.append(f"#### {division} — {gender_label(gender)}\n")
            sections.append("| Rank | Team | Points | Scoring Members |")
            sections.append("|-----:|------|-------:|-----------------|")
            for r in rows:
                members = [
                    ti["runner"]
                    for ti in team_individual
                    if (
                        ti["event_id"] == event_id
                        and ti["division"] == division
                        and ti["gender"] == gender
                        and ti["team"] == r["team"]
                        and ti["rank"] == r["rank"]
                    )
                ]
                member_str = ", ".join(members) if members else "—"
                marker = "**" if r["team"] == team else ""
                marker_end = "**" if r["team"] == team else ""
                sections.append(
                    f"| {r['rank']} | {marker}{r['team']}{marker_end} | "
                    f"{r['team_points']} | {member_str} |"
                )
            sections.append("")

    return "\n".join(sections) if sections else f"_{team} did not score in any division/gender for this event._\n"


def format_individual_points(rows: list[dict]) -> str:
    if not rows:
        return "_No individual points earned._\n"
    lines = [
        "| Division | Gender | Place | Points | Runner | Time | Pace |",
        "|----------|--------|------:|-------:|--------|------|------|",
    ]
    for r in sorted(rows, key=lambda x: (DIVISION_ORDER.index(x["division"]) if x["division"] in DIVISION_ORDER else 99, x["gender"], x["rank"])):
        lines.append(
            f"| {r['division']} | {gender_label(r['gender'])} | {r['rank']} | "
            f"{r['points']} | {r['runner']} | {r.get('time', '')} | {r.get('pace', '')} |"
        )
    return "\n".join(lines) + "\n"


def cumulative_team_standings(
    team_points: list[dict],
    event_ids: list[int],
    team: str,
) -> str:
    totals: dict[tuple[str, str, str], int] = defaultdict(int)
    for row in team_points:
        if row["event_id"] in event_ids:
            key = (row["division"], row["gender"], row["team"])
            totals[key] += row["team_points"]

    sections: list[str] = []
    for division in DIVISION_ORDER:
        for gender in GENDER_ORDER:
            teams = {
                t: pts
                for (d, g, t), pts in totals.items()
                if d == division and g == gender
            }
            if not teams or team not in teams:
                continue
            ranked = sorted(teams.items(), key=lambda x: (-x[1], x[0]))
            sections.append(f"#### {division} — {gender_label(gender)}\n")
            sections.append("| Rank | Team | Total Points |")
            sections.append("|-----:|------|-------------:|")
            for rank, (t, pts) in enumerate(ranked, start=1):
                marker = "**" if t == team else ""
                marker_end = "**" if t == team else ""
                sections.append(f"| {rank} | {marker}{t}{marker_end} | {pts} |")
            sections.append("")
    return "\n".join(sections) if sections else f"_{team} has no cumulative team points in any division/gender._\n"


def build_cumulative_individual_totals(
    individual_points: list[dict],
    event_ids: list[int],
) -> list[dict]:
    totals: dict[tuple[str, str, str, str], dict] = {}
    for row in individual_points:
        if row["event_id"] not in event_ids:
            continue
        key = (row["runner"], row["gender"], row["team"], row["division"])
        if key not in totals:
            totals[key] = {
                "runner": row["runner"],
                "gender": row["gender"],
                "team": row["team"],
                "division": row["division"],
                "total_points": 0,
                "events": set(),
            }
        totals[key]["total_points"] += row["points"]
        totals[key]["events"].add(row["event_id"])
    return list(totals.values())


def cumulative_individual_standings(
    individual_points: list[dict],
    event_ids: list[int],
    team: str,
) -> str:
    all_totals = build_cumulative_individual_totals(individual_points, event_ids)
    team_totals = [r for r in all_totals if r["team"] == team and r["total_points"] > 0]

    if not team_totals:
        return f"_No {team} runners have scored individual points through this event._\n"

    div_gender_ranks = rank_by_division_gender(all_totals)

    rows = sorted(
        team_totals,
        key=lambda x: (
            DIVISION_ORDER.index(x["division"]) if x["division"] in DIVISION_ORDER else 99,
            x["gender"],
            div_gender_ranks.get((x["runner"], x["gender"], x["team"], x["division"]), 999),
            -x["total_points"],
        ),
    )
    lines = [
        "| Div/Gender Rank | Runner | Division | Gender | Total Points | Events Scored |",
        "|----------------:|--------|----------|--------|-------------:|--------------:|",
    ]
    for r in rows:
        rank = div_gender_ranks.get((r["runner"], r["gender"], r["team"], r["division"]), "—")
        lines.append(
            f"| {rank} | {r['runner']} | {r['division']} | {gender_label(r['gender'])} | "
            f"{r['total_points']} | {len(r['events'])} |"
        )
    return "\n".join(lines) + "\n"


def generate_summary(team: str) -> str:
    events = events_with_results(load_json("events"))
    results = load_json("results")
    individual = load_json("individual")
    team_points = load_json("team-points")
    team_individual = load_json("team-individual")
    individual_points = load_json("individual-points")
    team_totals = load_json("team-totals")
    paces = pace_lookup(results)

    htc_total = next((t for t in team_totals if t["team"] == team), None)
    season_line = ""
    if htc_total:
        season_line = (
            f"Season team total: **{htc_total['total_points']} points** "
            f"(rank {htc_total['team_rank']} overall).\n"
        )

    parts = [
        f"# {team} — Grand Prix Summary\n",
        f"USATF-CT Road Grand Prix 2026 season results for **{team}**.\n",
        season_line,
        "---\n",
        "## Event Results\n",
        "Per-event results in chronological order.\n",
    ]

    event_ids_chrono = [e["id"] for e in events]

    for event in events:
        eid = event["id"]
        ename = event["name"]
        edate = event["date"]
        parts.append(f"\n### {ename} ({edate})\n")

        htc_results = [r for r in individual if r.get("team") == team and r["event_id"] == eid]
        parts.append(f"#### Race Standings ({team} Members)\n")
        parts.append(format_race_standings(htc_results, team, paces))

        parts.append("#### Team Standings\n")
        parts.append(
            format_team_standings_event(team_points, team_individual, eid, team)
        )

        htc_indiv = [
            r for r in individual_points
            if r.get("team") == team and r["event_id"] == eid
        ]
        parts.append(f"#### Individual Points ({team} Members)\n")
        parts.append(format_individual_points(htc_indiv))

    parts.append("\n---\n")
    parts.append("## Overall Results\n")
    parts.append(
        "Cumulative standings through each event (includes all prior events in the season).\n"
    )

    for i, event in enumerate(events):
        eid = event["id"]
        ename = event["name"]
        edate = event["date"]
        through_ids = event_ids_chrono[: i + 1]
        parts.append(f"\n### Through {ename} ({edate})\n")

        parts.append("#### Team Standings (cumulative)\n")
        parts.append(cumulative_team_standings(team_points, through_ids, team))

        parts.append(f"#### Individual Standings ({team} scorers, cumulative)\n")
        parts.append(
            cumulative_individual_standings(individual_points, through_ids, team)
        )

    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate team summary markdown for AI prompts")
    parser.add_argument("team", help='Team name, e.g. "Hartford TC"')
    parser.add_argument(
        "--output",
        help="Output file path (default: data/summary/<slug>.md)",
    )
    args = parser.parse_args()

    out = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR / f"{slugify(args.team)}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(generate_summary(args.team), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
