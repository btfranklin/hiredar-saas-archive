"""Tests for messaging models."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.authentication.models import User
from apps.job_seekers.models import JobSeekerProfile
from apps.messaging.models import Conversation, Message


class ConversationModelTest(TestCase):
    """Test cases for the Conversation model."""

    def setUp(self):
        """Set up test data."""
        # Create test users using create_user method
        self.user1 = User.objects.create_user(  # type: ignore
            email="conv_user1@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User1",
        )
        self.user2 = User.objects.create_user(  # type: ignore
            email="conv_user2@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User2",
        )

        # Get the automatically created profiles
        user_content_type = ContentType.objects.get_for_model(User)
        self.profile1 = JobSeekerProfile.objects.get(
            owner_content_type=user_content_type, owner_object_id=self.user1.id
        )
        self.profile2 = JobSeekerProfile.objects.get(
            owner_content_type=user_content_type, owner_object_id=self.user2.id
        )

        # Create a conversation with User objects (not profiles)
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

    def test_conversation_creation(self):
        """Test that conversation can be created with participants"""
        self.assertEqual(self.conversation.participants.count(), 2)
        self.assertIn(self.user1, self.conversation.participants.all())
        self.assertIn(self.user2, self.conversation.participants.all())

    def test_get_other_participant(self):
        """Test the method to get the other participant in a conversation"""
        other_participant = self.conversation.get_other_participant(self.user1)
        self.assertEqual(other_participant, self.user2)


class MessageModelTest(TestCase):
    """Test cases for the Message model."""

    def setUp(self):
        """Set up test data."""
        # Create test users using create_user method with unique emails
        self.user1 = User.objects.create_user(  # type: ignore
            email="msg_user1@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User1",
        )
        self.user2 = User.objects.create_user(  # type: ignore
            email="msg_user2@example.com",
            password="password123",
            user_type="job_seeker",
            name="Test User2",
        )

        # Get the automatically created profiles
        user_content_type = ContentType.objects.get_for_model(User)
        self.profile1 = JobSeekerProfile.objects.get(
            owner_content_type=user_content_type, owner_object_id=self.user1.id
        )
        self.profile2 = JobSeekerProfile.objects.get(
            owner_content_type=user_content_type, owner_object_id=self.user2.id
        )

        # Create a conversation with User objects (not profiles)
        self.conversation = Conversation.objects.create()
        self.conversation.participants.add(self.user1, self.user2)

        # Create a message
        self.message = Message.objects.create(
            conversation=self.conversation,
            sender=self.user1,
            content="Hello, this is a test message.",
        )

    def test_message_creation(self):
        """Test that message can be created"""
        self.assertEqual(self.message.sender, self.user1)
        self.assertEqual(self.message.content, "Hello, this is a test message.")
        self.assertFalse(self.message.is_read)
