# Talent Sheet Embedding Implementation

This document describes the current implementation of the talent sheet embedding system within the matching app, detailing the modular architecture, workflow, and technical details.

## Architecture Overview

The talent sheet embedding system follows a modular design pattern where each component has a clear responsibility:

1. **Common Utilities**: Shared embedding functionality used across different entity types
2. **Talent Sheet Tasks**: Functions specific to processing talent sheets
3. **Signal Handlers**: Event-based triggers for embedding actions
4. **Management Commands**: Manual tools for processing and administration

This modular approach allows for independent evolution of different entity embedding systems (job openings and talent sheets) while ensuring consistent embedding quality.

## Component Structure

The system is organized into the following files:

```bash
apps/matching/
├── tasks/
│   ├── __init__.py             # Package exports
│   ├── common.py               # Shared utilities
│   ├── talent_sheet_tasks.py   # Talent sheet processing
│   └── job_opening_tasks.py    # Job opening processing
├── signals.py                  # Event handlers
├── management/commands/        # Miscellaneous matching and inspection commands
├── tests/
│   ├── unit/
│   │   ├── test_signals.py
│   │   ├── test_talent_embeddings.py
│   │   └── test_matching.py
│   └── manual/                 # Manual tests (integration and end-to-end)
```

## Workflow & Process

### Embedding Generation Flow

When a talent sheet is saved or updated:

1. **Event Detection**: Django signals detect changes to TalentSheet instances
2. **Status Check**: Only "PUBLISHED" talent sheets are processed
3. **Text Extraction**: Key fields (promotional_blurb, skills, skill_overview, ideal_roles) are extracted
4. **Text Enhancement**: Section context is added to each field using templates
5. **Embedding Generation**: OpenAI's embedding API generates semantic vectors
6. **Vector Storage**: Vectors are stored in Pinecone with rich metadata
7. **Namespace Management**: All talent sheet vectors are stored in the "talent_sheets" namespace

### Data Details and Algorithms

#### 1. Text Processing

Unlike job opening embedding, talent sheet text is already processed by an LLM before reaching the embedding phase. The text enhancement is minimal:

```python
def generate_enriched_text_for_talent(section_name: str, raw_text: str) -> str:
    """Add section context to already-processed talent sheet text."""
    return f"Section: {section_name} | {raw_text.strip()}"
```

This preserves the already optimized text while adding context for semantic search.

#### 2. Field Processing

The system processes these fields from each talent sheet:

| Field | Description | Vector ID Format |
|-------|-------------|------------------|
| Promotional Blurb | High-level candidate description | talent_{id}_promotional_blurb |
| Skills | Pipe-separated raw skills from JobSeekerProfile | talent_{id}_skills |
| Skill Overview | Technical and professional skills summary | talent_{id}_skill_overview |
| Ideal Roles | Desired positions and roles | talent_{id}_ideal_roles |

#### 3. Metadata Schema

Each vector is stored with detailed metadata for filtering and display:

```python
metadata = {
    "talent_sheet_id": talent_sheet.id,
    "section": section,
    "job_seeker_id": talent_sheet.job_seeker.id,
    "job_seeker_name": job_seeker_name,
    "content_preview": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text,
    "pool_id": pool_owner.id if pool_owner else 0,
}
# Remove None values
metadata = {k: v for k, v in metadata.items() if v is not None}
```

#### 4. Status-Based Processing

The system responds to talent sheet status changes:

- **PUBLISHED**: Generate and store embeddings
- **WITHDRAWN/INACTIVE**: Trigger asynchronous tasks `remove_talent_sheet_embeddings` and `remove_talent_sheet_matches`
- **Deletion**: Trigger asynchronous tasks `remove_talent_sheet_embeddings` and `remove_talent_sheet_matches`

## Integration Points

### Django Signals

```python
@receiver(post_save, sender="job_seekers.TalentSheet")
def handle_talent_sheet_save(sender, instance, created, **kwargs):
    """
    Handle TalentSheet save events.

    Process published talent sheets for embeddings, and remove embeddings and matches for unpublished ones.
    """
    # Only process embeddings for published talent sheets
    if instance.is_published:
        transaction.on_commit(
            lambda: async_task(
                "apps.matching.tasks.create_talent_sheet_embeddings",
                instance.id,
            )
        )
    else:
        def _cleanup_unpublished():
            async_task(
                "apps.matching.tasks.remove_talent_sheet_embeddings",
                instance.id,
            )
            async_task(
                "apps.matching.tasks.remove_talent_sheet_matches",
                instance.id,
            )
        transaction.on_commit(_cleanup_unpublished)

@receiver(post_delete, sender="job_seekers.TalentSheet")
def handle_talent_sheet_delete(sender, instance, **kwargs):
    """
    Handle TalentSheet deletion events.

    Remove embeddings and matches when a talent sheet is deleted.
    """
    async_task(
        "apps.matching.tasks.remove_talent_sheet_embeddings",
        instance.id,
    )
    async_task(
        "apps.matching.tasks.remove_talent_sheet_matches",
        instance.id,
    )
```

Talent sheet embeddings are now primarily managed automatically via these Django signals. When a `TalentSheet` is saved with `is_published=True`, the `create_talent_sheet_embeddings` task is triggered. If it's saved with `is_published=False` or deleted, the `remove_talent_sheet_embeddings` task is triggered.

## Pinecone Vector Storage Details

### Namespaces

The system uses distinct namespaces to separate different entity types:

- `talent_sheets`: All talent sheet vectors
- `job_openings`: All job opening vectors (separate system)

### Vector IDs

Vector IDs follow a structured format to ensure uniqueness:

```python
talent_{talent_sheet_id}_{section_slug}
```

Example: `talent_123_promotional_blurb`

## Error Handling

The system implements robust error handling throughout:

1. **API Errors**: Errors from OpenAI or Pinecone are caught and logged
2. **Missing Entities**: Non-existent talent sheets are handled gracefully
3. **Status Validation**: Only appropriate statuses trigger processing
4. **Empty Field Handling**: Empty fields are skipped rather than processed
