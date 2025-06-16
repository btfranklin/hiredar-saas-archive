from django.views.generic import TemplateView


class AboutView(TemplateView):
    """Display the About Us page."""

    template_name = "core/about.html"


class ContactView(TemplateView):
    """Display the Contact page."""

    template_name = "core/contact.html"


class PrivacyPolicyView(TemplateView):
    """Display the Privacy Policy page."""

    template_name = "core/privacy.html"


class TermsOfServiceView(TemplateView):
    """Display the Terms of Service page."""

    template_name = "core/terms.html"


# Marketing pages


class FeaturesView(TemplateView):
    """Display the Features marketing page."""

    template_name = "core/features.html"


class PricingSignupView(TemplateView):
    """Display the Pricing & Signup marketing page."""

    template_name = "core/pricing.html"
