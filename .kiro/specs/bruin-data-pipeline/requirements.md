# Requirements Document

## Introduction

This feature delivers a Bruin data pipeline that runs in the VPS layer of the Smart Plant Monitoring system. The pipeline reads raw, MQTT-ingested staging tables in DuckDB (sensor readings, image disease analytics, BMKG weather snapshots and forecasts) and transforms them into curated, analytics-ready tables. The curated tables are consumed by two downstream services: the ETL uploader, which incrementally loads them into BigQuery, and the Streamlit dashboard, which renders near-real-time plant health views. The pipeline is organized into three domain-aligned sub-pipelines (camera, sensor, weather) and runs on a scheduled cadence inside the existing `bruin` docker-compose service.

## Glossary

- **Bruin_Pipeline**: The complete Bruin workspace at `./bruin/` containing `pipeline.yml`, `.bruin.yml`, and a tree of asset definitions executed by `bruin run .`.
- **Camera_Pipeline**: The sub-pipeline that transforms `image_log` and `image_analytics` staging tables into curated camera/disease tables.
- **Sensor_Pipeline**: The sub-pipeline that transforms the `sensor` staging table into curated environmental telemetry tables.
- **Weather_Pipeline**: The sub-pipeline that transforms `bmkg_weather` and `bmkg_weather_forecast` staging tables into curated weather tables.
- **Staging_Table**: A raw DuckDB table populated by the Ingestor or external loaders; one of `image_log`, `image_analytics`, `sensor`, `bmkg_weather`, `bmkg_weather_forecast`.
- **Curated_Table**: A Bruin-materialized DuckDB table under the `curated` schema, with a stable schema, primary key, and quality checks; the unit of consumption for ETL and Dashboard.
- **DuckDB_Default**: The single shared DuckDB database file located at `/data/duckdb.db` inside containers and `./bruin/duckdb.db` on the host, accessed via the `duckdb-default` connection in `.bruin.yml`.
- **ETL_Service**: The `etl` docker-compose service that incrementally uploads `Curated_Table` rows into BigQuery.
- **Dashboard_Service**: The `dashboard` docker-compose service (Streamlit) that reads `Curated_Table` rows for visualization.
- **Plant_Id**: A logical identifier of a monitored plant; derived from MQTT topic `plants/<plant_id>/...` and propagated through the pipeline.
- **Watermark_Column**: A monotonically non-decreasing timestamp column on a `Curated_Table` (`event_time` or `ingested_at`) used by `ETL_Service` for incremental extraction.
- **Quality_Check**: A Bruin column-level check (`not_null`, `unique`, `positive`, `accepted_values`) or `custom_checks` block defined in an asset's frontmatter.
- **Round_Trip_Property**: A property that asserts that re-running an asset on the same staging snapshot produces a curated table whose contents (excluding `ingested_at`) are equal to the previous run's output.
- **Pipeline_Run**: A single invocation of `bruin run .` over the `Bruin_Pipeline`.
- **Run_Timestamp**: A single `TIMESTAMP` value evaluated once at the start of a Pipeline_Run and reused as the `ingested_at` value for every Curated_Table written during that run.

## Requirements

### Requirement 1: Bruin Workspace Layout

**User Story:** As a data engineer, I want the Bruin pipeline to live at the path the docker-compose `bruin` service mounts, so that `docker compose run --rm bruin` executes it without configuration changes.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL be rooted at the workspace path `./bruin/` and SHALL contain a `pipeline.yml` file and a `.bruin.yml` file directly at that path.
2. THE Bruin_Pipeline `pipeline.yml` SHALL declare a non-empty `name`, a non-empty `schedule`, a `start_date` formatted as `YYYY-MM-DD`, a boolean `catchup`, and a `default_connections.duckdb` value equal to the connection name defined in `.bruin.yml`.
3. THE Bruin_Pipeline `.bruin.yml` SHALL define exactly one DuckDB connection with name `duckdb-default` whose `path` is the string `/data/duckdb.db`.
4. THE Bruin_Pipeline SHALL organize assets exclusively under `assets/camera/`, `assets/sensor/`, and `assets/weather/`, with at least one asset file per directory, corresponding to `Camera_Pipeline`, `Sensor_Pipeline`, and `Weather_Pipeline` respectively.
5. WHEN `bruin run .` is executed from `/workspace` inside the `bruin` container against a populated DuckDB_Default, THE Bruin_Pipeline SHALL exit with status code 0 within 600 seconds.
6. IF `pipeline.yml`, `.bruin.yml`, the `duckdb-default` connection, or any of the three required asset directories is missing or malformed, THEN THE Bruin_Pipeline SHALL exit with a non-zero status code, SHALL emit an error identifying the missing or malformed item, and SHALL leave the DuckDB_Default file unchanged.

