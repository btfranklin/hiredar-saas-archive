"""
Task for creating embeddings for a CandidateProfile in Pinecone.
"""

from typing import Any

from celery import shared_task
from django.apps import apps

from apps.matching.services.candidate_embeddings import (
    generate_enriched_text_for_candidate,
    upsert_candidate_embeddings,
)
from apps.matching.tasks.common import get_embedding, logger
from apps.resume_processing.services.xml_parser import extract_personal_details


@shared_task(name="apps.matching.tasks.create_candidate_embeddings")
def create_candidate_embeddings(candidate_profile_id: int, **kwargs) -> dict[str, Any]:
    """
    Create and store embeddings for a CandidateProfile in Pinecone.
    """
    CandidateProfile = apps.get_model("candidates", "CandidateProfile")

    try:
        candidate_profile = CandidateProfile.objects.get(id=candidate_profile_id)
    except CandidateProfile.DoesNotExist:
        logger.error("CandidateProfile with id %s does not exist.", candidate_profile_id)
        return {
            "status": "error",
            "message": f"CandidateProfile with id {candidate_profile_id} does not exist",
        }

    if not candidate_profile.is_published:
        logger.info(
            "Skipping embedding for non-published CandidateProfile %s (is_published: %s)",
            candidate_profile_id,
            candidate_profile.is_published,
        )
        return {
            "status": "skipped",
            "message": f"CandidateProfile {candidate_profile_id} is not published",
        }

    career_direction_text: str | None = None
    if candidate_profile.promotional_blurb or candidate_profile.ideal_roles:
        promo_text = candidate_profile.promotional_blurb or ""
        ideal_roles_text = candidate_profile.ideal_roles or ""
        career_direction_text = (
            f"{promo_text.strip()}\n\nIdeal roles: {ideal_roles_text.strip()}".strip()
        )

    fields: dict[str, str | None] = {
        "Career Direction": career_direction_text,
        "Skills": candidate_profile.skills,
        "Experience Overview": candidate_profile.experience_overview,
        "Qualifications": candidate_profile.qualifications,
    }

    batch_vectors: list[tuple[str, list[float], dict[str, Any]]] = []

    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_candidate(section, raw_text)
        embedding = get_embedding(enriched_text)

        section_slug = section.lower().replace(" ", "_")
        vector_id = f"candidate_{candidate_profile.id}_{section_slug}"

        xml_content = candidate_profile.resume_xml or ""
        candidate_name: str | None = None
        if xml_content:
            try:
                personal_details = extract_personal_details(xml_content)
                candidate_name = personal_details.get("name")
            except Exception:  # pragma: no cover - defensive fallback
                candidate_name = None
        candidate_name = candidate_name or candidate_profile.display_name

        metadata: dict[str, Any] = {
            "candidate_profile_id": candidate_profile.id,
            "section": section,
            "candidate_name": candidate_name,
            "content_preview": (
                raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
            ),
        }
        metadata = {key: value for key, value in metadata.items() if value is not None}
        pool_owner = candidate_profile.pool
        metadata["pool_id"] = pool_owner.id if pool_owner else 0

        batch_vectors.append((vector_id, embedding, metadata))

        logger.debug(
            "Prepared embedding for CandidateProfile %s section '%s' (vector_id=%s)",
            candidate_profile.id,
            section,
            vector_id,
        )

    upsert_candidate_embeddings(batch_vectors)

    logger.info(
        "Completed processing embeddings for CandidateProfile %s (sections=%d)",
        candidate_profile.id,
        len(batch_vectors),
    )

    return {
        "status": "success",
        "candidate_profile_id": candidate_profile.id,
        "sections_processed": len(batch_vectors),
    }

