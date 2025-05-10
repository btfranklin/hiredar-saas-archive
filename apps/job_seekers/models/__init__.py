# This package aggregates the job_seekers models split into submodules
from .profile import CandidatePool, JobSeekerProfile
from .talent import RoleRecommendation, TalentSheet

__all__ = [
    "CandidatePool",
    "JobSeekerProfile",
    "RoleRecommendation",
    "TalentSheet",
]
