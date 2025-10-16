"""
Legacy facade for resume-processing services.

All concrete implementations now live under ``apps.candidates.services`` so we
import and re-export that package here for backward compatibility while the
``resume_processing`` app is phased out.
"""

from importlib import import_module
import sys

resume_processing = import_module("apps.candidates.services.resume_processing")
sys.modules[__name__ + ".resume_processing"] = resume_processing

__all__ = ["resume_processing"]
