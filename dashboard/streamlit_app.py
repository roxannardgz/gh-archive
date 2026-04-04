import os
from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd
import streamlit as st
from datetime import timedelta
import altair as alt

try:
    import duckdb
except Exception:
    duckdb = None

try:
    from google.cloud import bigquery
except Exception:
    bigquery = None


DataSource = Literal["Local", "Cloud"]


# ---------- Config ----------
LOCAL_DUCKDB_PATH = "gharchive.duckdb"
BQ_PROJECT = os.getenv("BQ_PROJECT", "gharchive-491810")
BQ_DATASET = os.getenv("BQ_DATASET", "gharchive_dataset")
LOOKBACK_DAYS = 7
BAR_COLOR = "#4078c0"

LOCAL_TABLES = {
    "stg_events": "stg_events",
    "stg_selected_events": "stg_selected_events",
    "mart_repo_daily_activity": "mart_repo_daily_activity",
    "mart_repo_daily_event_type_activity": "mart_repo_daily_event_type_activity",
    "mart_repo_actor_activity": "mart_repo_actor_activity",
    "mart_repo_summary": "mart_repo_summary",
}

CLOUD_TABLES = {
    "stg_events": f"`{BQ_PROJECT}.{BQ_DATASET}.stg_events`",
    "stg_selected_events": f"`{BQ_PROJECT}.{BQ_DATASET}.stg_selected_events`",
    "mart_repo_daily_activity": f"`{BQ_PROJECT}.{BQ_DATASET}.mart_repo_daily_activity`",
    "mart_repo_daily_event_type_activity": f"`{BQ_PROJECT}.{BQ_DATASET}.mart_repo_daily_event_type_activity`",
    "mart_repo_actor_activity": f"`{BQ_PROJECT}.{BQ_DATASET}.mart_repo_actor_activity`",
    "mart_repo_summary": f"`{BQ_PROJECT}.{BQ_DATASET}.mart_repo_summary`",
}



if BQ_PROJECT == "gharchive-491810":
    st.warning("Using default BigQuery project. Set BQ_PROJECT env variable for your own setup.")


# ---------- Data access ----------
@dataclass
class DataBackend:
    source: DataSource

    @property
    def tables(self) -> dict:
        return LOCAL_TABLES if self.source == "Local" else CLOUD_TABLES

    def run_query(self, sql: str) -> pd.DataFrame:
        if self.source == "Local":
            if duckdb is None:
                raise RuntimeError("duckdb is not installed in this environment.")
            with duckdb.connect(LOCAL_DUCKDB_PATH, read_only=True) as con:
                return con.execute(sql).df()

        if bigquery is None:
            raise RuntimeError("google-cloud-bigquery is not installed in this environment.")
        client = bigquery.Client(project=BQ_PROJECT)
        return client.query(sql).to_dataframe()


# ---------- SQL helpers ----------
def quote_sql(value: str) -> str:
    return value.replace("'", "''")


def repo_filter_clause(repo: Optional[str]) -> str:
    if not repo or repo == "All repos":
        return ""
    return f" AND repo_name = '{quote_sql(repo)}'"


def sql_date(value) -> str:
    return f"DATE '{pd.to_datetime(value).date()}'"


def created_at_range_clause(start_date, end_date) -> str:
    return (
        f"DATE(created_at) BETWEEN {sql_date(start_date)} "
        f"AND {sql_date(end_date)}"
    )


def event_date_range_clause(start_date, end_date) -> str:
    return (
        f"event_date BETWEEN {sql_date(start_date)} "
        f"AND {sql_date(end_date)}"
    )

def get_top_entities(backend: DataBackend, repo: Optional[str], start_date, end_date) -> pd.DataFrame:
    if not repo:
        t = backend.tables["mart_repo_summary"]
        sql = f"""
        SELECT
            repo_name AS entity_name,
            total_events
        FROM {t}
        ORDER BY total_events DESC, repo_name
        LIMIT 5
        """
        return backend.run_query(sql)

    t = backend.tables["stg_selected_events"]
    sql = f"""
    SELECT
        actor_login AS entity_name,
        COUNT(*) AS total_events
    FROM {t}
    WHERE {created_at_range_clause(start_date, end_date)}
      AND repo_name = '{quote_sql(repo)}'
    GROUP BY actor_login
    ORDER BY total_events DESC, actor_login
    LIMIT 5
    """
    return backend.run_query(sql)


# ---------- Query builders ----------
def get_repo_options(backend: DataBackend) -> list[str]:
    t = backend.tables["mart_repo_summary"]
    sql = f"SELECT repo_name FROM {t} ORDER BY repo_name"
    df = backend.run_query(sql)
    return ["All repos"] + df["repo_name"].tolist()


def get_last_loaded_date(backend: DataBackend) -> Optional[pd.Timestamp]:
    t = backend.tables["stg_events"]
    sql = f"SELECT MAX(DATE(created_at)) AS max_date FROM {t}"
    df = backend.run_query(sql)
    return df.iloc[0]["max_date"] if not df.empty else None


