import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from apps.authentication.models import User
from apps.recruiters.models import RecruiterProfile


class RecruiterCountersTests(TestCase):
    """Test that recruiter profile counters are incremented correctly."""

    def setUp(self):
        # Create a recruiter user and associated profile
        self.user = User.objects.create_user(  # type: ignore[attr-defined]
            email="recruiter@example.com", password="testpass123", user_type="recruiter"
        )
        # RecruiterProfile is auto-created by signal on user creation; fetch it
        self.profile = RecruiterProfile.objects.get(user=self.user)
        # Authenticate client
        self.client = Client()
        self.client.login(email="recruiter@example.com", password="testpass123")

    def test_bulk_upload_increments_counter(self):
        """Uploading a valid ZIP increments the total_bulk_uploads_performed counter."""
        # Ensure initial counter is zero
        self.assertEqual(self.profile.total_bulk_uploads_performed, 0)
        # Create an in-memory ZIP with one PDF file
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, mode="w") as zf:
            zf.writestr("resume1.pdf", b"%PDF-1.4 fake pdf content")
        buffer.seek(0)
        upload_file = SimpleUploadedFile(
            "resumes.zip", buffer.read(), content_type="application/zip"
        )
        # Post to the bulk upload view
        url = reverse("recruiters:bulk_upload_create")
        response = self.client.post(url, {"name": "Test Pool", "zip_file": upload_file})
        # Expect a redirect on success
        self.assertEqual(response.status_code, 302)
        # Refresh profile and check counter
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.total_bulk_uploads_performed, 1)
