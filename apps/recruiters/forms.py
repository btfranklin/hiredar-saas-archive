from django import forms

from apps.recruiters.models import BulkResumeUpload


class BulkResumeUploadForm(forms.ModelForm):
    """Form to upload a named pool of resumes."""

    class Meta:
        model = BulkResumeUpload
        fields = ["name", "zip_file"]
