"""Tests for messaging models."""

from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile
from apps.messaging.models import Conversation, Message


class ConversationModelTest(TestCase):
    """Test cases for the Conversation model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(  # type: ignore[attr-defined]
            email="conv_user1@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User1",
        )
        self.user2 = User.objects.create_user(  # type: ignore[attr-defined]
            email="conv_user2@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User2",
        )

        # Fetch the automatically created profiles
        self.profile1 = JobSeekerProfile.objects.get(user_owner=self.user1)
        self.profile2 = JobSeekerProfile.objects.get(user_owner=self.user2)

        # Create a conversation with participants
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

    def test_conversation_creation(self):
        """Conversation should start with two participants."""
        self.assertEqual(self.conversation.participants.count(), 2)
        self.assertIn(self.user1, self.conversation.participants.all())
        self.assertIn(self.user2, self.conversation.participants.all())

    def test_get_other_participant(self):
        """Should return the other participant correctly."""
        other = self.conversation.get_other_participant(self.user1)
        self.assertEqual(other, self.user2)


class MessageModelTest(TestCase):
    """Test cases for the Message model."""

    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(  # type: ignore[attr-defined]
            email="msg_user1@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User1",
        )
        self.user2 = User.objects.create_user(  # type: ignore[attr-defined]
            email="msg_user2@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User2",
        )

        # Fetch profiles
        self.profile1 = JobSeekerProfile.objects.get(user_owner=self.user1)
        self.profile2 = JobSeekerProfile.objects.get(user_owner=self.user2)

        # Create conversation and message
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Hello, this is a test message.",
        )

    def test_message_creation(self):
        """Message fields should match and be unread by default."""
        self.assertEqual(self.message.sender, self.user1)
        self.assertEqual(self.message.content, "Hello, this is a test message.")
        self.assertFalse(self.message.is_read)
