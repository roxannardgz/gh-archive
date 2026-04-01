import os
from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd
import streamlit as st
from datetime import timedelta


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


def date_filter_stg(source: DataSource) -> str:
    if source == "Local":
        return f"created_at >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS - 1} days'"
    return f"DATE(created_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL {LOOKBACK_DAYS - 1} DAY)"


def date_filter_event_date(source: DataSource) -> str:
    if source == "Local":
        return f"event_date >= CURRENT_DATE - INTERVAL '{LOOKBACK_DAYS - 1} days'"
    return f"event_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {LOOKBACK_DAYS - 1} DAY)"


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


def get_active_repo_count(backend: DataBackend) -> int:
    t = backend.tables["stg_selected_events"]
    sql = f"""
    SELECT COUNT(DISTINCT repo_name) AS active_repos
    FROM {t}
    WHERE {date_filter_stg(backend.source)}
    """
    return int(backend.run_query(sql).iloc[0]["active_repos"])


def get_kpis(backend: DataBackend, repo: Optional[str]) -> dict:
    t = backend.tables["stg_selected_events"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        COUNT(*) AS total_events,
        COUNT(DISTINCT actor_login) AS total_contributors,
        COUNT(*) * 1.0 / NULLIF(COUNT(DISTINCT DATE(created_at)), 0) AS avg_events_per_day
    FROM {t}
    WHERE {date_filter_stg(backend.source)}
    {repo_clause}
    """
    row = backend.run_query(sql).iloc[0]
    return {
        "total_events": int(row["total_events"] or 0),
        "total_contributors": int(row["total_contributors"] or 0),
        "avg_events_per_day": float(row["avg_events_per_day"] or 0),
    }


def get_activity_over_time(backend: DataBackend, repo: Optional[str]) -> pd.DataFrame:
    t = backend.tables["mart_repo_daily_activity"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        event_date,
        total_events,
        unique_actors
    FROM {t}
    WHERE {date_filter_event_date(backend.source)}
    {repo_clause}
    ORDER BY event_date
    """
    return backend.run_query(sql)


def get_event_type_distribution(backend: DataBackend, repo: Optional[str]) -> pd.DataFrame:
    t = backend.tables["mart_repo_daily_event_type_activity"]
    repo_clause = repo_filter_clause(repo)
    sql = f"""
    SELECT
        event_type,
        SUM(total_events) AS total_events
    FROM {t}
    WHERE {date_filter_event_date(backend.source)}
    {repo_clause}
    GROUP BY event_type
    ORDER BY total_events DESC
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
            active_repos = get_active_repo_count(backend)
            st.caption(f"Active repos: {active_repos}")
        except Exception:
            pass

st.divider()


repo_filter = None if selected_repo == "All repos" else selected_repo

try:
    kpis = get_kpis(backend, repo_filter)
    activity_df = get_activity_over_time(backend, repo_filter)
    event_types_df = get_event_type_distribution(backend, repo_filter)
except Exception as e:
    st.error(f"Could not load dashboard data: {e}")
    st.stop()

# KPI row
k1, k2, k3 = st.columns(3)
k1.metric("Total events", f"{kpis['total_events']:,}")
k2.metric("Total contributors", f"{kpis['total_contributors']:,}")
k3.metric("Avg events per day", f"{kpis['avg_events_per_day']:.1f}")


# Activity over time
st.subheader("Activity over time")

activity_metric = st.radio(
    "Activity metric",
    ["Total events", "Unique actors"],
    horizontal=True
)

if activity_df.empty:
    st.info("No activity data available for the selected view.")
else:
    chart_col = "total_events" if activity_metric == "Total events" else "unique_actors"
    chart_df = activity_df.set_index("event_date")[[chart_col]]
    st.bar_chart(chart_df)

# Event type distribution
st.subheader("Event type distribution")
if event_types_df.empty:
    st.info("No event type data available for the selected view.")
else:
    event_types_df = event_types_df.sort_values("total_events", ascending=True).set_index("event_type")
    st.bar_chart(event_types_df)

# Bottom section switches by scope
if selected_repo == "All repos":
    st.subheader("Top repos")
    try:
        top_repos_df = get_top_repos(backend)
        if top_repos_df.empty:
            st.info("No repo summary data available.")
        else:
            st.bar_chart(top_repos_df.set_index("repo_name")[["total_events"]])
    except Exception as e:
        st.error(f"Could not load top repos: {e}")
else:
    st.subheader("Top contributors")
    try:
        contributors_df = get_top_contributors(backend, selected_repo)
        if contributors_df.empty:
            st.info("No contributor data available for this repo.")
        else:
            st.dataframe(contributors_df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load top contributors: {e}")
