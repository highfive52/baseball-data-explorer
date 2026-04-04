import os

import streamlit as st
import requests
import pandas as pd
import altair as alt
from streamlit.errors import StreamlitSecretNotFoundError

DEFAULT_BASE_URL = "http://localhost:8000"


def get_setting(name, default):
    try:
        if name in st.secrets:
            return st.secrets[name]
    except StreamlitSecretNotFoundError:
        pass
    return os.getenv(name, default)


def get_bool_setting(name, default):
    value = get_setting(name, default)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


BASE_URL = str(get_setting("BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
VERIFY_SSL = get_bool_setting("VERIFY_SSL", True)
LEADERBOARD_STATS = ["H", "2B", "3B", "HR", "SB", "RBI"]


def extract_years_from_meta(meta_payload):
    years = set()

    def add_year(value):
        try:
            year_int = int(value)
            if 1800 <= year_int <= 2100:
                years.add(year_int)
        except (TypeError, ValueError):
            return

    def handle_year_collection(candidate):
        if isinstance(candidate, list):
            for item in candidate:
                add_year(item)

    if isinstance(meta_payload, dict):
        # Most likely field names for available seasons.
        for key in [
            "years",
            "available_years",
            "availableYears",
            "yearIDs",
            "year_ids",
        ]:
            handle_year_collection(meta_payload.get(key))

        # Common pattern: list of records under data/partitions.
        for key in ["data", "partitions", "partitions_info"]:
            records = meta_payload.get(key)
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        for year_key in ["yearID", "year", "season", "value"]:
                            if year_key in record:
                                add_year(record.get(year_key))

        # Last-resort scan: any dict key containing 'year'.
        if not years:
            for key, value in meta_payload.items():
                if "year" in str(key).lower():
                    if isinstance(value, list):
                        handle_year_collection(value)
                    else:
                        add_year(value)

    elif isinstance(meta_payload, list):
        # Fallback if endpoint returns a plain list of years/records.
        for item in meta_payload:
            if isinstance(item, dict):
                for year_key in ["yearID", "year", "season", "value"]:
                    if year_key in item:
                        add_year(item.get(year_key))
            else:
                add_year(item)

    return sorted(years)


st.title("Baseball Data Explorer")

tab2, tab3, tab4, tab1 = st.tabs(
    [
        "People Search",
        "Top 10 Career Stats List Builder",
        "Top 20 Batting Leaders",
        "API Data Inspection",
    ]
)

# ===== TAB 1: API Data Inspection =====
with tab1:
    try:
        response = requests.get(f"{BASE_URL}/data/batting", verify=VERIFY_SSL)
        if not VERIFY_SSL:
            st.warning("SSL verification is disabled for local development.")
        response.raise_for_status()

        # Validate and inspect raw payload
        st.subheader("API response checks")
        st.write("Status code:", response.status_code)
        st.write("Content-Type:", response.headers.get("Content-Type"))

        data = response.json()
        st.write("Raw JSON type:", type(data))

        if isinstance(data, list):
            st.write("Records returned:", len(data))
            st.write("First 5 raw records:")
            st.json(data[:5])
            df = pd.DataFrame(data)
        elif isinstance(data, dict):
            # If wrapped in {"data": [...]} or similar
            if "data" in data and isinstance(data["data"], list):
                st.write("Records returned:", len(data["data"]))
                st.write("First 5 raw records:")
                st.json(data["data"][:5])
                df = pd.DataFrame(data["data"])
            else:
                st.error(
                    "JSON returned as dict but could not interpret it as a table of rows."
                )
                st.write(data)
                st.stop()
        else:
            st.error(
                "Unsupported JSON structure; expected list of records or dict with data list."
            )
            st.write(data)
            st.stop()

        if df.empty:
            st.warning("DataFrame is empty after conversion; nothing to display")
            st.stop()

        st.subheader("DataFrame preview")
        st.dataframe(df.head())

    except Exception as e:
        st.error(f"Error fetching or processing data: {e}")

# ===== TAB 2: People Search =====
with tab2:
    st.subheader("Search People by Name")

    with st.form("people_search_form"):
        col1, col2 = st.columns(2)
        with col1:
            name_first = st.text_input(
                "First Name", placeholder="e.g., David (optional)"
            )
        with col2:
            name_last = st.text_input("Last Name", placeholder="e.g., Ortiz (optional)")

        submitted = st.form_submit_button("Search")

    if submitted:
        if name_first or name_last:
            try:
                # Build query params from provided inputs
                query_params = {}
                if name_first:
                    query_params["nameFirst"] = name_first
                if name_last:
                    query_params["nameLast"] = name_last

                response = requests.get(
                    f"{BASE_URL}/data/people",
                    params=query_params,
                    verify=VERIFY_SSL,
                )
                response.raise_for_status()

                data = response.json()

                # Handle both list and dict responses
                if isinstance(data, list):
                    results_data = data
                elif isinstance(data, dict) and "data" in data:
                    results_data = data["data"]
                else:
                    results_data = [data] if data else []

                if results_data:
                    df_results = pd.DataFrame(results_data)
                    st.success(f"Found {len(df_results)} result(s)")

                    # Display only selected columns
                    columns_to_display = [
                        "playerID",
                        "nameFirst",
                        "nameLast",
                        "birthYear",
                        "birthCountry",
                        "bats",
                        "throws",
                        "debut",
                        "finalGame",
                    ]
                    available_columns = [
                        col for col in columns_to_display if col in df_results.columns
                    ]
                    st.dataframe(df_results[available_columns])

                    st.subheader("View Player Details")
                    for result in results_data:
                        player_id = result.get("playerID", "Unknown")
                        result_name_first = result.get("nameFirst", "")
                        result_name_last = result.get("nameLast", "")
                        player_name = f"{result_name_first} {result_name_last}".strip()

                        with st.expander(f"📋 {player_name} ({player_id})"):
                            # Pivot the data: column names in first column, values in second
                            df_pivoted = pd.DataFrame(
                                list(result.items()), columns=["Attribute", "Value"]
                            )
                            # Normalize mixed types so Arrow serialization is stable.
                            df_pivoted["Value"] = df_pivoted["Value"].astype(str)
                            st.dataframe(df_pivoted, width="stretch")
                else:
                    st.info("No results found for the given search criteria.")
            except Exception as e:
                st.error(f"Error querying people API: {e}")
        else:
            st.warning(
                "Please enter at least one search criterion (first name or last name)."
            )

# ===== TAB 3: Top 10 Career Stats =====
with tab3:
    st.subheader("Top 10 Career Stats Builder")

    if st.button("Build Top 10 Career Stats"):
        try:
            meta_response = requests.get(
                f"{BASE_URL}/data/batting/meta", verify=VERIFY_SSL
            )
            meta_response.raise_for_status()
            meta_payload = meta_response.json()

            years = extract_years_from_meta(meta_payload)
            if not years:
                st.error(
                    "Could not determine available batting years from /data/batting/meta."
                )
                st.stop()

            st.write(f"Years discovered: {len(years)}")
            st.write(f"Range: {years[0]} to {years[-1]}")

            yearly_frames = []
            columns_to_keep = ["playerID", "H", "HR", "nameFirst", "nameLast"]
            status_placeholder = st.empty()
            progress_bar = st.progress(0)
            for index, year in enumerate(years, start=1):
                status_placeholder.write(
                    f"Fetching batting data for year: {year} ({index}/{len(years)})"
                )
                year_response = requests.get(
                    f"{BASE_URL}/data/batting",
                    params={"yearID": year},
                    verify=VERIFY_SSL,
                )
                year_response.raise_for_status()
                year_payload = year_response.json()

                if isinstance(year_payload, list):
                    year_rows = year_payload
                elif (
                    isinstance(year_payload, dict)
                    and "data" in year_payload
                    and isinstance(year_payload["data"], list)
                ):
                    year_rows = year_payload["data"]
                else:
                    year_rows = []

                if year_rows:
                    filtered_rows = []
                    for row in year_rows:
                        if isinstance(row, dict):
                            filtered_rows.append(
                                {column: row.get(column) for column in columns_to_keep}
                            )

                    if filtered_rows:
                        yearly_frames.append(pd.DataFrame(filtered_rows))

                progress_bar.progress(index / len(years))

            status_placeholder.success(
                f"Finished fetching batting data for {len(years)} years."
            )

            if not yearly_frames:
                st.warning("No batting records were returned for the discovered years.")
                st.stop()

            all_batting = pd.concat(yearly_frames, ignore_index=True)
            required_columns = {"playerID", "H"}
            missing_columns = required_columns - set(all_batting.columns)
            if missing_columns:
                st.error(
                    f"Required columns missing from batting data: {', '.join(sorted(missing_columns))}"
                )
                st.stop()

            if "nameFirst" in all_batting.columns and "nameLast" in all_batting.columns:
                all_batting["displayName"] = (
                    all_batting["nameFirst"].fillna("").astype(str)
                    + " "
                    + all_batting["nameLast"].fillna("").astype(str)
                ).str.strip()
                name_column = "displayName"
            else:
                all_batting["displayName"] = all_batting["playerID"].astype(str)
                name_column = "displayName"

            top_hitters = (
                all_batting.groupby(["playerID", name_column], dropna=False)
                .agg(
                    Hits=("H", "sum"),
                )
                .reset_index()
                .rename(columns={name_column: "playerName"})
                .sort_values("Hits", ascending=False)
                .head(10)
            )

            st.subheader("Top 10 Career Hits")
            st.dataframe(top_hitters, width="stretch")

            top_homers = (
                all_batting.groupby(["playerID", name_column], dropna=False)
                .agg(
                    HomeRuns=("HR", "sum"),
                )
                .reset_index()
                .rename(columns={name_column: "playerName"})
                .sort_values("HomeRuns", ascending=False)
                .head(10)
            )

            st.subheader("Top 10 Career Home Runs")
            st.dataframe(top_homers, width="stretch")
        except Exception as e:
            st.error(f"Error building top 10 career hits: {e}")

# ===== TAB 4: Top 20 Batting Leaders =====
with tab4:
    st.subheader("Top 20 Batting Leaders")

    selected_stat = st.selectbox(
        "Choose a batting stat",
        options=LEADERBOARD_STATS,
        index=0,
        key="batting_top_stat",
    )

    try:
        leaderboard_response = requests.get(
            f"{BASE_URL}/data/batting/top",
            params={"stat": selected_stat, "limit": 20, "include_details": True},
            verify=VERIFY_SSL,
        )
        leaderboard_response.raise_for_status()
        leaderboard_payload = leaderboard_response.json()

        if isinstance(leaderboard_payload, list):
            leaderboard_rows = leaderboard_payload
        elif isinstance(leaderboard_payload, dict) and "data" in leaderboard_payload:
            leaderboard_rows = leaderboard_payload["data"]
        else:
            leaderboard_rows = []

        if leaderboard_rows:
            leaderboard_df = pd.DataFrame(leaderboard_rows)

            if "stat_total" in leaderboard_df.columns:
                leaderboard_df = leaderboard_df.rename(
                    columns={"stat_total": selected_stat}
                )

            preferred_columns = [
                "playerID",
                "nameFirst",
                "nameLast",
                "debut",
                "finalGame",
                selected_stat,
            ]
            available_columns = [
                column
                for column in preferred_columns
                if column in leaderboard_df.columns
            ]

            st.dataframe(leaderboard_df[available_columns], width="stretch")

            if (
                "playerID" in leaderboard_df.columns
                and selected_stat in leaderboard_df.columns
            ):
                chart_df = leaderboard_df[["playerID", selected_stat]].copy()
                chart_df[selected_stat] = pd.to_numeric(
                    chart_df[selected_stat], errors="coerce"
                )
                chart_df = chart_df.dropna(subset=[selected_stat]).sort_values(
                    selected_stat, ascending=False
                )

                if not chart_df.empty:
                    st.subheader(f"Top 20 {selected_stat} Leaders")
                    chart = (
                        alt.Chart(chart_df)
                        .mark_bar()
                        .encode(
                            x=alt.X(
                                "playerID:N",
                                sort=alt.EncodingSortField(
                                    field=selected_stat, order="descending"
                                ),
                                title="playerID",
                            ),
                            y=alt.Y(f"{selected_stat}:Q", title=selected_stat),
                            tooltip=[
                                "playerID",
                                alt.Tooltip(f"{selected_stat}:Q", title=selected_stat),
                            ],
                        )
                        .properties(height=500)
                    )
                    st.altair_chart(chart, use_container_width=True)

            bubble_chart_columns = [
                "playerID",
                "nameFirst",
                "nameLast",
                selected_stat,
                "career_games",
                "batting_average",
            ]

            if all(column in leaderboard_df.columns for column in bubble_chart_columns):
                bubble_df = leaderboard_df[bubble_chart_columns].copy()
                for column in [selected_stat, "career_games", "batting_average"]:
                    bubble_df[column] = pd.to_numeric(
                        bubble_df[column], errors="coerce"
                    )

                bubble_df = bubble_df.dropna(
                    subset=[selected_stat, "career_games", "batting_average"]
                )

                if not bubble_df.empty:
                    min_games = bubble_df["career_games"].min()
                    max_games = bubble_df["career_games"].max()
                    if min_games == max_games:
                        size_scale = alt.Scale(range=[500, 500])
                    else:
                        size_scale = alt.Scale(
                            domain=[min_games, max_games], range=[80, 1600]
                        )

                    st.subheader(f"{selected_stat} vs Batting Average")
                    bubble_chart = (
                        alt.Chart(bubble_df)
                        .mark_circle(opacity=0.7)
                        .encode(
                            x=alt.X(
                                "batting_average:Q",
                                title="Batting Average",
                                axis=alt.Axis(format=".3f"),
                                scale=alt.Scale(zero=False),
                            ),
                            y=alt.Y(f"{selected_stat}:Q", title=selected_stat),
                            size=alt.Size(
                                "career_games:Q",
                                title="Career Games",
                                scale=size_scale,
                                legend=alt.Legend(orient="right"),
                            ),
                            tooltip=[
                                alt.Tooltip("playerID:N", title="playerID"),
                                alt.Tooltip("nameFirst:N", title="First Name"),
                                alt.Tooltip("nameLast:N", title="Last Name"),
                                alt.Tooltip(f"{selected_stat}:Q", title=selected_stat),
                                alt.Tooltip(
                                    "batting_average:Q",
                                    title="Batting Average",
                                    format=".3f",
                                ),
                                alt.Tooltip("career_games:Q", title="Career Games"),
                            ],
                        )
                        .properties(height=450)
                    )
                    st.altair_chart(bubble_chart, use_container_width=True)
        else:
            st.info("No leaderboard rows were returned for the selected stat.")
    except Exception as e:
        st.error(f"Error loading batting leaderboard for {selected_stat}: {e}")
