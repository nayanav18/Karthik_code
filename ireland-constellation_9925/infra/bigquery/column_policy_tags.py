"""
Sets up column-level security for BigQuery via Data Catalog policy tags.

Flow:
  1. Create a taxonomy (a namespace for classification labels).
  2. Create policy tags within it (e.g. PII, Financial, Internal).
  3. Attach a policy tag to specific columns on the target table.
  4. Grant the Data Catalog "Fine-Grained Reader" IAM role on a policy tag to
     the groups that should be able to see that column. Anyone without the
     binding gets a permission error querying that column, even if the row
     is visible to them under the row access policy.

Run once during setup: `python column_policy_tags.py`
Requires: pip install google-cloud-datacatalog google-cloud-bigquery
"""

from google.cloud import datacatalog_v1
from google.cloud import bigquery

PROJECT_ID = "your_project"
LOCATION = "europe-west1"
DATASET = "ireland_constellation"
TABLE = "regional_metrics"

# column_name -> (policy_tag_display_name, description)
COLUMN_TAG_MAP = {
    "customer_account_id": ("PII", "Directly identifies a customer account"),
    "revenue_amount": ("Financial", "Revenue figures — finance-sensitive"),
}

# policy_tag_display_name -> list of principals granted read access
TAG_GRANTS = {
    "PII": ["group:data-privacy-team@yourco.com", "group:eng-admins@yourco.com"],
    "Financial": ["group:finance-team@yourco.com", "group:eng-admins@yourco.com"],
}


def create_taxonomy(client: datacatalog_v1.PolicyTagManagerClient) -> str:
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    taxonomy = datacatalog_v1.Taxonomy(
        display_name="ireland_constellation_classification",
        description="Sensitivity classification for Ireland Constellation columns",
        activated_policy_types=[
            datacatalog_v1.Taxonomy.PolicyType.FINE_GRAINED_ACCESS_CONTROL
        ],
    )
    created = client.create_taxonomy(parent=parent, taxonomy=taxonomy)
    print(f"Created taxonomy: {created.name}")
    return created.name


def create_policy_tags(client: datacatalog_v1.PolicyTagManagerClient, taxonomy_name: str) -> dict:
    tag_names = {}
    seen = {tag for tag, _ in COLUMN_TAG_MAP.values()}
    for display_name in seen:
        policy_tag = datacatalog_v1.PolicyTag(display_name=display_name)
        created = client.create_policy_tag(parent=taxonomy_name, policy_tag=policy_tag)
        tag_names[display_name] = created.name
        print(f"Created policy tag '{display_name}': {created.name}")
    return tag_names


def grant_access(client: datacatalog_v1.PolicyTagManagerClient, tag_names: dict):
    from google.iam.v1 import iam_policy_pb2, policy_pb2

    for display_name, resource_name in tag_names.items():
        members = TAG_GRANTS.get(display_name, [])
        if not members:
            continue
        policy = policy_pb2.Policy(
            bindings=[
                policy_pb2.Binding(
                    role="roles/datacatalog.categoryFineGrainedReader",
                    members=members,
                )
            ]
        )
        client.set_iam_policy(
            request=iam_policy_pb2.SetIamPolicyRequest(resource=resource_name, policy=policy)
        )
        print(f"Granted {members} read access to '{display_name}'")


def apply_tags_to_table(tag_names: dict):
    bq_client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET}.{TABLE}"
    table = bq_client.get_table(table_ref)

    new_schema = []
    for field in table.schema:
        if field.name in COLUMN_TAG_MAP:
            tag_display_name, _ = COLUMN_TAG_MAP[field.name]
            policy_tags = bigquery.PolicyTagList(names=[tag_names[tag_display_name]])
            new_schema.append(
                bigquery.SchemaField(
                    field.name, field.field_type, mode=field.mode, policy_tags=policy_tags
                )
            )
        else:
            new_schema.append(field)

    table.schema = new_schema
    bq_client.update_table(table, ["schema"])
    print(f"Applied policy tags to columns on {table_ref}")


if __name__ == "__main__":
    ptm_client = datacatalog_v1.PolicyTagManagerClient()
    taxonomy_name = create_taxonomy(ptm_client)
    tag_names = create_policy_tags(ptm_client, taxonomy_name)
    grant_access(ptm_client, tag_names)
    apply_tags_to_table(tag_names)