def get_active_repo_count(backend: DataBackend, start_date, end_date) -> int:
    t = backend.tables["stg_selected_events"]
    sql = f"""
    SELECT COUNT(DISTINCT repo_name) AS active_repos
    FROM {t}
    WHERE {created_at_range_clause(start_date, end_date)}
    """
    return int(backend.run_query(sql).iloc[0]["active_repos"])


def get_kpis(backend: DataBackend, repo: Optional[str], start_date, end_date) -> dict:
    t = backend.tables["stg_selected_events"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        COUNT(*) AS total_events,
        COUNT(DISTINCT actor_login) AS total_contributors,
        COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT DATE(created_at)), 0) AS avg_events_per_day
    FROM {t}
    WHERE {created_at_range_clause(start_date, end_date)}
    {repo_clause}
    """
    row = backend.run_query(sql).iloc[0]
    return {
        "total_events": int(row["total_events"] or 0),
        "total_contributors": int(row["total_contributors"] or 0),
        "avg_events_per_day": float(row["avg_events_per_day"] or 0),
    }


def get_activity_over_time(backend: DataBackend, repo: Optional[str], start_date, end_date) -> pd.DataFrame:
    t = backend.tables["stg_selected_events"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        DATE(created_at) AS event_date,
        COUNT(*) AS total_events,
        COUNT(DISTINCT actor_login) AS unique_actors
    FROM {t}
    WHERE {created_at_range_clause(start_date, end_date)}
    {repo_clause}
    GROUP BY DATE(created_at)
    ORDER BY event_date
    """
    return backend.run_query(sql)


