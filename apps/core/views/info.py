from django.views.generic import TemplateView


class RecruiterAboutView(TemplateView):
    """Display the About Us page for Recruiters."""

    template_name = "core/recruiters/about.html"


class RecruiterContactView(TemplateView):
    """Display the Contact page for Recruiters."""

    template_name = "core/recruiters/contact.html"


class RecruiterPrivacyPolicyView(TemplateView):
    """Display the Privacy Policy page for Recruiters."""

    template_name = "core/recruiters/privacy.html"


class RecruiterTermsOfServiceView(TemplateView):
    """Display the Terms of Service page for Recruiters."""

    template_name = "core/recruiters/terms.html"


class RecruiterFeaturesView(TemplateView):
    """Display the Features marketing page."""

    template_name = "core/recruiters/features.html"


class RecruiterPricingSignupView(TemplateView):
    """Display the Pricing & Signup marketing page."""

    template_name = "core/recruiters/pricing.html"


class JobSeekerContactView(TemplateView):
    """Display the Contact page for Job Seekers with tailored navigation."""

    template_name = "core/job_seekers/contact.html"


class JobSeekerAboutView(TemplateView):
    """Display the About Us page for Job Seekers."""

    template_name = "core/job_seekers/about.html"


class JobSeekerPrivacyPolicyView(TemplateView):
    """Display the Privacy Policy page for Job Seekers."""

    template_name = "core/job_seekers/privacy.html"


class JobSeekerTermsOfServiceView(TemplateView):
    """Display the Terms of Service page for Job Seekers."""

    template_name = "core/job_seekers/terms.html"
