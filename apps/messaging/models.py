"""Models for the messaging app, including conversations, messages, and notifications."""

from typing import TYPE_CHECKING, cast

from django.db import models

from apps.authentication.models import User
from apps.recruiters.models import JobOpening


class Conversation(models.Model):
    """Model for conversations between users"""

    CONVERSATION_STATUS = (
        ("interest_requested", "Interest Requested"),
        ("candidate_interested", "Candidate Interested"),
        ("candidate_not_interested", "Candidate Not Interested"),
        ("active", "Active"),
        ("archived", "Archived"),
    )

    participants = models.ManyToManyField(
        User,
        related_name="conversations",
    )
    job_opening = models.ForeignKey(
        JobOpening,
        on_delete=models.CASCADE,
        related_name="conversations",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=30,
        choices=CONVERSATION_STATUS,
        default="interest_requested",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    id: int  # Add type hint for Django-generated ID field

    def __str__(self) -> str:
        return f"Conversation {self.id}"

    def get_other_participant(self, user: User) -> User:
        """Get the other participant in a conversation"""
        return cast(User, self.participants.exclude(pk=user.pk).first())

    @property
    def other_participant(self) -> User | None:
        """Property accessor for templates to get the other participant without parameters.

        Note: This is used when the conversation has exactly 2 participants and
        returns the first participant (which could be any of the two).
        For specific user-relative lookup, use get_other_participant(user) instead.
        """
        if self.participants.count() == 2:
            return self.participants.first()
        return None


class Message(models.Model):
    """Model for messages within a conversation"""

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    id: int  # Add type hint for Django-generated ID field

    def __str__(self) -> str:
        return f"Message from {self.sender} in {self.conversation}"

    class Meta:
        ordering = ["created_at"]


class Notification(models.Model):
    """Model for user notifications"""

    NOTIFICATION_TYPES = (
        ("message", "New Message"),
        ("match", "New Match"),
        ("application", "New Application"),
        ("system", "System Notification"),
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    content = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    id: int  # Add type hint for Django-generated ID field

    if TYPE_CHECKING:
        # Add stub for Django's dynamically generated method to help type checkers
        def get_notification_type_display(self) -> str: ...

    def __str__(self) -> str:
        # Now we can use the method directly without a type ignore comment
        return f"{self.get_notification_type_display()} for {self.user}"

    class Meta:
        ordering = ["-created_at"]
