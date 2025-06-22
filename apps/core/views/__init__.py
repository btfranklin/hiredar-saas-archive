__all__ = [
    "HomeView",
    # Recruiter marketing/info views
    "RecruiterAboutView",
    "RecruiterContactView",
    "RecruiterPrivacyPolicyView",
    "RecruiterTermsOfServiceView",
    "RecruiterFeaturesView",
    "RecruiterPricingSignupView",
    # Job-seeker marketing/info views
    "JobSeekerAboutView",
    "JobSeekerContactView",
    "JobSeekerPrivacyPolicyView",
    "JobSeekerTermsOfServiceView",
]

from .index import HomeView  # noqa: F401 – re-export

# Import recruiter-side views
from .info import (  # noqa: F401 – re-export for convenience; Job seeker views
    JobSeekerAboutView,
    JobSeekerContactView,
    JobSeekerPrivacyPolicyView,
    JobSeekerTermsOfServiceView,
    RecruiterAboutView,
    RecruiterContactView,
    RecruiterFeaturesView,
    RecruiterPricingSignupView,
    RecruiterPrivacyPolicyView,
    RecruiterTermsOfServiceView,
)
