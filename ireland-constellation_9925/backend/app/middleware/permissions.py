"""
App-layer ACL enforcement for dashboards and folders. This is the
enforcement point for "dashboard-level" and "folder-level" security that
BigQuery has no concept of.

Used as a FastAPI dependency on any route that reads/writes a specific
dashboard or folder:

    @router.get("/dashboards/{dashboard_id}")
    async def get_dashboard(
        dashboard_id: str,
        _: dict = Depends(require_dashboard_access(role="viewer")),
    ):
        ...

Folder permissions are inherited downward: access to a folder implies the
same access to everything nested under it, so folder checks walk up the
parent chain looking for the first ACL entry that grants the caller access.
"""

from fastapi import Request, HTTPException, Depends
from app.services.firestore_client import get_dashboard, get_folder

ROLE_RANK = {"viewer": 0, "editor": 1, "owner": 2}


def _principal_matches(entry_principal: str, user: dict) -> bool:
    if entry_principal == user["uid"] or entry_principal == user.get("email"):
        return True
    if entry_principal.startswith("group:"):
        return entry_principal.removeprefix("group:") in user.get("groups", [])
    return False


def _acl_grants(acl: list[dict], user: dict, required_role: str) -> bool:
    required_rank = ROLE_RANK[required_role]
    for entry in acl:
        if _principal_matches(entry["principal"], user) and ROLE_RANK.get(entry["role"], -1) >= required_rank:
            return True
    return False


async def _check_folder_chain(folder_id: str, user: dict, required_role: str) -> bool:
    current_id = folder_id
    visited = set()
    while current_id and current_id not in visited:
        visited.add(current_id)
        folder = await get_folder(current_id)
        if folder is None:
            return False
        if _acl_grants(folder.get("acl", []), user, required_role):
            return True
        current_id = folder.get("parent_id")
    return False


def require_dashboard_access(role: str = "viewer"):
    async def _dependency(request: Request, dashboard_id: str):
        user = request.state.user
        dashboard = await get_dashboard(dashboard_id)
        if dashboard is None:
            raise HTTPException(status_code=404, detail="Dashboard not found")

        if _acl_grants(dashboard.get("acl", []), user, role):
            return dashboard

        folder_id = dashboard.get("folder_id")
        if folder_id and await _check_folder_chain(folder_id, user, role):
            return dashboard

        raise HTTPException(status_code=403, detail="Insufficient permissions on dashboard")

    return _dependency


def require_folder_access(role: str = "viewer"):
    async def _dependency(request: Request, folder_id: str):
        user = request.state.user
        if await _check_folder_chain(folder_id, user, role):
            folder = await get_folder(folder_id)
            return folder
        raise HTTPException(status_code=403, detail="Insufficient permissions on folder")

    return _dependency
