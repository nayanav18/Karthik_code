import uuid

from fastapi import APIRouter, Request, Depends

from app.middleware.permissions import require_folder_access
from app.models.schemas import CreateFolderRequest
from app.services import firestore_client

router = APIRouter(prefix="/folders", tags=["folders"])


@router.post("")
async def create_folder(request: Request, body: CreateFolderRequest):
    user = request.state.user
    folder_id = str(uuid.uuid4())
    folder = await firestore_client.create_folder(
        folder_id=folder_id, owner_uid=user["uid"], parent_id=body.parent_id, name=body.name
    )
    return {"id": folder_id, **folder}


@router.get("/{folder_id}")
async def get_folder(folder_id: str, folder: dict = Depends(require_folder_access(role="viewer"))):
    return folder
