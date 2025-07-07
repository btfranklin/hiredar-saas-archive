from .index import HomeView  # noqa: F401 – re-export
from .info import (  # noqa: F401 – re-export for convenience
    AboutView,
    ContactView,
    ManifestoView,
    PrivacyPolicyView,
    RecruiterFeaturesView,
    RecruiterPricingSignupView,
    TermsOfServiceView,
)

__all__ = [
    "HomeView",
    "AboutView",
    "ContactView",
    "PrivacyPolicyView",
    "TermsOfServiceView",
    "RecruiterFeaturesView",
    "RecruiterPricingSignupView",
    "ManifestoView",
]
