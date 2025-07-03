from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.messaging.models import Conversation
from apps.recruiters.models import JobOpening, RecruiterProfile


class CreditAndCounterTests(TestCase):
    """Verify recruiter credit deductions and counters for conversations/messages."""

    def setUp(self):
        # Recruiter
        self.recruiter_user = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com",
            password="password123",
            user_type="recruiter",
            name="Recruiter Rick",
        )
        self.recruiter_profile: RecruiterProfile = self.recruiter_user.recruiter_profile  # type: ignore[attr-defined]
        self.client_recruiter = Client()
        self.client_recruiter.force_login(self.recruiter_user)

        # Job seeker
        self.job_seeker_user = User.objects.create_user(  # type: ignore[attr-defined]
            email="seeker@example.com",
            password="password123",
            user_type="job_seeker",
            name="Seeker Sally",
        )

        # Job opening
        self.job_opening = JobOpening.objects.create(
            recruiter=self.recruiter_profile,
            title="Backend Engineer",
            description="Great role",
            location="Remote",
            company="Acme",
            status="active",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_conversation(self):
        url = reverse(
            "messaging:conversation_create",
            kwargs={
                "job_id": self.job_opening.pk,
                "recipient_id": self.job_seeker_user.pk,
            },
        )
        return self.client_recruiter.post(url)

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_credit_deducted_and_interest_counter_incremented(self):
        starting_credits = self.recruiter_profile.credits_available

        resp = self._create_conversation()
        self.assertEqual(resp.status_code, 200)

        # Refresh profile
        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.credits_available, starting_credits - 2)
        self.assertEqual(self.recruiter_profile.total_interest_requests_sent, 1)
        self.assertEqual(self.recruiter_profile.total_messages_sent, 0)

    def test_no_additional_deduction_for_existing_conversation(self):
        self._create_conversation()
        credits_after_first = RecruiterProfile.objects.get(
            pk=self.recruiter_profile.pk
        ).credits_available
        interest_after_first = RecruiterProfile.objects.get(
            pk=self.recruiter_profile.pk
        ).total_interest_requests_sent

        # Second attempt should find existing conversation
        resp2 = self._create_conversation()
        self.assertEqual(resp2.status_code, 200)

        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.credits_available, credits_after_first)
        self.assertEqual(
            self.recruiter_profile.total_interest_requests_sent, interest_after_first
        )

    def test_insufficient_credits_blocks_outreach(self):
        # Reduce credits to 1 (< required 2)
        RecruiterProfile.objects.filter(pk=self.recruiter_profile.pk).update(
            credits_available=1
        )
        self.recruiter_profile.refresh_from_db()

        resp = self._create_conversation()
        self.assertEqual(resp.status_code, 400)

        # No change to credits or counters
        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.credits_available, 1)
        self.assertEqual(self.recruiter_profile.total_interest_requests_sent, 0)
        self.assertEqual(Conversation.objects.count(), 0)

    def test_message_increments_message_counter(self):
        # Create conversation first
        self._create_conversation()
        conversation = Conversation.objects.get()
        # Promote conversation to active to satisfy SendMessageView constraints
        conversation.status = "active"
        conversation.save(update_fields=["status"])

        send_url = reverse("messaging:send_message", kwargs={"pk": conversation.pk})
        resp = self.client_recruiter.post(send_url, {"message": "Hello"})
        self.assertEqual(resp.status_code, 200)

        self.recruiter_profile.refresh_from_db()
        self.assertEqual(self.recruiter_profile.total_messages_sent, 1)
        # Credits should remain unchanged after sending message
        self.assertEqual(
            self.recruiter_profile.credits_available,
            self.recruiter_profile.credits_total - 2,
        )
