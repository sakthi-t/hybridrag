from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalScope:
    user_id: str | None = None
    workspace_id: str | None = None
    document_ids: list[str] = field(default_factory=list)
    file_types: list[str] = field(default_factory=list)


def build_metadata_filter(scope: RetrievalScope) -> dict[str, Any]:
    conditions: list[dict[str, Any]] = []

    if scope.user_id:
        conditions.append({"user_id": scope.user_id})

    if scope.workspace_id:
        conditions.append({"workspace_id": scope.workspace_id})

    if scope.document_ids:
        if len(scope.document_ids) == 1:
            conditions.append({"document_id": scope.document_ids[0]})
        else:
            conditions.append({"$or": [{"document_id": did} for did in scope.document_ids]})

    if scope.file_types:
        if len(scope.file_types) == 1:
            conditions.append({"file_type": scope.file_types[0]})
        else:
            conditions.append({"$or": [{"file_type": ft} for ft in scope.file_types]})

    if not conditions:
        return {}

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}
