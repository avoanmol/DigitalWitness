import re

from .schemas import Entity


EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+91[\s-]?)?[6-9]\d{9}(?!\w)"
)

URL_PATTERN = re.compile(
    r"https?://[^\s]+?(?=[.,!?;:]?(?:\s|$))"
)

HANDLE_PATTERN = re.compile(
    r"(?<!\w)@[A-Za-z0-9_]{3,30}\b"
)


def extract_entities(text: str) -> list[Entity]:
    """Extract basic entities from evidence text using regex."""
    entities: list[Entity] = []

    for match in EMAIL_PATTERN.finditer(text):
        entities.append(
            Entity(
                type="email",
                value=match.group(),
                confidence=1.0,
                snippet=match.group(),
            )
        )

    for match in PHONE_PATTERN.finditer(text):
        entities.append(
            Entity(
                type="phone",
                value=match.group(),
                confidence=1.0,
                snippet=match.group(),
            )
        )

    for match in URL_PATTERN.finditer(text):
        entities.append(
            Entity(
                type="url",
                value=match.group().rstrip(".,!?;:"),
                confidence=1.0,
                snippet=match.group().rstrip(".,!?;:"),
            )
        )

    for match in HANDLE_PATTERN.finditer(text):
        entities.append(
            Entity(
                type="handle",
                value=match.group(),
                confidence=1.0,
                snippet=match.group(),
            )
        )

    return entities