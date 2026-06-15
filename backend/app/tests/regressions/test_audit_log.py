"""Reproduce bug Fase 3: UUID y datetime en audit_log.changes fallaban serialización JSONB."""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.enums import AuditAction
from app.models.audit import AuditLog


async def test_audit_log_serializes_uuid_in_changes(db, admin_user):
    """UUID en changes dict debe persistirse en JSONB sin error de serialización."""
    old_id = uuid4()
    new_id = uuid4()
    log = AuditLog(
        id=uuid4(),
        user_id=admin_user.id,
        entity_type="product",
        entity_id=uuid4(),
        action=AuditAction.UPDATE,
        changes={"base_unit_id": {"old": str(old_id), "new": str(new_id)}},
    )
    db.add(log)
    # flush -> INSERT al JSONB. Si el serializer falla, esto lanza TypeError/ProgrammingError.
    await db.flush()

    row = (await db.execute(select(AuditLog).where(AuditLog.id == log.id))).scalar_one()
    assert row.changes["base_unit_id"]["old"] == str(old_id)
    assert row.changes["base_unit_id"]["new"] == str(new_id)


async def test_audit_log_serializes_datetime_in_changes(db, admin_user):
    """datetime en changes dict debe persistirse en JSONB sin error de serialización."""
    ts = datetime.now(timezone.utc)
    log = AuditLog(
        id=uuid4(),
        user_id=admin_user.id,
        entity_type="product",
        entity_id=uuid4(),
        action=AuditAction.UPDATE,
        changes={"deleted_at": {"old": None, "new": ts.isoformat()}},
    )
    db.add(log)
    await db.flush()

    row = (await db.execute(select(AuditLog).where(AuditLog.id == log.id))).scalar_one()
    assert row.changes["deleted_at"]["new"] == ts.isoformat()
