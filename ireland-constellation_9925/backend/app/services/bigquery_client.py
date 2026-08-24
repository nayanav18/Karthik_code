"""
Wraps BigQuery access for two purposes:
  1. Executing (guardrailed) SQL against the Ireland dataset, on behalf of a
     specific user, so row/column-level security policies apply per-caller.
  2. Writing one audit_log row per request via streaming insert.

Per-user row-level security requires the query to run under the *caller's*
identity, not a shared service account — otherwise SESSION_USER() in the
row access policy resolves to the service account and RLS is bypassed.
In production this typically means either (a) BigQuery's Python client
authenticated with the end user's OAuth credentials (impersonation), or
(b) a Cloud Run service configured to forward the user's identity token.
This wrapper takes `user_credentials` explicitly to make that requirement
visible rather than silently defaulting to a service account.
"""

import time
import uuid
from google.cloud import bigquery
from app.config import settings

ALLOWED_TABLES = {"regional_metrics"}  # SQL guardrail allowlist


class SQLGuardrailError(Exception):
    pass


def validate_generated_sql(sql: str) -> None:
    """Minimal guardrail: block DML/DDL, enforce table allowlist, cap rows."""
    lowered = sql.strip().lower()
    if not lowered.startswith("select"):
        raise SQLGuardrailError("Only SELECT statements are permitted")

    forbidden = ["insert", "update", "delete", "drop", "alter", "create", "merge", "truncate"]
    if any(f" {kw} " in f" {lowered} " for kw in forbidden):
        raise SQLGuardrailError("Generated SQL contains a disallowed statement")

    if not any(table in lowered for table in ALLOWED_TABLES):
        raise SQLGuardrailError("Generated SQL does not reference an allowed table")

    if "limit" not in lowered:
        sql = sql.rstrip().rstrip(";") + " LIMIT 1000"

    return sql


def run_user_query(sql: str, user_credentials) -> list[dict]:
    validated_sql = validate_generated_sql(sql)
    client = bigquery.Client(project=settings.GCP_PROJECT_ID, credentials=user_credentials)
    job = client.query(validated_sql)
    return [dict(row) for row in job.result()]


def write_audit_log(
    *,
    user_id: str,
    persona: str | None,
    query_text: str | None,
    route_taken: str,
    generated_sql: str | None,
    tables_accessed: list[str],
    columns_accessed: list[str],
    grounding_sources: list[str],
    dashboard_id: str | None,
    folder_id: str | None,
    permission_result: str,
    guardrail_flags: list[str],
    response_status: str,
    started_at: float,
) -> None:
    client = bigquery.Client(project=settings.GCP_PROJECT_ID)
    table_ref = f"{settings.GCP_PROJECT_ID}.{settings.BQ_DATASET}.audit_log"

    row = {
        "request_id": str(uuid.uuid4()),
        "user_id": user_id,
        "persona": persona,
        "request_timestamp": time.time(),
        "query_text": query_text,
        "route_taken": route_taken,
        "generated_sql": generated_sql,
        "tables_accessed": tables_accessed,
        "columns_accessed": columns_accessed,
        "grounding_sources": grounding_sources,
        "dashboard_id": dashboard_id,
        "folder_id": folder_id,
        "permission_result": permission_result,
        "guardrail_flags": guardrail_flags,
        "response_status": response_status,
        "latency_ms": int((time.time() - started_at) * 1000),
    }

    errors = client.insert_rows_json(table_ref, [row])
    if errors:
        # Never let a logging failure break the user-facing request — log locally instead.
        print(f"[audit_log] insert failed: {errors}")
