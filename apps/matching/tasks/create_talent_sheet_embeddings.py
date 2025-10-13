"""
Task for creating embeddings for a TalentSheet in Pinecone.
"""

from typing import Any

from celery import shared_task
from django.apps import apps

from apps.matching.services.talent_sheet_embeddings import (
    generate_enriched_text_for_talent,
    upsert_talent_embeddings,
)
from apps.matching.tasks.common import get_embedding, logger
from apps.resume_processing.services.xml_parser import extract_personal_details


@shared_task(name="apps.matching.tasks.create_talent_sheet_embeddings")
def create_talent_sheet_embeddings(talent_sheet_id: int, **kwargs) -> dict[str, Any]:
    """
    Create and store embeddings for a TalentSheet in Pinecone.

    Process a TalentSheet by extracting key fields, generating embeddings for each section,
    and storing them in Pinecone with rich metadata.

    Args:
        talent_sheet_id: ID of the TalentSheet to process
        **kwargs: Additional keyword arguments (ignored)

    Returns:
        dict: Result containing status and talent_sheet_id
    """
    TalentSheet = apps.get_model("job_seekers", "TalentSheet")

    try:
        talent_sheet = TalentSheet.objects.get(id=talent_sheet_id)
    except TalentSheet.DoesNotExist:
        logger.error("TalentSheet with id %s does not exist.", talent_sheet_id)
        return {
            "status": "error",
            "message": f"TalentSheet with id {talent_sheet_id} does not exist",
        }

    if not talent_sheet.is_published:
        logger.info(
            "Skipping embedding for non-published TalentSheet %s (is_published: %s)",
            talent_sheet_id,
            talent_sheet.is_published,
        )
        return {
            "status": "skipped",
            "message": f"TalentSheet {talent_sheet_id} is not published",
        }

    career_direction_text: str | None = None
    if talent_sheet.promotional_blurb or talent_sheet.ideal_roles:
        promo_text = talent_sheet.promotional_blurb or ""
        ideal_roles_text = talent_sheet.ideal_roles or ""
        career_direction_text = (
            f"{promo_text.strip()}\n\nIdeal roles: {ideal_roles_text.strip()}".strip()
        )

    fields: dict[str, str | None] = {
        "Career Direction": career_direction_text,
        "Skills": talent_sheet.skills,
        "Experience Overview": talent_sheet.experience_overview,
        "Qualifications": talent_sheet.qualifications,
    }

    batch_vectors: list[tuple[str, list[float], dict[str, Any]]] = []

    for section, raw_text in fields.items():
        if not raw_text:
            continue

        enriched_text = generate_enriched_text_for_talent(section, raw_text)
        embedding = get_embedding(enriched_text)

        section_slug = section.lower().replace(" ", "_")
        vector_id = f"talent_{talent_sheet.id}_{section_slug}"

        xml_content = talent_sheet.job_seeker.resume_xml or ""
        candidate_name: str | None = None
        if xml_content:
            try:
                personal_details = extract_personal_details(xml_content)
                candidate_name = personal_details.get("name")
            except Exception:
                candidate_name = None
        job_seeker_user = talent_sheet.job_seeker.user_owner
        job_seeker_name = candidate_name or (
            job_seeker_user.get_full_name() if job_seeker_user else None
        )

        metadata: dict[str, Any] = {
            "talent_sheet_id": talent_sheet.id,
            "section": section,
            "job_seeker_id": talent_sheet.job_seeker.id,
            "job_seeker_name": job_seeker_name,
            "content_preview": (
                raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
            ),
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}
        pool_owner = talent_sheet.job_seeker.candidate_pool
        metadata["pool_id"] = pool_owner.id if pool_owner else 0

        batch_vectors.append((vector_id, embedding, metadata))

        logger.debug(
            "Prepared embedding for TalentSheet %s section '%s' (vector_id=%s)",
            talent_sheet.id,
            section,
            vector_id,
        )

    upsert_talent_embeddings(batch_vectors)

    logger.info(
        "Completed processing embeddings for TalentSheet %s (sections=%d)",
        talent_sheet.id,
        len(batch_vectors),
    )

    # Return the talent_sheet_id for potential chaining
    return {
        "status": "success",
        "talent_sheet_id": talent_sheet.id,
        "sections_processed": len(batch_vectors),
    }
