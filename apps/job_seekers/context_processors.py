from apps.job_seekers.services import ProfileManager


def personal_tagline(request):
    """Return the personal tagline for authenticated job seeker users.

    This makes the ``personal_tagline`` variable available globally to templates
    so that shared UI fragments (e.g. job seeker sidebar) don't need every view
    to duplicate context preparation logic.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    if getattr(user, "user_type", None) != "job_seeker":
        return {}

    profile = ProfileManager.get_profile_for_user(user)
    if not profile:
        return {"personal_tagline": "Job Seeker"}

    tagline = profile.personal_tagline or "Job Seeker"
    return {"personal_tagline": tagline}
