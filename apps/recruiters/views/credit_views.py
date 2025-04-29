import stripe
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from stripe.error import StripeError  # type: ignore


class CreditsView(LoginRequiredMixin, TemplateView):
    """Display the recruiter's current credits and purchase options."""

    template_name = "recruiters/credits.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = self.request.user.recruiter_profile  # type: ignore[attr-defined]
        context["credits_available"] = profile.credits_available
        context["credits_total"] = profile.credits_total
        # Prepare price options: list of dicts with credits count and Stripe price_id
        context["price_options"] = [
            {"credits": credits, "price_id": settings.STRIPE_PRICE_IDS[credits]}
            for credits in sorted(settings.STRIPE_PRICE_IDS)
        ]
        return context


@login_required
def create_checkout_session(request, credits_amount: int):  # type: ignore[type-arg]
    """Create a Stripe Checkout session for the selected credits bundle and redirect."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    price_id = settings.STRIPE_PRICE_IDS.get(credits_amount)
    if not price_id:
        return redirect("recruiters:credits")

    # Create Checkout Session
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="payment",
        success_url=request.build_absolute_uri(reverse("recruiters:checkout_success"))
        + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse("recruiters:credits")),
        client_reference_id=str(request.user.id),
        metadata={"credits": str(credits_amount)},
    )

    # Redirect to the Checkout session URL
    session_url = session.url or ""
    return redirect(session_url)


class CheckoutSuccessView(LoginRequiredMixin, TemplateView):
    """Handle successful Stripe Checkout redirect, grant credits, and show confirmation."""

    template_name = "recruiters/checkout_success.html"

    def get(self, request, *args, **kwargs):
        session_id = request.GET.get("session_id")
        if not session_id:
            return redirect("recruiters:credits")

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except StripeError:
            return redirect("recruiters:credits")

        # Only grant once and on successful payment
        if getattr(session, "payment_status", "") == "paid":
            metadata = session.metadata or {}
            credits_str = metadata.get("credits", "0")
            credits = int(credits_str)
            # Update recruiter profile atomically
            profile = request.user.recruiter_profile  # type: ignore[attr-defined]
            from apps.recruiters.models import RecruiterProfile

            RecruiterProfile.objects.filter(pk=profile.pk).update(
                credits_total=F("credits_total") + credits,
                credits_available=F("credits_available") + credits,
            )
        return super().get(request, *args, **kwargs)
