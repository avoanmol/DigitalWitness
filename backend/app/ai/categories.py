"""Reporter-selected investigation focus labels; labels do not imply a finding."""

INVESTIGATION_CATEGORIES = (
    "cyberstalking_bullying",
    "blackmail_threatening",
    "intimate_image_abuse",
    "defamation_morphing",
    "fake_profile_impersonation",
)

INVESTIGATION_CATEGORY_GUIDANCE = {
    "cyberstalking_bullying": "Repeated unwanted contact, monitoring, following, or intimidation.",
    "blackmail_threatening": "Coercion, threats, or demands involving money, action, or exposure.",
    "intimate_image_abuse": "Threatened or non-consensual distribution of intimate imagery; never infer consent.",
    "defamation_morphing": "Targeted false factual claims or alleged alteration of imagery; text/image inspection cannot authenticate a file.",
    "fake_profile_impersonation": "A profile allegedly pretending to be a real person; distinguish disclosed parody or fictional accounts when evidence permits.",
}


def clean_investigation_categories(values: list[str] | None) -> list[str]:
    selected = list(dict.fromkeys(values or []))
    if set(selected) - set(INVESTIGATION_CATEGORIES):
        raise ValueError("One or more investigation categories are invalid.")
    return selected