### Requirement 2: Source Declarations for Staging Tables

**User Story:** As a data engineer, I want every staging table consumed by the pipeline to be declared as a Bruin source, so that asset dependencies and lineage are explicit.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL declare a source asset for `image_log` referencing the existing DuckDB table `image_log` in DuckDB_Default.
2. THE Bruin_Pipeline SHALL declare a source asset for `image_analytics` referencing the existing DuckDB table `image_analytics` in DuckDB_Default.
3. THE Bruin_Pipeline SHALL declare a source asset for `sensor` referencing the existing DuckDB table `sensor` in DuckDB_Default.
4. THE Bruin_Pipeline SHALL declare a source asset for `bmkg_weather` referencing the existing DuckDB table `bmkg_weather` in DuckDB_Default.
5. THE Bruin_Pipeline SHALL declare a source asset for `bmkg_weather_forecast` referencing the existing DuckDB table `bmkg_weather_forecast` in DuckDB_Default.
6. WHERE a source asset is declared, THE Bruin_Pipeline SHALL list every column defined in the corresponding `sources/*.sql` staging schema with each declared `name` matching the staging column name case-sensitively and each declared `type` matching the staging column type, with no missing or extra columns.
7. IF a referenced staging table does not exist in DuckDB_Default when a Pipeline_Run begins executing an asset that depends on it, THEN THE Bruin_Pipeline SHALL fail that asset with an error containing the missing table name, SHALL NOT create, overwrite, or empty the dependent Curated_Table, and SHALL continue executing assets whose source dependencies are all present.
8. IF a column declared in a source asset is absent from the referenced DuckDB staging table or its declared `type` differs from the actual column type, THEN THE Bruin_Pipeline SHALL fail the affected source asset with an error identifying the source asset name, the offending column name, and whether the mismatch is a missing column or a type difference.

### Requirement 3: Camera Pipeline Curated Tables

**User Story:** As a dashboard user, I want curated camera/disease tables, so that I can see per-plant disease incidence over time and the latest health status for each plant.

#### Acceptance Criteria

1. THE Camera_Pipeline SHALL produce a curated table `curated.camera_events` whose row set is the inner join of `image_analytics` to `image_log` on `filename`, with exactly the columns `plant_id`, `filename`, `event_time` (sourced from `image_log.event_time`), `plant_type`, `health_status`, `confidence`, `severity`, `summary`, and `ingested_at`.
2. WHERE an `image_analytics.filename` has no matching row in `image_log`, THE Camera_Pipeline SHALL exclude that filename from `curated.camera_events` and SHALL emit one row per excluded filename into a `curated.camera_events_orphans` table containing `filename` and `image_analytics.event_time`.
3. THE Camera_Pipeline SHALL produce a curated table `curated.camera_daily_disease` aggregating `curated.camera_events` to one row per (`plant_id`, `event_date`, `health_status`), where `event_date` is `CAST(event_time AS DATE)` evaluated in UTC, with columns `event_count` (count of rows), `avg_confidence` (mean over rows whose `confidence` is not null), `avg_severity` (mean over rows whose `severity` is not null), and `ingested_at`.
4. THE Camera_Pipeline SHALL produce a curated table `curated.camera_latest_status` with one row per `plant_id`, where the row selected for each `plant_id` is the row in `curated.camera_events` with the greatest `event_time` and, when multiple rows share the greatest `event_time`, the row with the lexicographically greatest `filename`, exposing columns `plant_id`, `event_time`, `health_status`, `confidence`, `severity`, `summary`, and `ingested_at`.
5. WHEN `health_status` in `image_analytics` is non-null, THE Camera_Pipeline SHALL constrain `curated.camera_events.health_status` to the `accepted_values` set `{"healthy", "diseased", "unknown"}` via a Quality_Check that fails the affected asset on any violating value.
6. IF `image_analytics.confidence` is non-null and outside the closed interval `[0.0, 1.0]`, THEN THE Camera_Pipeline SHALL fail the affected asset's `confidence` Quality_Check with an error identifying the offending `filename` values.
7. THE Camera_Pipeline SHALL declare `not_null` and `unique` Quality_Checks on `curated.camera_events.filename` that fail the asset run on any violation.
8. THE Camera_Pipeline SHALL declare a `not_null` Quality_Check on `curated.camera_events.event_time` and a `not_null` Quality_Check on `curated.camera_events.plant_id`, each failing the asset run on any violation.

