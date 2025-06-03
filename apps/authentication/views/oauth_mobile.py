from typing import cast
from uuid import uuid4  # for generating random passwords

import requests
from django.conf import settings
from django.contrib.auth import login
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView, View

from apps.authentication.models import User, UserManager


class LinkedInMobileRedirectView(TemplateView):
    """
    Serves a tiny HTML file that deep-links into the LinkedIn app.
    """

    template_name = "authentication/linkedin_mobile.html"


class LinkedInMobileFinishView(TemplateView):
    """
    Serves a tiny HTML file that catches the deep-link callback and finishes login.
    """

    template_name = "authentication/linkedin_mobile_finish.html"


@method_decorator(csrf_exempt, name="dispatch")
class LinkedInMobileFinishAPI(View):
    """
    API endpoint to exchange the LinkedIn OAuth code for an access token,
    fetch user info, create or lookup a local user, and log them in.
    """

    def post(self, request: HttpRequest):
        try:
            body = request.body.decode("utf-8")
            import json

            data = json.loads(body)
            code = data.get("code")
            code_verifier = data.get("code_verifier")
            user_type = data.get("user_type")
            if not code or not code_verifier:
                return HttpResponseBadRequest("Missing code or code_verifier")
            token_resp = requests.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.LI_MOBILE_REDIRECT,
                    "client_id": settings.LI_CLIENT_ID,
                    "code_verifier": code_verifier,
                    "client_secret": settings.LI_CLIENT_SECRET,
                },
                timeout=10,
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("access_token")
            # Fetch LinkedIn profile info
            profile_resp = requests.get(
                "https://api.linkedin.com/v2/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            profile_resp.raise_for_status()
            profile_data = profile_resp.json()
            # Fetch LinkedIn email
            email_resp = requests.get(
                "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10,
            )
            email_resp.raise_for_status()
            email_data = email_resp.json()
            email = email_data["elements"][0]["handle~"]["emailAddress"]
            # Lookup existing user or create a new one via create_user (generates username)
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                random_password = uuid4().hex
                # Use UserManager.create_user for proper username generation
                user_manager = cast(UserManager, User.objects)
                user = user_manager.create_user(
                    email=email,
                    password=random_password,
                    user_type=user_type or "recruiter",
                )
            # Update user's name if available (for both new and existing)
            first_name = profile_data.get("localizedFirstName") or ""
            last_name = profile_data.get("localizedLastName") or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                user.name = full_name
                user.save(update_fields=["name"])
            # Assign backend attribute dynamically to avoid linter errors and allow login
            setattr(user, "backend", settings.AUTHENTICATION_BACKENDS[0])
            login(request, user)
            return JsonResponse({"status": "ok"})
        except Exception as e:
            import logging

            logging.exception("LinkedIn mobile finish error")
            return JsonResponse({"error": str(e)}, status=500)
