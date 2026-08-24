from pydantic import BaseModel


class AclEntry(BaseModel):
    principal: str      # user email, uid, or 'group:xyz@yourco.com'
    role: str            # 'viewer' | 'editor' | 'owner'


class CreateDashboardRequest(BaseModel):
    title: str
    folder_id: str | None = None


class CreateFolderRequest(BaseModel):
    name: str
    parent_id: str | None = None


class UpdateAclRequest(BaseModel):
    acl: list[AclEntry]


class ChatRequest(BaseModel):
    message: str
    dashboard_id: str | None = None
