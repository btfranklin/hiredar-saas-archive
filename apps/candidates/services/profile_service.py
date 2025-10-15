"""Services for safely mutating CandidateProfile records."""

from __future__ import annotations

import logging
from typing import Any

from django.db import transaction

from apps.candidates.models import CandidateProfile

logger = logging.getLogger(__name__)


class CandidateProfileService:
    """Utility helpers that wrap CandidateProfile updates with row-level locking."""

    @staticmethod
    @transaction.atomic
    def safe_update_profile_enrichment(
        profile_id: int,
        enrichment_data: dict[str, Any],
    ) -> CandidateProfile:
        """
        Update enrichment-related fields on a candidate profile atomically.

        The provided ``enrichment_data`` must only contain keys that map to fields on
        ``CandidateProfile``. Unknown keys are ignored silently to keep the caller
        resilient across iterative schema changes.
        """
        profile = CandidateProfile.objects.select_for_update().get(pk=profile_id)

        valid_fields: list[str] = []
        for field, value in enrichment_data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)
                valid_fields.append(field)
            else:
                logger.debug(
                    "Ignoring unknown CandidateProfile field '%s' during enrichment update",
                    field,
                )

        if valid_fields:
            profile.save(update_fields=valid_fields + ["updated_at"])
            logger.debug(
                "Updated CandidateProfile %s fields: %s",
                profile_id,
                ", ".join(valid_fields),
            )
        else:
            logger.debug(
                "safe_update_profile_enrichment called for %s without valid fields",
                profile_id,
            )

        return profile

    @staticmethod
    @transaction.atomic
    def safe_update_publication_status(
        profile_id: int,
        *,
        is_published: bool,
    ) -> CandidateProfile:
        """Toggle the publication flag with optimistic locking."""
        profile = CandidateProfile.objects.select_for_update().get(pk=profile_id)
        profile.is_published = is_published
        profile.save(update_fields=["is_published", "updated_at"])
        logger.debug(
            "Set CandidateProfile %s publication status to %s",
            profile_id,
            is_published,
        )
        return profile

    @staticmethod
    @transaction.atomic
    def safe_update_ideal_roles(
        profile_id: int,
        ideal_roles: str,
    ) -> CandidateProfile:
        """Persist ``ideal_roles`` while holding a row lock."""
        profile = CandidateProfile.objects.select_for_update().get(pk=profile_id)
        profile.ideal_roles = ideal_roles
        profile.save(update_fields=["ideal_roles", "updated_at"])
        logger.debug(
            "Updated CandidateProfile %s ideal_roles",
            profile_id,
        )
        return profile

