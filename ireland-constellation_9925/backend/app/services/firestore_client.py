"""
Thin async-friendly wrapper around Firestore for dashboards/folders/ACLs.
Firestore's Python SDK is sync by default; wrapped with run_in_executor so
FastAPI routes can `await` it without blocking the event loop.
"""

import asyncio
from google.cloud import firestore
from app.config import settings

_db = firestore.Client(project=settings.GCP_PROJECT_ID)


def _to_thread(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: fn(*args, **kwargs))


async def get_dashboard(dashboard_id: str) -> dict | None:
    doc = await _to_thread(_db.collection("dashboards").document(dashboard_id).get)
    return doc.to_dict() if doc.exists else None


async def get_folder(folder_id: str) -> dict | None:
    doc = await _to_thread(_db.collection("folders").document(folder_id).get)
    return doc.to_dict() if doc.exists else None


async def create_dashboard(dashboard_id: str, owner_uid: str, folder_id: str | None, title: str) -> dict:
    data = {
        "title": title,
        "owner": owner_uid,
        "folder_id": folder_id,
        "acl": [{"principal": owner_uid, "role": "owner"}],
        "viz_specs": [],
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    await _to_thread(_db.collection("dashboards").document(dashboard_id).set, data)
    return data


async def create_folder(folder_id: str, owner_uid: str, parent_id: str | None, name: str) -> dict:
    data = {
        "name": name,
        "parent_id": parent_id,
        "acl": [{"principal": owner_uid, "role": "owner"}],
        "created_at": firestore.SERVER_TIMESTAMP,
    }
    await _to_thread(_db.collection("folders").document(folder_id).set, data)
    return data


async def update_dashboard_acl(dashboard_id: str, acl: list[dict]) -> None:
    await _to_thread(_db.collection("dashboards").document(dashboard_id).update, {"acl": acl})


async def append_viz_spec(dashboard_id: str, viz_spec: dict) -> None:
    await _to_thread(
        _db.collection("dashboards").document(dashboard_id).update,
        {"viz_specs": firestore.ArrayUnion([viz_spec])},
    )
