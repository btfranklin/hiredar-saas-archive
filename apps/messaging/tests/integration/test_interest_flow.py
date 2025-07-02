from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile
from apps.messaging.models import Conversation, Message
from apps.recruiters.models import JobOpening, RecruiterProfile


class InterestFlowTest(TestCase):
    """Integration tests covering interest request lifecycle."""

    def setUp(self) -> None:
        # Users
        self.recruiter_user = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com",
            password="password123",
            user_type="recruiter",
            name="Recruiter Rick",
        )
        self.job_seeker_user = User.objects.create_user(  # type: ignore[attr-defined]
            email="seeker@example.com",
            password="password123",
            user_type="job_seeker",
            name="Seeker Sally",
        )

        # Recruiter profile + job opening
        recruiter_profile = RecruiterProfile.objects.get(user=self.recruiter_user)
        self.job_opening = JobOpening.objects.create(
            recruiter=recruiter_profile,
            title="Backend Engineer",
            description="Great role",
            location="Remote",
            company="Acme",
            status="active",
        )

        # Test clients
        self.client_recruiter = Client()
        self.client_candidate = Client()
        self.client_recruiter.force_login(self.recruiter_user)
        self.client_candidate.force_login(self.job_seeker_user)

        # Ensure the candidate profile has a resume attached so resume-upload
        # middleware allows access to messaging endpoints used in these tests.
        seeker_profile = JobSeekerProfile.objects.get(user_owner=self.job_seeker_user)
        seeker_profile.resume_xml = "<resume />"
        seeker_profile.save(update_fields=["resume_xml"])

    def _create_conversation(self) -> Conversation:
        url = reverse(
            "messaging:conversation_create",
            kwargs={
                "job_id": self.job_opening.pk,
                "recipient_id": self.job_seeker_user.pk,
            },
        )
        response = self.client_recruiter.post(url)
        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.get()
        self.assertEqual(conversation.status, "interest_requested")
        return conversation

    def test_accept_interest_promotes_to_active(self):
        """Candidate clicks Interested -> status candidate_interested, recruiter first message -> active."""
        conversation = self._create_conversation()

        # Candidate responds interested
        respond_url = reverse(
            "messaging:respond_to_interest", kwargs={"pk": conversation.pk}
        )
        resp = self.client_candidate.post(
            respond_url, {"is_interested": "true"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(resp.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, "candidate_interested")

        # Recruiter sends first message
        send_url = reverse("messaging:send_message", kwargs={"pk": conversation.pk})
        resp = self.client_recruiter.post(
            send_url, {"message": "Hello!"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(resp.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, "active")

    def test_decline_sets_status(self):
        conversation = self._create_conversation()
        respond_url = reverse(
            "messaging:respond_to_interest", kwargs={"pk": conversation.pk}
        )
        resp = self.client_candidate.post(
            respond_url, {"is_interested": "false"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(resp.status_code, 200)
        conversation.refresh_from_db()
        self.assertEqual(conversation.status, "candidate_not_interested")

    def test_unread_count_logic(self):
        conversation = self._create_conversation()

        # Recruiter sends a message despite candidate not yet accepted -> should fail
        send_url = reverse("messaging:send_message", kwargs={"pk": conversation.pk})
        response = self.client_recruiter.post(
            send_url, {"message": "Hi"}, HTTP_HX_REQUEST="true"
        )
        self.assertEqual(response.status_code, 400)

        # Candidate accepts interest
        respond_url = reverse(
            "messaging:respond_to_interest", kwargs={"pk": conversation.pk}
        )
        self.client_candidate.post(
            respond_url, {"is_interested": "true"}, HTTP_HX_REQUEST="true"
        )
        conversation.refresh_from_db()

        # Recruiter sends message (now allowed)
        self.client_recruiter.post(
            send_url, {"message": "Welcome!"}, HTTP_HX_REQUEST="true"
        )

        # Job seeker should have 1 unread message
        unread = (
            Message.objects.filter(conversation=conversation, is_read=False)
            .exclude(sender=self.job_seeker_user)
            .count()
        )
        self.assertEqual(unread, 1)

        # Candidate views conversation detail -> messages marked read
        detail_url = reverse(
            "messaging:conversation_detail", kwargs={"pk": conversation.pk}
        )
        self.client_candidate.get(detail_url)
        unread_after = (
            Message.objects.filter(conversation=conversation, is_read=False)
            .exclude(sender=self.job_seeker_user)
            .count()
        )
        self.assertEqual(unread_after, 0)
