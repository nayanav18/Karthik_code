import time
import uuid

from fastapi import APIRouter, Request, Depends

from app.middleware.permissions import require_dashboard_access
from app.models.schemas import CreateDashboardRequest, UpdateAclRequest
from app.services import firestore_client, bigquery_client

router = APIRouter(prefix="/dashboards", tags=["dashboards"])


@router.post("")
async def create_dashboard(request: Request, body: CreateDashboardRequest):
    user = request.state.user
    dashboard_id = str(uuid.uuid4())
    dashboard = await firestore_client.create_dashboard(
        dashboard_id=dashboard_id, owner_uid=user["uid"], folder_id=body.folder_id, title=body.title
    )
    return {"id": dashboard_id, **dashboard}


@router.get("/{dashboard_id}")
async def get_dashboard(
    dashboard_id: str,
    request: Request,
    dashboard: dict = Depends(require_dashboard_access(role="viewer")),
):
    started_at = time.time()
    bigquery_client.write_audit_log(
        user_id=request.state.user["uid"],
        persona=request.state.user.get("persona"),
        query_text=None,
        route_taken="none",
        generated_sql=None,
        tables_accessed=[],
        columns_accessed=[],
        grounding_sources=[],
        dashboard_id=dashboard_id,
        folder_id=dashboard.get("folder_id"),
        permission_result="allowed",
        guardrail_flags=[],
        response_status="success",
        started_at=started_at,
    )
    return dashboard


@router.patch("/{dashboard_id}/acl")
async def update_dashboard_acl(
    dashboard_id: str,
    body: UpdateAclRequest,
    _: dict = Depends(require_dashboard_access(role="owner")),
):
    await firestore_client.update_dashboard_acl(dashboard_id, [entry.model_dump() for entry in body.acl])
    return {"status": "updated"}
