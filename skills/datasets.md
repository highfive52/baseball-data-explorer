# Lehman Baseball API - Dataset Guide

This document describes the datasets available in the Lehman Baseball Analytics system and how they relate to each other.

---

# Available Datasets

## Batting

**Purpose:** Offensive player statistics.

**Key fields:**
- playerID (string)
- yearID (int)
- teamID (string)
- AB (at-bats)
- H (hits)
- HR (home runs)
- RBI (runs batted in)
- BB (walks)
- SO (strikeouts)

**Notes:**
- This is the primary dataset for offensive aggregations.
- It is often joined with `people` data for player names.

---

## Batting Top

**Purpose:** API-generated career batting leaders for a selected batting stat.

**Key fields:**
- playerID (string)
- nameFirst (string)
- nameLast (string)
- debut (date, earliest debut seen for the player)
- finalGame (date, latest final game seen for the player)
- stat_total (int, career total for the requested stat)

**Additional fields when `include_details=true`:**
- career_games (int)
- career_hits (int)
- career_at_bats (int)
- batting_average (float, rounded to 3 decimals)

**Notes:**
- This endpoint is used for leaderboard-style results by stat category.
- Supported stat categories include `H`, `2B`, `3B`, `HR`, `SB`, and `RBI`.
- Response metadata includes `dataset`, `aggregation`, `stat`, `include_details`, `row_count`, and `limit`.
- The aggregation value is `career_total_by_player`.
- Use the `limit` parameter to control how many ranked results are returned. The API default is 50 and the allowed range is 1 to 500.
- Set `include_details=true` to include the four extra career summary fields listed above.
- Rows are ordered by `stat_total` descending, then `nameLast` ascending, then `nameFirst` ascending.
- Treat the extra detail fields as optional when building downstream tables.

---

## Pitching

**Purpose:** Pitcher performance statistics

**Key fields:**
- playerID
- yearID
- teamID
- W (wins)
- L (losses)
- ERA (earned run average)
- SO (strikeouts)
- BB (walks)

---

## Fielding

**Purpose:** Defensive performance statistics

**Key fields:**
- playerID
- yearID
- teamID
- PO (putouts)
- A (assists)
- E (errors)

---

## Appearances

**Purpose:** Tracks player participation by position and game

**Key fields:**
- playerID
- yearID
- teamID
- G_all (games played)
- GS (games started)

---

## People

**Purpose:** Player and personnel metadata

**Key fields:**
- playerID
- nameFirst
- nameLast
- nameGiven
- debut
- finalGame
- birthYear, birthMonth, birthDay
- height, weight
- bats, throws

---

# Relationships Between Datasets

All major datasets share these common keys:

- playerID → primary join key across datasets
- yearID → temporal dimension
- teamID → team-level grouping

Typical joins:

- batting ↔ people via playerID
- pitching ↔ people via playerID
- fielding ↔ people via playerID
- appearances ↔ people via playerID

---

# Joined and Enriched Datasets

Some datasets may include pre-joined fields such as:

- nameFirst
- nameLast
- nameGiven

These are derived from the `people` dataset.

---

# Schema Notes

- Not all datasets contain the same columns
- Some fields may be null depending on historical completeness
- Always inspect available columns before performing transformations
- Column names are case-sensitive

---

# Common Analytical Patterns

## Aggregate batting stats by player

- Group by: playerID (+ name fields if available)
- Metrics: HR, H, RBI, etc.
- Often aggregated across all years (career totals)
- For common leaderboard queries, prefer `/data/batting/top` instead of recomputing career totals client-side.

## Time-based analysis

- Group by yearID
- Track trends over time (e.g., HR per season)

## Team-level analysis

- Group by teamID and yearID
- Compare performance across teams/seasons

---

# Important Usage Rules

- Use playerID as the primary join key
- Do not assume all datasets include name fields
- Validate columns before grouping or aggregating
- Prefer explicit joins when combining datasets

---

# Design Intent

- Datasets are optimized for analytical workloads
- Data is stored as parquet and queried via DuckDB
- API serves filtered subsets; deeper analysis is typically performed client-side using pandas