from django.views.generic import TemplateView


class AboutView(TemplateView):
    """Universal About Us page for all anonymous visitors."""

    template_name = "core/about.html"


class ContactView(TemplateView):
    """Universal Contact page for all anonymous visitors."""

    template_name = "core/contact.html"


class PrivacyPolicyView(TemplateView):
    """Universal Privacy Policy page."""

    template_name = "core/privacy.html"


class TermsOfServiceView(TemplateView):
    """Universal Terms of Service page."""

    template_name = "core/terms.html"


class RecruiterFeaturesView(TemplateView):
    """Display the recruiter-focused Features marketing page."""

    template_name = "core/recruiters/features.html"


class RecruiterPricingSignupView(TemplateView):
    """Display the Pricing & Signup marketing page."""

    template_name = "core/recruiters/pricing.html"


class JobSeekerFeaturesView(TemplateView):
    """Display the job-seeker-focused Features marketing page."""

    template_name = "core/job_seekers/features.html"
