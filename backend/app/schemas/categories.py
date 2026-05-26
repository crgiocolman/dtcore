from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None


class CategoryOut(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class CategoryTreeNode(BaseModel):
    id: UUID
    name: str
    parent_id: UUID | None
    is_active: bool
    children: list["CategoryTreeNode"] = []


CategoryTreeNode.model_rebuild()