### Requirement 4: Sensor Pipeline Curated Tables

**User Story:** As a dashboard user, I want curated sensor telemetry tables, so that I can see per-plant environmental trends and hourly aggregates aligned with disease events.

#### Acceptance Criteria

1. THE Sensor_Pipeline SHALL produce a curated table `curated.sensor_events` with exactly the columns `plant_id`, `event_time` (interpreted in UTC), `temperature`, `humidity`, `soil_moisture`, `filename`, and `ingested_at`, derived row-for-row from the `sensor` staging table with column renames `temp -> temperature`, `humid -> humidity`, `soil -> soil_moisture`.
2. THE Sensor_Pipeline SHALL produce a curated table `curated.sensor_hourly` aggregating `curated.sensor_events` to one row per (`plant_id`, `hour_bucket_utc`), where `hour_bucket_utc` is `date_trunc('hour', event_time)` evaluated in UTC, with columns `avg_temperature`, `avg_humidity`, `avg_soil_moisture`, `min_temperature`, `max_temperature`, `min_humidity`, `max_humidity`, `min_soil_moisture`, `max_soil_moisture` (each computed over rows whose corresponding metric is not null), `sample_count` (count of all rows in the bucket regardless of nullness), and `ingested_at`.
3. THE Sensor_Pipeline SHALL declare `not_null` Quality_Checks on `curated.sensor_events.plant_id` and `curated.sensor_events.event_time` that fail the asset run on any violation.
4. IF `temperature` is non-null and outside the closed interval `[-40.0, 85.0]`, THEN THE Sensor_Pipeline SHALL fail the affected asset's `temperature` range Quality_Check with an error identifying the offending row's `plant_id` and `event_time`.
5. IF `humidity` is non-null and strictly less than `0.0` or strictly greater than `100.0`, THEN THE Sensor_Pipeline SHALL fail the affected asset's `humidity` range Quality_Check with an error identifying the offending row's `plant_id` and `event_time` (boundary values `0.0` and `100.0` are accepted).
6. IF `soil_moisture` is non-null and outside the closed interval `[0.0, 1023.0]`, THEN THE Sensor_Pipeline SHALL fail the affected asset's `soil_moisture` range Quality_Check with an error identifying the offending row's `plant_id` and `event_time`.
7. THE Sensor_Pipeline SHALL declare a `unique` Quality_Check (expressed as a `custom_checks` row-count query equal to zero) on the composite key (`plant_id`, `event_time`) of `curated.sensor_events` that fails the asset run on any duplicate.
8. IF any Quality_Check on `curated.sensor_events` fails during a Pipeline_Run, THEN THE Sensor_Pipeline SHALL not execute downstream assets that depend on `curated.sensor_events` (including `curated.sensor_hourly` and `curated.plant_event_joined`).

### Requirement 5: Weather Pipeline Curated Tables

**User Story:** As a dashboard user, I want curated weather tables that combine the BMKG snapshot and multi-day forecast, so that I can correlate plant condition with environmental conditions.

#### Acceptance Criteria

