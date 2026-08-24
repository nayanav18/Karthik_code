-- Every request the backend handles gets one row here, regardless of outcome.
-- Partitioned by day and clustered by user_id for cheap, fast audit queries.

CREATE TABLE IF NOT EXISTS `your_project.ireland_constellation.audit_log` (
  request_id STRING NOT NULL,
  user_id STRING NOT NULL,
  persona STRING,
  request_timestamp TIMESTAMP NOT NULL,
  query_text STRING,
  route_taken STRING,                 -- 'bigquery' | 'grounding' | 'both'
  generated_sql STRING,
  tables_accessed ARRAY<STRING>,
  columns_accessed ARRAY<STRING>,
  grounding_sources ARRAY<STRING>,
  dashboard_id STRING,
  folder_id STRING,
  permission_result STRING,           -- 'allowed' | 'denied'
  guardrail_flags ARRAY<STRING>,      -- e.g. ['prompt_injection_suspected']
  response_status STRING,             -- 'success' | 'error' | 'denied'
  latency_ms INT64
)
PARTITION BY DATE(request_timestamp)
CLUSTER BY user_id;
