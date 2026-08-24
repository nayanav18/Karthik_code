-- Ireland Constellation: core dataset + tables
-- Run with: bq query --use_legacy_sql=false < setup_dataset.sql

CREATE SCHEMA IF NOT EXISTS `your_project.ireland_constellation`
OPTIONS (location = 'europe-west1');

-- Core Ireland dataset (example shape — replace with your real schema)
CREATE TABLE IF NOT EXISTS `your_project.ireland_constellation.regional_metrics` (
  record_id STRING NOT NULL,
  country_region STRING NOT NULL,   -- e.g. 'Munster', 'Leinster', 'Connacht', 'Ulster'
  metric_date DATE NOT NULL,
  metric_name STRING NOT NULL,
  metric_value FLOAT64,
  customer_account_id STRING,       -- example sensitive column -> column-tagged PII/Internal
  revenue_amount FLOAT64,           -- example sensitive column -> column-tagged Financial
  ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);

-- Maps a principal (user email or group email) to the region(s) they're
-- allowed to see. Drives the row access policy below.
CREATE TABLE IF NOT EXISTS `your_project.ireland_constellation.user_access_map` (
  principal STRING NOT NULL,        -- e.g. 'analyst-team@yourco.com' or a user email
  allowed_region STRING NOT NULL,   -- 'ALL' grants every region
  granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
);