1. WHEN a Pipeline_Run executes the corresponding asset, THE Weather_Pipeline SHALL produce a curated table `curated.weather_current` with exactly one row per `adm4` location, selecting for each `adm4` the row with the greatest `observed_at` extracted from `bmkg_weather.weather_data` JSON, exposing flattened columns `adm4`, `provinsi`, `kotkab`, `kecamatan`, `desa`, `lon`, `lat`, `timezone`, `observed_at`, `temperature`, `humidity`, `wind_speed`, `weather_desc`, and `ingested_at`.
2. WHEN a Pipeline_Run executes the corresponding asset, THE Weather_Pipeline SHALL produce a curated table `curated.weather_forecast_hourly` derived from `bmkg_weather_forecast` with renamed columns `t -> temperature`, `hu -> humidity`, `tp -> precipitation_mm`, `ws -> wind_speed`, `tcc -> cloud_cover_pct`, `vs -> visibility_meters` and preserved columns `adm4`, `datetime_utc`, `datetime_local`, `weather_desc`, `weather_desc_en`, `image`, plus `ingested_at`.
3. THE Weather_Pipeline SHALL declare a `unique` Quality_Check (expressed as a `custom_checks` row-count query equal to zero) on the composite key (`adm4`, `datetime_utc`) of `curated.weather_forecast_hourly` that fails the asset run when one or more duplicates exist.
4. THE Weather_Pipeline SHALL declare `not_null` Quality_Checks on `adm4` and `datetime_utc` of `curated.weather_forecast_hourly` that fail the asset run when one or more null values exist.
5. IF `humidity` in `curated.weather_forecast_hourly` is non-null and strictly less than `0.0` or strictly greater than `100.0`, THEN THE Weather_Pipeline SHALL fail the affected asset's `humidity` range Quality_Check (boundary values `0.0` and `100.0` are accepted; null values do not trigger this check).
6. IF `cloud_cover_pct` in `curated.weather_forecast_hourly` is non-null and strictly less than `0.0` or strictly greater than `100.0`, THEN THE Weather_Pipeline SHALL fail the affected asset's `cloud_cover_pct` range Quality_Check (boundary values `0.0` and `100.0` are accepted; null values do not trigger this check).
7. THE Weather_Pipeline SHALL declare `not_null` and `unique` Quality_Checks on `curated.weather_current.adm4` that fail the asset run on any violation.

### Requirement 6: JSON Parsing of BMKG Weather Snapshot

**User Story:** As a data engineer, I want the BMKG weather JSON payload parsed into typed columns with a verifiable round-trip, so that downstream consumers see a stable schema and ingestion bugs are caught early.

#### Acceptance Criteria

1. WHEN a Pipeline_Run executes the parsing asset, THE Weather_Pipeline SHALL parse `bmkg_weather.weather_data` (DuckDB `JSON`) into the typed columns of `curated.weather_current` defined in Requirement 5.1.
2. THE Weather_Pipeline SHALL declare `not_null` Quality_Checks on `curated.weather_current.adm4` and `curated.weather_current.observed_at` that fail the asset run on any violation.
3. THE Weather_Pipeline SHALL declare a `unique` Quality_Check on `curated.weather_current.adm4` that fails the asset run on any duplicate.
4. IF `bmkg_weather.weather_data` is `NULL` or fails JSON extraction for any of the required fields `adm4`, `observed_at`, `temperature`, `humidity`, `wind_speed`, `weather_desc`, THEN THE Weather_Pipeline SHALL exclude the affected row from `curated.weather_current` and SHALL emit a row into a `curated.weather_current_rejects` table containing the original `id`, `adm4`, the name of the missing or unparseable field, and a textual reason.
5. WHEN the parsing asset is executed twice in succession against the same `bmkg_weather` snapshot (no rows added, modified, or deleted between runs), THE Weather_Pipeline SHALL produce a `curated.weather_current` table whose contents excluding `ingested_at` are byte-equivalent across the two runs (Round_Trip_Property).

### Requirement 7: Cross-Domain Joined View for the Dashboard

**User Story:** As a dashboard user, I want a single curated view that joins disease predictions to the sensor telemetry captured at the same time, so that I can correlate environmental conditions with detected plant health issues.

#### Acceptance Criteria

