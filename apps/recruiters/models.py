from django.db import models

from apps.authentication.models import User


class RecruiterProfile(models.Model):
    """Extended profile for recruiters"""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="recruiter_profile",
        limit_choices_to={"user_type": "recruiter"},
    )

    # Subscription status
    is_subscribed = models.BooleanField(default=False)
    subscription_tier = models.CharField(
        max_length=20,
        choices=(
            ("basic", "Basic"),
            ("professional", "Professional"),
            ("enterprise", "Enterprise"),
        ),
        default="basic",
    )

    def __str__(self) -> str:
        return f"Recruiter: {self.user.email}"
