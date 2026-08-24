# Ireland Constellation

Enterprise conversational analytics platform: persona-aware dashboard generation,
LangGraph-orchestrated agents (BigQuery text-to-SQL + Vertex AI Grounding), and
enterprise-grade access control (row/column/dashboard/folder level security) with
full request auditing.

## Repo layout

```
ireland-constellation/
├── backend/                     # FastAPI app
│   └── app/
│       ├── main.py              # app entrypoint, middleware wiring
│       ├── config.py            # env/config loading
│       ├── middleware/
│       │   ├── auth.py          # Firebase ID token verification
│       │   └── permissions.py   # dashboard/folder ACL enforcement
│       ├── services/
│       │   ├── bigquery_client.py   # BQ query execution + audit logging
│       │   └── firestore_client.py  # dashboards/folders/ACL CRUD
│       ├── models/
│       │   └── schemas.py       # Pydantic request/response models
│       └── routers/
│           ├── dashboards.py
│           └── folders.py
├── infra/
│   ├── bigquery/
│   │   ├── setup_dataset.sql        # dataset + core tables
│   │   ├── row_access_policies.sql  # RLS policies
│   │   ├── audit_log_schema.sql     # audit_log table
│   │   └── column_policy_tags.py    # Data Catalog taxonomy + policy tags (CLS)
│   └── firestore/
│       └── firestore.rules          # Firestore security rules for ACL docs
└── .env.example
```

## How the security model fits together

1. **Row-level security (BigQuery)** — `row_access_policies.sql` restricts which
   *rows* a query can see based on the authenticated user's group, via a
   `user_access_map` table joined against `SESSION_USER()`.
2. **Column-level security (BigQuery)** — `column_policy_tags.py` creates a Data
   Catalog taxonomy (e.g. `PII`, `Financial`, `Internal`) and tags sensitive
   columns. Access to tagged columns is granted via IAM `Fine-Grained Reader`
   bindings per group — a user without the binding gets a permission error on
   that column, even if the row is otherwise visible.
3. **Dashboard/folder-level security (app layer)** — BigQuery doesn't know what
   a "dashboard" is, so this lives in Firestore. Every dashboard/folder document
   carries an `acl` array of `{principal, role}`. `permissions.py` enforces this
   on every request *before* anything touches BigQuery or LangGraph.
4. **Audit logging** — every request that reaches the backend, whether it
   succeeds, is denied, or errors, gets one row in BigQuery's `audit_log` table,
   written via `bigquery_client.py`'s streaming insert wrapper.

Two independent enforcement layers (BQ RLS/CLS + app-layer ACL checks) is
intentional defense-in-depth: a bug in one shouldn't be a full data breach.

## Setup order

1. `bq query < infra/bigquery/setup_dataset.sql`
2. `bq query < infra/bigquery/row_access_policies.sql`
3. `python infra/bigquery/column_policy_tags.py`
4. `bq query < infra/bigquery/audit_log_schema.sql`
5. Deploy `infra/firestore/firestore.rules` via `firebase deploy --only firestore:rules`
6. `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