1. THE Camera_Pipeline SHALL produce a curated table `curated.plant_event_joined` with one row per `curated.camera_events.filename`, joined LEFT to `curated.sensor_events` on `filename`, exposing columns `plant_id` (from `curated.camera_events`), `filename`, `event_time` (from `curated.camera_events`), `health_status`, `confidence`, `severity`, `temperature` (from `curated.sensor_events`), `humidity` (from `curated.sensor_events`), `soil_moisture` (from `curated.sensor_events`), and `ingested_at`.
2. WHERE multiple rows in `curated.sensor_events` share the same `filename`, THE Camera_Pipeline SHALL select the sensor row whose `event_time` is closest in absolute distance to the camera row's `event_time` and, on ties, the sensor row with the smallest `event_time`, so that the output remains exactly one row per camera `filename`.
3. IF a `curated.camera_events` row has no matching `curated.sensor_events` row by `filename`, THEN THE Camera_Pipeline SHALL emit the camera row into `curated.plant_event_joined` with `temperature`, `humidity`, and `soil_moisture` set to `NULL`.
4. THE Camera_Pipeline SHALL declare `not_null` and `unique` Quality_Checks on `curated.plant_event_joined.filename` that fail the asset run on any violation.
5. THE Camera_Pipeline SHALL declare a `not_null` Quality_Check on `curated.plant_event_joined.plant_id` that fails the asset run on any violation.
6. THE Camera_Pipeline SHALL declare a `not_null` Quality_Check on `curated.plant_event_joined.event_time` that fails the asset run on any violation.

### Requirement 8: Materialization, Watermarks, and Incremental Compatibility

**User Story:** As an ETL engineer, I want curated tables to expose a stable monotonic watermark and a deterministic primary key, so that the ETL_Service can incrementally upload to BigQuery without duplicates or gaps.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL materialize every Curated_Table as `materialization.type: table` in DuckDB_Default under a schema named `curated`, and SHALL create the `curated` schema if it does not already exist.
2. THE Bruin_Pipeline SHALL evaluate the Run_Timestamp exactly once at the start of each Pipeline_Run and SHALL set the `ingested_at` column of every row written to a Curated_Table during that run to the Run_Timestamp value, with type `TIMESTAMP`.
3. FOR ALL pairs of successful Pipeline_Runs (R1, R2) where R2 starts after R1 ends, THE Bruin_Pipeline SHALL ensure the Run_Timestamp of R2 is strictly greater than the Run_Timestamp of R1.
4. THE Bruin_Pipeline SHALL define a primary-key column or composite key (of 2 to 4 columns) for every Curated_Table.
5. WHERE a Curated_Table has a single primary-key column, THE Bruin_Pipeline SHALL declare a `not_null` and a `unique` Quality_Check on that column; WHERE a Curated_Table has a composite primary key, THE Bruin_Pipeline SHALL declare a `not_null` Quality_Check on each component column and a `custom_checks` row-count query asserting that the count of rows whose composite key is duplicated equals zero.
6. WHEN a Pipeline_Run completes with exit status 0, THE Bruin_Pipeline SHALL leave every Curated_Table queryable through `/data/duckdb.db` in a single committed state with no partially-written rows visible to the ETL_Service.
7. IF a Pipeline_Run fails on any asset, THEN THE Bruin_Pipeline SHALL preserve every Curated_Table from previous successful runs that the current run did not yet attempt to rewrite, SHALL preserve the prior contents of any Curated_Table the current run started but did not finish writing (no partially-written table SHALL be exposed), and SHALL exit with a non-zero status code.

### Requirement 9: Idempotency of Pipeline Runs

**User Story:** As a data engineer, I want re-running the pipeline against an unchanged staging dataset to produce identical curated outputs, so that re-runs are safe and verifiable.

#### Acceptance Criteria

1. WHEN a Pipeline_Run is executed twice in succession against the same Staging_Table snapshot (no rows added, modified, or deleted between runs), THE Bruin_Pipeline SHALL produce, for every Curated_Table, a row set that matches row-by-row on all columns excluding `ingested_at` with no extra and no missing rows across the two runs.
2. WHEN a Pipeline_Run is executed twice in succession against the same Staging_Table snapshot, THE Bruin_Pipeline SHALL produce row counts for every Curated_Table that differ by exactly 0 rows across the two runs.
3. WHILE a Pipeline_Run is in progress, THE Bruin_Pipeline SHALL NOT hold any DuckDB transaction open across asset boundaries, and SHALL release any write lock acquired by an asset within 5 seconds of that asset's completion (DuckDB single-writer constraints during an active write are out of scope).
4. IF a prior Pipeline_Run failed and a subsequent Pipeline_Run executes successfully against the same Staging_Table snapshot that existed at the start of the failed run, THEN THE Bruin_Pipeline SHALL produce Curated_Tables whose contents excluding `ingested_at` are equal to the output of a single successful Pipeline_Run against that snapshot.

