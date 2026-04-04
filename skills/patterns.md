# Lehman Baseball API - Usage Patterns

This document describes common ways to work with the Lehman Baseball API using Python, pandas, and Streamlit.

---

# Typical Workflow

1. Call an API endpoint.
2. Convert the JSON response to a pandas DataFrame.
3. Validate required columns.
4. Transform or aggregate the data.
5. Visualize the results in Streamlit or return a table.

---

# Fetch Data Pattern

Use this pattern when loading a dataset from the API.

```python
import requests
import pandas as pd

BASE_URL = "https://lehman-api.localdev.me"

response = requests.get(
    f"{BASE_URL}/data/batting",
    params={"limit": 10000},
    verify=False,
)
response.raise_for_status()

payload = response.json()
rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
df = pd.DataFrame(rows)
```

---

# Column Validation Pattern

Always validate required columns before performing transformations.

```python
required_cols = ["playerID", "HR", "nameFirst", "nameLast"]
missing = [col for col in required_cols if col not in df.columns]

if missing:
    raise Exception(f"Missing required columns: {missing}")
```

---

# Derived Field Pattern

Create derived fields after the schema has been validated.

Example: build a display name from first and last name.

```python
df["name"] = (
    df["nameFirst"].fillna("").astype(str)
    + " "
    + df["nameLast"].fillna("").astype(str)
).str.strip()
```

---

# Aggregation Pattern

Example: Top career home runs.

```python
top_homers = (
    df.groupby(["playerID", "name"], dropna=False)["HR"]
    .sum()
    .reset_index()
    .sort_values("HR", ascending=False)
    .head(10)
)
```

Use this only when you need a custom aggregation that the API does not already provide.

---

# Batting Leaderboard Endpoint Pattern

Use the dedicated batting leaderboard endpoint when you need career leaders for one supported batting stat.

```python
response = requests.get(
    f"{BASE_URL}/data/batting/top",
    params={"stat": "HR", "limit": 20, "include_details": True},
    verify=False,
)
response.raise_for_status()

payload = response.json()
rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
leaders = pd.DataFrame(rows)

aggregation = payload.get("aggregation") if isinstance(payload, dict) else None
selected_stat = payload.get("stat") if isinstance(payload, dict) else "HR"
include_details = payload.get("include_details") if isinstance(payload, dict) else False
```

Notes:
- Supported `stat` values are `H`, `2B`, `3B`, `HR`, `SB`, and `RBI`.
- `limit` defaults to 50 and must be between 1 and 500.
- `include_details=True` adds `career_games`, `career_hits`, `career_at_bats`, and `batting_average`.
- `batting_average` is derived from `career_hits / career_at_bats` and rounded to 3 decimals.
- The wrapped payload includes metadata such as `aggregation="career_total_by_player"`.

---

# Time Series Pattern

Example: home runs by year.

```python
hr_by_year = (
    df.groupby("yearID")["HR"]
    .sum()
    .reset_index()
)
```

---

# People Search Pattern

Use the people endpoint for player lookup and metadata retrieval.

```python
response = requests.get(
    f"{BASE_URL}/data/people",
    params={"nameLast": "Ortiz"},
    verify=False,
)
response.raise_for_status()

payload = response.json()
rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
people = pd.DataFrame(rows)
```

---

# Join Pattern

Join batting data with people data using `playerID`.

```python
batting_response = requests.get(
    f"{BASE_URL}/data/batting",
    params={"limit": 10000},
    verify=False,
)
batting_response.raise_for_status()
batting_payload = batting_response.json()
batting_rows = batting_payload["data"] if isinstance(batting_payload, dict) and "data" in batting_payload else batting_payload
batting = pd.DataFrame(batting_rows)

people_response = requests.get(
    f"{BASE_URL}/data/people",
    params={"limit": 10000},
    verify=False,
)
people_response.raise_for_status()
people_payload = people_response.json()
people_rows = people_payload["data"] if isinstance(people_payload, dict) and "data" in people_payload else people_payload
people = pd.DataFrame(people_rows)

merged = batting.merge(people, on="playerID", how="left")
merged["name"] = (
    merged["nameFirst"].fillna("").astype(str)
    + " "
    + merged["nameLast"].fillna("").astype(str)
).str.strip()
```

---

# Streamlit Table Pattern

Use Streamlit dataframes for tabular output.

```python
import streamlit as st

st.subheader("Top 10 Career Home Runs")
st.dataframe(top_homers, width="stretch")
```

---

# Streamlit Chart Pattern

Use Streamlit charts for quick visualizations.

```python
st.bar_chart(top_homers.set_index("name")["HR"])
st.line_chart(hr_by_year.set_index("yearID")["HR"])
```

---

# Batting Leaderboard Display Pattern

Normalize the leaderboard output before displaying it.

```python
if "stat_total" in leaders.columns:
    leaders = leaders.rename(columns={"stat_total": selected_stat})

preferred_columns = [
    "playerID",
    "nameFirst",
    "nameLast",
    "debut",
    "finalGame",
    selected_stat,
]

detail_columns = [column for column in leaders.columns if column not in preferred_columns]
display_columns = [column for column in preferred_columns if column in leaders.columns] + detail_columns

st.dataframe(leaders[display_columns], width="stretch")
```

If you want a stable detail-first layout when `include_details=True`, use:

```python
detail_columns = [
    "career_games",
    "career_hits",
    "career_at_bats",
    "batting_average",
]

display_columns = [column for column in preferred_columns if column in leaders.columns]
display_columns += [column for column in detail_columns if column in leaders.columns]

st.dataframe(leaders[display_columns], width="stretch")
```

---

# Important Usage Rules

- Always check the API response before processing data.
- Prefer reading records from `response.json()["data"]` when the endpoint returns a wrapped payload.
- Validate required columns before aggregating.
- Do not assume all datasets share the same schema.
- Use `playerID` as the primary join key.
- Prefer API-side aggregation when a dedicated endpoint such as `/data/batting/top` already exists.
- Treat optional leaderboard detail fields as additive and validate them before use.

---

# Design Principles

- API = data retrieval layer
- pandas = transformation layer
- Streamlit = presentation layer

Keep these concerns separated for clarity and maintainability.

---

# Task Template

When solving an analytics task:

1. Identify the dataset or datasets.
2. Fetch the required data via API.
3. Load the response into a DataFrame.
4. Validate the schema.
5. Create derived fields if needed.
6. Aggregate with pandas.
7. Visualize or output the result.