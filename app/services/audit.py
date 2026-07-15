from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def write_audit(
    db: Session,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            metadata_json=metadata,
            created_at=datetime.now(UTC),
        )
    )