### Requirement 10: Quality Checks Coverage and Failure Behavior

**User Story:** As a data engineer, I want every curated table to have minimum quality coverage and to fail loudly on violation, so that bad data does not propagate into BigQuery and the dashboard.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL declare at least one `not_null` Quality_Check on every primary-key column of every Curated_Table, where "primary-key column" is the column or set of columns identified per Requirement 8.4.
2. THE Bruin_Pipeline SHALL declare at least one `unique` Quality_Check on the primary-key column of every Curated_Table, expressed as a column-level `unique` check for single-column keys and as a `custom_checks` row-count query asserting that the count of duplicated composite keys equals zero for composite keys.
3. THE Bruin_Pipeline SHALL declare a `custom_checks` row-count query named `row count is greater than zero` on every Curated_Table that is a non-aggregating, row-preserving projection of a Staging_Table that contains at least one row at the start of the Pipeline_Run.
4. IF any Quality_Check fails during a Pipeline_Run, THEN THE Bruin_Pipeline SHALL fail the affected asset, SHALL not execute downstream assets that depend on the failed asset, SHALL emit an error identifying the failed asset and the failed Quality_Check, and SHALL exit the Pipeline_Run with a non-zero status code.
5. WHERE a Curated_Table is an aggregating Curated_Table (one whose row count is strictly less than or equal to the row count of its source Curated_Table due to GROUP BY), THE Bruin_Pipeline SHALL exempt that table from the row-count check in criterion 3 but SHALL still apply criteria 1 and 2.

### Requirement 11: Scheduling Configuration

**User Story:** As a system operator, I want the pipeline to be schedulable on a fixed cadence, so that curated data is refreshed predictably without manual intervention.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL set `schedule: hourly` in `pipeline.yml` so that scheduled deployments trigger a Pipeline_Run within 60 seconds of each hour boundary in the configured timezone.
2. THE Bruin_Pipeline SHALL set `catchup: false` in `pipeline.yml` so that schedule slots missed while the scheduler was not running produce no Pipeline_Run and no failure indication.
3. WHEN invoked manually via `docker compose run --rm bruin`, THE Bruin_Pipeline SHALL execute exactly one Pipeline_Run regardless of schedule state and SHALL exit with status code 0 on success.
4. IF a manually-invoked Pipeline_Run encounters a non-recoverable error (resource constraints, configuration errors, missing connection), THEN THE Bruin_Pipeline SHALL exit with a non-zero status code without retrying, SHALL emit an error identifying the asset that failed, and SHALL require the operator to re-invoke the run manually.
5. IF `schedule` is missing or set to a value not accepted by Bruin, or `catchup` is missing or not a boolean, THEN THE Bruin_Pipeline SHALL fail at startup with a non-zero status code and an error identifying the invalid configuration field, before executing any asset.

### Requirement 12: Connection Configuration

**User Story:** As a data engineer, I want the DuckDB connection to be defined once and reused by every asset, so that paths and credentials are not duplicated across asset files.

#### Acceptance Criteria

1. THE Bruin_Pipeline SHALL define exactly one DuckDB connection entry with the name `duckdb-default` in `.bruin.yml` under `environments.default.connections.duckdb`, and the entry name SHALL match the value referenced by `default_connections.duckdb` in `pipeline.yml`.
2. THE Bruin_Pipeline SHALL set `default_connections.duckdb: duckdb-default` in `pipeline.yml` so that every `duckdb.sql` asset resolves to this connection without declaring its own `connection` field in the asset header.
3. THE Bruin_Pipeline SHALL set the `duckdb-default` `path` to `/data/duckdb.db`, the file path exposed by the `duckdb-data` volume mount inside the `bruin` container.
4. IF the `duckdb-default` connection is missing from `.bruin.yml`, or its `path` value is empty or not equal to `/data/duckdb.db`, THEN THE Bruin_Pipeline SHALL fail validation before executing any asset, SHALL produce an error identifying the missing or invalid DuckDB connection definition, and SHALL leave existing data files unchanged.
5. IF any `duckdb.sql` asset declares a `connection` value other than `duckdb-default`, THEN THE Bruin_Pipeline SHALL fail validation with an error identifying the offending asset and the conflicting connection name, and SHALL not execute that asset.
