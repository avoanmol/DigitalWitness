"""Case access policy shared by case-scoped endpoints."""


def can_access_case(user: object, case: object) -> bool:
    """Reporters can access their own cases; investigation roles can access all cases."""
    role = getattr(user, "role", None)
    if role in {"investigator", "legal", "admin"}:
        return True

    return (
        role == "reporter"
        and getattr(user, "id", None) == getattr(case, "created_by", None)
    )