def get_event_type_distribution(backend: DataBackend, repo: Optional[str], start_date, end_date) -> pd.DataFrame:
    t = backend.tables["mart_repo_daily_event_type_activity"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        event_type,
        SUM(total_events) AS total_events
    FROM {t}
    WHERE {event_date_range_clause(start_date, end_date)}
    {repo_clause}
    GROUP BY event_type
    ORDER BY total_events DESC, event_type
    """
    return backend.run_query(sql)


def get_top_contributors(backend: DataBackend, repo: str) -> pd.DataFrame:
    t = backend.tables["mart_repo_actor_activity"]
    sql = f"""
    SELECT
        actor_login,
        total_events,
        first_activity,
        last_activity
    FROM {t}
    WHERE repo_name = '{quote_sql(repo)}'
    ORDER BY total_events DESC, actor_login
    LIMIT 5
    """
    return backend.run_query(sql)


def get_top_repos(backend: DataBackend) -> pd.DataFrame:
    t = backend.tables["mart_repo_summary"]
    sql = f"""
    SELECT
        repo_name,
        total_events
    FROM {t}
    ORDER BY total_events DESC, repo_name
    LIMIT 5
    """
    return backend.run_query(sql)


# ---------- UI ----------
st.set_page_config(page_title="GH Archive Activity", layout="wide")
st.title("GH Archive Activity")


with st.sidebar:
    st.header("Controls")
    source: DataSource = st.radio("Data source", ["Local", "Cloud"], index=1)

backend = DataBackend(source=source)

try:
    repo_options = get_repo_options(backend)
except Exception as e:
    st.error(f"Could not load repo options from {source} source: {e}")
    st.stop()

last_loaded = None
try:
    last_loaded = get_last_loaded_date(backend)
except Exception as e:
    st.error(f"Could not load last loaded date: {e}")

start_date = None
end_date = last_loaded

if last_loaded is not None:
    start_date = last_loaded - timedelta(days=LOOKBACK_DAYS - 1)

top_left, top_right = st.columns([2, 1])

with top_left:
    selected_repo = st.selectbox("Repo", repo_options, index=0)

with top_right:
    st.markdown("**Now Showing**")

    if start_date is not None and end_date is not None:
        st.caption(
            f"{start_date.strftime('%b %d')} → {end_date.strftime('%b %d')}"
        )

    if selected_repo == "All repos":
        try:
            active_repos = get_active_repo_count(backend, start_date, end_date)
            st.caption(f"Active repos: {active_repos}")
        except Exception:
            pass

st.divider()


repo_filter = None if selected_repo == "All repos" else selected_repo

try:
    kpis = get_kpis(backend, repo_filter, start_date, end_date)
    activity_df = get_activity_over_time(backend, repo_filter, start_date, end_date)
    event_types_df = get_event_type_distribution(backend, repo_filter, start_date, end_date)
except Exception as e:
    st.error(f"Could not load dashboard data: {e}")
    st.stop()



# KPI row -- -- -- -- -- -- -- --
k1, k2, k3 = st.columns(3)
k1.metric("Total events", f"{kpis['total_events']:,}")
k2.metric("Total contributors", f"{kpis['total_contributors']:,}")
k3.metric("Avg events per day", f"{kpis['avg_events_per_day']:.1f}")


# Activity over time -- -- -- -- -- -- -- --
title_col, toggle_col = st.columns([3, 2])

with title_col:
    st.subheader("Activity over time")

with toggle_col:
    activity_metric = st.radio(
        "Activity metric",
        ["Total events", "Unique contributors"],
        horizontal=True,
        label_visibility="collapsed"
    )

if activity_df.empty:
    st.info("No activity data available for the selected view.")
else:
    chart_col = "total_events" if activity_metric == "Total events" else "unique_actors"

    activity_df = activity_df.copy()
    activity_df["event_date"] = pd.to_datetime(activity_df["event_date"]).dt.date

    if start_date is not None and end_date is not None:
        full_dates = pd.date_range(start=start_date, end=end_date, freq="D").date
    else:
        full_dates = sorted(activity_df["event_date"].unique())

    full_df = pd.DataFrame({"event_date": list(full_dates)})

    chart_df = full_df.merge(
        activity_df[["event_date", chart_col]],
        on="event_date",
        how="left"
    )

    chart_df[chart_col] = chart_df[chart_col].fillna(0).astype(int)
    chart_df["event_date_label"] = pd.to_datetime(chart_df["event_date"]).dt.strftime("%b %d")

    base = alt.Chart(chart_df)

    bars = base.mark_bar(color=BAR_COLOR).encode(
        x=alt.X(
            "event_date_label:N",
            sort=chart_df["event_date_label"].tolist(),
            title=None,
            axis=alt.Axis(labelAngle=0)
        ),
        y=alt.Y(f"{chart_col}:Q", title=activity_metric),
        tooltip=[
            alt.Tooltip("event_date_label:N", title="Date"),
            alt.Tooltip(f"{chart_col}:Q", title=activity_metric)
        ]
    )

    text = base.mark_text(
        dy=-5,
        color=BAR_COLOR,
        fontWeight="bold"
    ).encode(
        x=alt.X(
            "event_date_label:N",
            sort=chart_df["event_date_label"].tolist()
        ),
        y=alt.Y(f"{chart_col}:Q"),
        text=alt.Text(f"{chart_col}:Q", format=",.0f")
    )

    activity_chart = (bars + text).properties(height=300)

    st.altair_chart(activity_chart, use_container_width=True)



# -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
bottom_left, spacer, bottom_right = st.columns([2, 0.2, 1])

# Event type distribution -- -- -- -- -- -- -- --
with bottom_left:
    st.subheader("Event type distribution")

    if event_types_df.empty:
        st.info("No event type data available for the selected view.")
    else:
        event_types_df = event_types_df.sort_values(
            ["total_events", "event_type"],
            ascending=[False, True]
        )

        base = alt.Chart(event_types_df)

        bars = base.mark_bar(color=BAR_COLOR).encode(
            x=alt.X(
                "event_type:N",
                sort=event_types_df["event_type"].tolist(),
                title=None
            ),
            y=alt.Y("total_events:Q", title="Total events"),
            tooltip=[
                alt.Tooltip("event_type:N", title="Event type"),
                alt.Tooltip("total_events:Q", title="Total events", format=",.0f")
            ]
        )

        text = base.mark_text(
            dy=-5,
            color=BAR_COLOR,
            fontWeight="bold"
        ).encode(
            x=alt.X(
                "event_type:N",
                sort=event_types_df["event_type"].tolist()
            ),
            y=alt.Y("total_events:Q"),
            text=alt.Text("total_events:Q", format=",.0f")
        )

        event_type_chart = (bars + text).properties(height=400)

        st.altair_chart(event_type_chart, use_container_width=True)


with spacer:
    st.empty()

# Top 5 - repo or actor depending on scope -- -- -- -- -- -- -- --
with bottom_right:
    if selected_repo == "All repos":
        st.subheader("Top repos")
    else:
        st.subheader("Top contributors")

    try:
        top_entities_df = get_top_entities(backend, repo_filter, start_date, end_date)

        if top_entities_df.empty:
            st.info("No data available for this view.")
        else:
            top_entities_df = top_entities_df.sort_values(
                ["total_events", "entity_name"],
                ascending=[False, True]
            )

            top_entities_df = top_entities_df.copy()

            if selected_repo == "All repos":
                top_entities_df["entity_label"] = top_entities_df["entity_name"].str.split("/", n=1).str[-1]
            else:
                top_entities_df["entity_label"] = top_entities_df["entity_name"]

            base = alt.Chart(top_entities_df)

            bars = base.mark_bar(color=BAR_COLOR).encode(
                x=alt.X("total_events:Q", title="Total events"),
                y=alt.Y("entity_label:N", sort="-x", title=None),
                tooltip=[
                    alt.Tooltip("entity_name:N", title="Full name"),
                    alt.Tooltip("total_events:Q", title="Total events", format=",.0f")
                ]
            )

            text = base.mark_text(
                align="right",
                dx=-5,
                fontWeight="bold"
            ).encode(
                x=alt.X("total_events:Q"),
                y=alt.Y("entity_label:N", sort="-x"),
                text=alt.Text("total_events:Q", format=",.0f")
            )

            top_entities_chart = (bars + text).properties(height=400)

            st.altair_chart(top_entities_chart, use_container_width=True)

    except Exception as e:
        if selected_repo == "All repos":
            st.error(f"Could not load top repos: {e}")
        else:
            st.error(f"Could not load top contributors: {e}")