"""Case access policy shared by case-scoped endpoints."""


def can_access_case(user: object, case: object) -> bool:
    """Allow case creators and administrators until membership is modeled."""
    return (
        getattr(user, "role", None) == "admin"
        or getattr(user, "id", None) == getattr(case, "created_by", None)
    )
