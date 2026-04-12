# GH Archive Analytics Pipeline
[Data Engineering Zoomcamp](https://datatalks.club/blog/data-engineering-zoomcamp.html) 2026 by *Data Talks Club* \
Final project

> [!TIP]
> **Are you a peer reviewer?** See this [review guide](/peer-reviewers.md) for a structured overview of the project based on the evaluation criteria.


## Table of Contents
- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Architecture and Modeling Approach](#architecture-and-modeling-approach)
    - [Local Pipeline](#-local-pipeline)
    - [Cloud Pipeline](#-cloud-pipeline)
    - [Checks and Validation](#checks-and-validation)
- [Dashboard](#dashboard)
- [Key Design Decision](#key-design-decision)
- [How to Reproduce](#how-to-reproduce)
- [Selected Repos](#selected-repos)


## Overview
The [GH Archive dataset](https://www.gharchive.org/) provides large-scale GitHub event data that is difficult to analyze due to its volume, nested structure, and lack of pre-aggregated metrics.

The challenge is to design a data pipeline that can efficiently process this data while supporting both local development and cloud execution.

This project implements an end-to-end data pipeline that transforms raw GitHub events into analytics-ready tables and delivers insights through an interactive Streamlit dashboard.

The project includes two pipelines based on storage backend:

- **Local pipeline** (`gharchive-local`) | DuckDB → 🟡
    - Use case: fast iteration, debugging transformations, dashboard development.
- **Cloud pipeline** (`gharchive-cloud`) | GCS + BigQuery → 🔵
    - Use case: scheduled execution, production-like setup.


> [!NOTE]
> The cloud pipeline supports both local execution (for development and testing) and cloud execution (for scheduled runs). The project is designed to be reproducible across both environments while supporting the same analytical use case.


\
This project demonstrates:
- End-to-end batch pipeline design
- Local and cloud reproducibility
- Data lake + warehouse architecture
- SQL-based transformations
- Idempotent ingestion patterns
- Data quality checks
- Local and cloud orchestration
- Dashboarding on top of analytics marts

## Tech Stack
- Orchestration: **Bruin**
- Local Warehouse: **DuckDB**
- Cloud Warehouse: **BigQuery**
- Data Lake: **Google Cloud Storage (GCS)**
- Transformation: **SQL**
- Language: **Python**
- Visualization: **Streamlit**
- Infrastructure: **Terraform**


## Architecture and Modeling Approach
Although similar, each execution mode has their own architecture. Both models filter to a [set of data engineering / analytics repositories](#selected-repos).

![General Architecture](images/gharchive-general-architecture.drawio.png)


### 🟡 Local Pipeline

#### Ingestion
- Python asset orchestrated with Bruin
- Downloads hourly GH Archive `.json.gz` files directly from GH Archive
- Maintains a rolling 7-day local window
- Handles:
  - retries
  - partial downloads
  - skipping existing files
  - cleanup of old files outside the rolling window

#### Data Storage
- Raw files stored in `data/raw/`
- Local DuckDB database


#### Data Model
- Raw Layer
    - Direct ingestion of JSON data
    - Handles schema drift using `union_by_name`[^1] and a full schema scan with `sample_size = -1`[^2]
- Staging Layer
  - Flattens nested JSON fields
  - Renames columns
  - Deduplicates events
  - Produces a cleaner event-level table
- Mart layer
  - Builds aggregated tables by repo, event type, and actor

> [!NOTE]
> The local pipeline intentionally keeps a fixed 7-day rolling window instead of storing the full history locally. This keeps local development faster, lighter, and aligned with the dashboard use case.

<br>

### 🔵 Cloud Pipeline

#### Ingestion
- Python asset orchestrated with Bruin
- Reads from BigQuery public dataset: `githubarchive.day.*`
- Exports that day to GCS in Parquet Format
- Keep all the data in GCS
- Supports safe reruns by overwriting the exported day if needed

#### Data Storage
- Raw data stored in GCS
- Analytical tables stored in BigQuery

#### Data Model
- Raw Layer
  - BigQuery external table reads Parquet files from GCS
  - Data is loaded into partitioned BigQuery tables
  - Daily loads are idempotent through delete + reload of the target day
- Staging Layer
    - Flattens fields
    - Renames columns
    - Deduplicates events
- Mart Layer
  - Builds aggregated tables by repo, event type, and actor


### Checks and Validation
The project uses custom SQL checks across layers[^3]:

- **Raw**: basic integrity checks
- **Staging**: structural and transformation checks
- **Marts**: aggregation and business logic validation

> [!IMPORTANT]
> Some checks, such as enforcing `repo_name IS NOT NULL` in staging, were intentionally not used because the source data can legitimately contain nulls. Built-in checks are only used in local mode.

<br>

## Dashboard 
The Streamlit dashboard supports both data sources. It includes:

- KPI cards
- Daily activity over time
- Event type distribution
- Top repos / top contributors
- Repo filter (`All repos` or a specific repo)

![Streamlit Dashboard](/images/streamlit-dashboard.png)

The dashboard reads from marts rather than raw tables to keep the UI logic simpler and the queries lighter.

<br>

## Key Design Decision
### ▫️Two independent pipelines instead of one heavily parameterized pipeline
Instead of a single parameterized pipeline, there are 2 independent pipelines (`gharcihve-local`, `gharchive-cloud`). This avoids excessive conditional logic, keeps dependencies simpler, and makes each setup easier to reason about and debug.

### ▫️Same cloud pipeline, different execution environments
The cloud pipeline can run:

- locally, for development and testing
- in the cloud, for scheduled execution

This keeps the cloud logic consistent across environments and reduces the risk of “dev vs prod” drift.

### ▫️Daily ingestion based on the previous UTC day
The pipeline processes one complete UTC day at a time, using the previous day as the data target.

This avoids:

- partial-day loads
- time-of-run inconsistencies
- different results depending on whether the pipeline was triggered locally or in the cloud

It also makes daily reruns and backfills safer.

### ▫️Idempotent daily loading
The project favors rerunnable daily loads:

- **Local**
  - maintains a rolling 7-day local window
  - old local files outside the window are removed
- **Cloud**
  - overwrites exported GCS files for the target day
  - deletes and reloads the target partition in BigQuery

This makes reruns and backfills simpler and more predictable.

### ▫️Terraform for reproducible cloud infrastructure

Terraform is used to provision the main cloud resources required by the project, including:

- the GCS bucket used as the lake layer
- the BigQuery dataset used as the warehouse layer

This keeps the infrastructure reproducible and reduces manual setup.

### ▫️Mart loading strategy

| Table | Strategy | Reason |
| --- | --- | --- |
| `mart_repo_daily_activity` | Incremental (daily partition reload / merge) | Time-series aggregate by day; efficient to update one target day at a time |
| `mart_repo_daily_event_type_activity` | Incremental (daily partition reload / merge) | Same pattern as daily activity; naturally aligned with daily ingestion |
| `mart_repo_actor_activity` | Full rebuild | Depends on activity across the full available history/window; simpler and safer to recompute |
| `mart_repo_summary` | Full rebuild | Small summary table; full rebuild keeps logic simple and correctness easy to verify |


### ▫️Unified Streamlit app
A single Streamlit application supports both DuckDB (local) and BigQuery (cloud) as data sources. This avoids duplicating dashboard logic and ensures consistent metrics and visualizations across environments. It also enables seamless switching between local development and cloud data without modifying the UI layer.

## How to Reproduce
By default, all pipeline runs process the previous UTC day. Check [here](#backfilling-data) for how to backfill a custom date range.

### Requirements
- Git
- Python 3.11+
- `uv`
- Bruin CLI
- Terraform (Cloud mode only)
- Google Cloud SDK (`gcloud`) (Cloud mode only)
- Access to a GCP project with permission to use GCS and BigQuery (Cloud modes only)

### Setup
From the repo root, clone the repository and install dependencies:

```
git clone https://github.com/roxannardgz/gh-archive
cd gh-archive
```

This project uses `uv`.
```
uv venv
source .venv/bin/activate
uv sync
```

Continue with [🟡 Local Mode](#-local-mode), [🔵 Cloud Mode (Local Execution)](#-cloud-mode-local-execution) or [🔵 Cloud Mode (Bruin Cloud)](#-cloud-mode-bruin-cloud).

---
### 🟡 Local Mode

Use this mode when you want the fastest feedback loop for development, debugging, and dashboard work.

> [!IMPORTANT]
> The local pipeline should run without additional cloud configuration. If you changed default paths or connection names in your local Bruin configuration, update them before running.

#### Run pipeline
You can use the helper script:
```
./scripts/run_local.sh
```

Or run the assets directly with Bruin:
```
bruin run pipelines/local/assets/*.py pipelines/local/assets/*.sql
```

What it does
- Downloads hourly GH Archive files into `data/raw/`
- Loads and transforms the data in DuckDB
- Builds staging and mart tables
- Keeps a rolling 7-day local window

#### Validate results
- A `gharchive.duckdb` file should be created/updated
- Staging and mart tables should be available


Continue with the [dashboard](#run-the-dashboard).

────────────

### 🔵 Cloud Mode (Local Execution)

Use this mode when you want to test the cloud pipeline locally before scheduling it.

> [!IMPORTANT]
> Ensure that project-specific values (GCP project ID, dataset, bucket name) match your environment. Defaults are provided but may need to be updated.


#### Requirements
- Python environment set up with uv
- GCP credentials configured
- BigQuery access
- GCS access
- Cloud resources created
    - GCS bucket
    - BigQuery dataset

#### Provision cloud resources
Terraform is used to provision the main cloud resources for the project.

Update `terraform.tfvars` with your GCP project ID and any required resource names.

From the `terraform/` directory, run:
```
terraform init
terraform plan
terraform apply
```
This creates the GCS bucket and BigQuery dataset used by the cloud pipeline.

#### Authenticate with Google Cloud

The local cloud pipeline uses Application Default Credentials:
```
gcloud auth application-default login
gcloud auth application-default set-quota-project <your-gcp-project-id>
```

Review the cloud pipeline configuration and confirm that the project ID, dataset, bucket, and connection names match your environment.

#### Run the cloud pipeline locally
You can use the helper script:
```
./scripts/run_cloud.sh
```

Or run the assets directly with Bruin:
```
bruin run pipelines/cloud/assets/*.py pipelines/cloud/assets/*.sql
```

What it does
- Reads one UTC day from the public GitHub Archive source in BigQuery
- Exports that day to GCS as Parquet
- Loads the raw layer into BigQuery
- Runs staging and mart transformations in BigQuery

#### Validate results
- Confirm that Parquet files were written to the configured GCS bucket
- Confirm that raw, staging, and mart tables were created in BigQuery


Continue with the [dashboard](#run-the-dashboard).

────────────

### 🔵 Cloud Mode (Bruin Cloud)

Use this mode for scheduled execution in the cloud.

> [!IMPORTANT]
> Before running this mode, provision the required cloud resources (GCS bucket and BigQuery dataset) and confirm that the GCP project ID, dataset, bucket name, and Bruin connection name match your environment.

#### Requirements
- Repository pushed to GitHub
- Bruin Cloud project configured
- Google Cloud connection configured in Bruin Cloud
- Required cloud resources provisioned
  - GCS bucket
  - BigQuery dataset

#### Setup flow
1. Provision the cloud resources with Terraform  
   See the [Terraform steps](#provision-cloud-resources) in **Cloud Mode (Local Execution)**
2. Push the repository to GitHub
3. Connect the repository in Bruin Cloud
4. Configure the required Google Cloud connection
5. Authenticate with Google Cloud using Application Default Credentials
    See the [Authentication steps](#authenticate-with-google-cloud) in **Cloud Mode (Local Execution)**.
6. Confirm that the connection name matches the one referenced by the cloud pipeline
7. Trigger a manual run to validate the setup
8. Enable the schedule

#### What it does
- Runs the same cloud pipeline in a scheduled cloud environment
- Processes the previous UTC day
- Exports raw data to GCS
- Loads and transforms data in BigQuery

#### Validate results
- Confirm that the scheduled or manual run succeeds in Bruin Cloud
- Confirm that Parquet files are written to the configured GCS bucket
- Confirm that raw, staging, and mart tables are updated in BigQuery


Continue with the [dashboard](#run-the-dashboard).

---

### Run the dashboard
The dashboard reads from either DuckDB (local) or BigQuery (cloud), depending on the selected source.

```
uv run streamlit run dashboard/streamlit_app.py
```

Then select the correct data source in the dashboard sidebar.


## Backfilling data

By default, all pipeline runs process the previous UTC day. You can run the pipeline for a custom date range using Bruin’s `--start-date` and `--end-date` parameters.

Dates must be provided in UTC using ISO format.

**🟡 Local Mode**
``` bruin run \
  --start-date 2026-03-25T00:00:00Z \
  --end-date 2026-03-31T23:59:59Z \
  pipelines/local/assets/*.py \
  pipelines/local/assets/*.sql
```

What it does
- Processes each day in the specified range
- Updates the DuckDB tables
- Maintains the rolling 7-day window (older local data may be removed)

**🔵 Cloud Mode (Local Execution)**
```
bruin run \
  --start-date 2026-03-25T00:00:00Z \
  --end-date 2026-03-31T23:59:59Z \
  pipelines/cloud/assets/*.py \
  pipelines/cloud/assets/*.sql
```

**🔵 Cloud Mode (Bruin Cloud)**

Backfilling in Bruin Cloud is done by triggering a manual run with a custom date range.

Steps
- Open the pipeline in Bruin Cloud
- Trigger a manual run
- Provide:
    - start_date
    - end_date

Notes
- Dates should be in UTC
- The pipeline will process each day in the specified range
- Existing partitions in BigQuery will be overwritten for those dates

## Selected Repos
The project focuses on a curated set of 15 data engineering / analytics repositories:

- `apache/airflow`
- `ClickHouse/ClickHouse`
- `metabase/metabase`
- `apache/superset`
- `airbytehq/airbyte`
- `apache/spark`
- `trinodb/trino`
- `duckdb/duckdb`
- `dbt-labs/dbt-core`
- `dagster-io/dagster`
- `PrefectHQ/prefect`
- `apache/flink`
- `DataTalksClub/data-engineering-zoomcamp`
- `kestra-io/kestra`
- `bruin-data/bruin`

> [!NOTE]
> This list can be changed. To analyze a different set of repositories, update the filtering logic in the asset that creates `stg_selected_events`.


[^1]: `union_by_name` helps handle schema drift when reading multiple JSON files whose fields are not perfectly aligned. DuckDB aligns columns by name and fills missing values with nulls where needed.

[^2]: `sample_size = -1` forces a full scan during schema inference instead of sampling only part of the data. This helps detect fields that appear only in a small subset of records.

[^3]: Custom SQL checks were used instead of relying on built-in checks because the cloud pipeline uses fully qualified BigQuery table references, and custom checks gave more control across environments.
