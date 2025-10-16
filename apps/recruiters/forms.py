from django import forms

from apps.recruiters.models import BulkResumeUpload


class BulkResumeUploadForm(forms.ModelForm):
    """Form to upload a named pool of résumés."""

    class Meta:
        model = BulkResumeUpload
        fields = ["name", "zip_file"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "input input-bordered w-full",
                    "placeholder": "e.g. Summer 2024 Candidates",
                }
            ),
            "zip_file": forms.ClearableFileInput(
                attrs={
                    "class": "file-input file-input-bordered file-input-primary w-full",
                }
            ),
        }
        labels = {
            "name": "Pool Name",
            "zip_file": "ZIP file of résumés (PDF, DOCX, RTF, ODT, TXT)",
        }
