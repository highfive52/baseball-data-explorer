# Lehman Baseball API - API Guide

This document describes how to interact with the Lehman Baseball Analytics API.

---

# Base URL

https://lehman-api.localdev.me

---

# Health Check

GET /health

Example:

GET https://lehman-api.localdev.me/health

Response:

```json
{"status": "ok"}
```

---

# Dataset Metadata

Returns available years and record counts for a dataset.

GET /data/{dataset}/meta

Supported datasets:
- batting
- pitching
- fielding
- appearances

Example:

GET https://lehman-api.localdev.me/data/batting/meta

Response:

```json
{
  "dataset": "batting",
  "available_years": [1871, 1872, 1873],
  "year_counts": {
    "1871": 115,
    "1872": 157,
    "1873": 125
  }
}
```

---

# Batting Data

GET /data/batting

Query Parameters:
- yearID (optional)
- limit (optional)

Example:

GET https://lehman-api.localdev.me/data/batting?yearID=2020

---

# Batting Data Top by Stat Category

GET /data/batting/top

Query Parameters:
- stat (required)
- limit (optional, default 50, min 1, max 500)
- include_details (optional, default false)

Available stat values:
- H
- 2B
- 3B
- HR
- SB
- RBI

Example:

GET https://lehman-api.localdev.me/data/batting/top?stat=H&limit=25&include_details=true

Response shape:

```json
{
  "dataset": "batting",
  "aggregation": "career_total_by_player",
  "stat": "H",
  "include_details": true,
  "row_count": 25,
  "limit": 25,
  "data": []
}
```

Notes:
- Results are career totals grouped by player.
- Each record includes `playerID`, `nameFirst`, `nameLast`, `debut`, `finalGame`, and `stat_total`.
- When `include_details=true`, each record also includes `career_games`, `career_hits`, `career_at_bats`, and `batting_average`.
- `debut` is the player's earliest debut date and `finalGame` is the latest final-game date observed in batting records.
- `batting_average` is computed as `career_hits / career_at_bats`, rounded to 3 decimals, and is `null` when career at-bats are 0.
- Invalid `stat` values return HTTP 400 with `detail="Invalid stat. Use one of: H, 2B, 3B, HR, SB, RBI"`.

---

# Pitching Data

GET /data/pitching

Query Parameters:
- yearID (optional)
- limit (optional)

Example:

GET https://lehman-api.localdev.me/data/pitching

---

# Fielding Data

GET /data/fielding

Query Parameters:
- yearID (optional)
- limit (optional)

Example:

GET https://lehman-api.localdev.me/data/fielding?yearID=2020

---

# Appearances Data

GET /data/appearances

Query Parameters:
- yearID (optional)
- limit (optional)

Example:

GET https://lehman-api.localdev.me/data/appearances

---

# People Data

GET /data/people

Query Parameters:
- playerID (optional)
- nameFirst (optional)
- nameLast (optional)
- nameGiven (optional)
- limit (optional)

Examples:

GET https://lehman-api.localdev.me/data/people

GET https://lehman-api.localdev.me/data/people?nameFirst=David&nameLast=Ortiz

GET https://lehman-api.localdev.me/data/people?playerID=ortizda01

---

# Response Format

Dataset endpoints return a JSON object in this general shape:

```json
{
  "dataset": "<dataset_name>",
  "row_count": 123,
  "limit": 1000,
  "data": []
}
```

Notes:
- data is a list of records
- each record is a flat JSON object
- column names are case-sensitive
- not all datasets include the same fields
- some endpoints also include metadata such as `aggregation`, `stat`, or `include_details`

---

# API Usage Rules

- Always check the response status before using the payload.
- Prefer reading records from response.json()["data"] when the endpoint returns a wrapped payload.
- Do not assume all fields exist in every dataset.
- Use query parameters such as yearID, playerID, nameFirst, and nameLast to filter results.
- Specify limit when large result sets are needed.
- For `/data/batting/top`, always send a valid `stat` and treat `include_details` as an opt-in enrichment flag.

Example:

```python
response = requests.get(f"{BASE_URL}/data/batting", params={"yearID": 2020}, verify=False)
response.raise_for_status()
payload = response.json()
rows = payload["data"] if isinstance(payload, dict) and "data" in payload else payload
```

---

# Error Handling

If a request fails:
- the API returns a non-200 status code
- the response may include a JSON body such as:

```json
{
  "detail": "Error message"
}
```

Example handling:

```python
if response.status_code != 200:
    raise Exception(f"API error: {response.text}")
```

---

# Networking Notes

- API is exposed via Kubernetes Ingress.
- Local domain: https://lehman-api.localdev.me
- Ensure your hosts file includes:

```text
127.0.0.1 lehman-api.localdev.me
```

---

# Design Intent

- API is optimized for analytical queries.
- Data is backed by parquet files queried via DuckDB.
- API is not intended for transactional workloads.
- Aggregations are often performed client-side with pandas.