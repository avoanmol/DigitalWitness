from __future__ import annotations
from collections import defaultdict
from uuid import UUID
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from backend.app.ai.normalise import is_common_url
from backend.models import Case, CaseLink, Entity

def suggest_links_for_case(db: Session, case_id: UUID) -> int:
    current = db.scalars(select(Entity).where(Entity.case_id == case_id)).all()
    matchable = [item for item in current if not (item.type == "url" and is_common_url(item.raw_value))]
    if not matchable or db.get(Case, case_id) is None:
        return 0
    values = {(item.type, item.normalised_value) for item in matchable}
    candidates = db.scalars(select(Entity).where(Entity.case_id != case_id, Entity.type.in_({v[0] for v in values}), Entity.normalised_value.in_({v[1] for v in values}))).all()
    by_key: dict[tuple[str, str], list[Entity]] = defaultdict(list)
    for item in matchable + candidates:
        if item.type == "url" and is_common_url(item.raw_value):
            continue
        by_key[(item.type, item.normalised_value)].append(item)
    grouped: dict[tuple[UUID, UUID], dict[tuple[str, str], Entity]] = defaultdict(dict)
    for key, entities in by_key.items():
        lefts = [item for item in entities if item.case_id == case_id]
        rights = [item for item in entities if item.case_id != case_id]
        for left in lefts:
            for right in rights:
                pair = tuple(sorted((left.case_id, right.case_id), key=lambda item: item.int))
                grouped[pair][key] = left
    if not grouped:
        return 0
    existing = db.scalars(select(CaseLink).where(or_(CaseLink.case_a_id == case_id, CaseLink.case_b_id == case_id))).all()
    existing_by_pair = {(item.case_a_id, item.case_b_id): item for item in existing}
    created = 0
    weights = {"email": .88, "phone": .82, "handle": .72, "url": .70}
    for pair, shared in grouped.items():
        link = existing_by_pair.get(pair)
        if link is not None and link.status != "suggested":
            continue
        shared_rows, remaining = [], 1.0
        for (entity_type, normalized), entity in shared.items():
            remaining *= 1.0 - weights.get(entity_type, .65)
            shared_rows.append({"id": f"{entity_type}:{normalized}", "type": entity_type, "raw": entity.raw_value, "normalised": normalized, "confidence": entity.confidence})
        score = min(.98, 1.0 - remaining)
        if link is None:
            db.add(CaseLink(case_a_id=pair[0], case_b_id=pair[1], shared_entities=shared_rows, confidence=score, status="suggested", created_by="ai:entity-match-v1"))
            created += 1
        else:
            link.shared_entities, link.confidence = shared_rows, score
    return created
