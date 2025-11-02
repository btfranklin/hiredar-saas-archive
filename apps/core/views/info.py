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


class HowItWorksView(TemplateView):
    """Display the recruiter-facing How It Works deep dive page."""

    template_name = "core/how_it_works.html"

