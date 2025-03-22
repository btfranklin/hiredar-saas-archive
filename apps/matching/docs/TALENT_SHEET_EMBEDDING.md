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
├── management/commands/
│   └── process_talent_embeddings.py  # CLI tool
└── tests/
    └── test_talent_embeddings.py     # Unit tests
```

## Workflow & Process

### Embedding Generation Flow

When a talent sheet is saved or updated:

1. **Event Detection**: Django signals detect changes to TalentSheet instances
2. **Status Check**: Only "PUBLISHED" talent sheets are processed
3. **Text Extraction**: Key fields (promotional_blurb, skill_overview, ideal_roles) are extracted
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
| Skill Overview | Technical and professional skills | talent_{id}_skill_overview |
| Ideal Roles | Desired positions and roles | talent_{id}_ideal_roles |

#### 3. Metadata Schema

Each vector is stored with detailed metadata for filtering and display:

```python
metadata = {
    "talent_sheet_id": talent_sheet.id,
    "section": section,  # e.g., "Promotional Blurb"
    "job_seeker_id": talent_sheet.job_seeker.id,
    "job_seeker_name": talent_sheet.job_seeker.user.get_full_name(),
    "content_preview": raw_text[:100] + "..." if len(raw_text) > 100 else raw_text
}
```

#### 4. Status-Based Processing

The system responds to talent sheet status changes:

- **PUBLISHED**: Generate and store embeddings
- **WITHDRAWN/INACTIVE**: Remove existing embeddings
- **Deletion**: Remove all associated embeddings

## Integration Points

### Django Signals

```python
@receiver(post_save, sender="job_seekers.TalentSheet")
def handle_talent_sheet_save(sender, instance, created, **kwargs):
    """Process talent sheets based on status."""
    if instance.status == "PUBLISHED":
        async_task("apps.matching.tasks.process_talent_sheet", instance.id)
    elif instance.status in ["WITHDRAWN", "INACTIVE"]:
        async_task("apps.matching.tasks.remove_talent_sheet_embeddings", instance.id)

@receiver(post_delete, sender="job_seekers.TalentSheet")
def handle_talent_sheet_delete(sender, instance, **kwargs):
    """Remove embeddings on deletion."""
    async_task("apps.matching.tasks.remove_talent_sheet_embeddings", instance.id)
```

### Management Command

The system includes a management command for manually processing talent sheets:

```bash
# Process a specific talent sheet
python manage.py process_talent_embeddings --talent_id=123

# Process all published talent sheets
python manage.py process_talent_embeddings --all

# Remove embeddings for talent sheets
python manage.py process_talent_embeddings --talent_id=123 --remove
```

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

## Environment Configuration

Required environment variables:

```bash
# OpenAI settings
OPENAI_API_KEY=your-openai-api-key
OPENAI_EMBEDDING_MODEL=text-embedding-3-large

# Pinecone settings
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX_NAME=job-matcher
PINECONE_PROJECT_NAME=Hiredar
```

## Implementation Notes

### Circular Import Prevention

The system uses Django's `apps.get_model()` to dynamically load models, preventing circular imports:

```python
TalentSheet = apps.get_model('job_seekers', 'TalentSheet')
```

### Modular Design Benefits

1. **Separation of Concerns**: Job opening and talent sheet embedding are independent
2. **Code Reuse**: Common embedding logic is shared via the common module
3. **Testability**: Each module can be tested in isolation
4. **Maintainability**: Changes to one entity type don't affect the other

### Type Annotation

The implementation uses Python 3.12 native type annotations throughout:

```python
def process_talent_sheet(talent_sheet_id: int) -> None:
    """Process a TalentSheet with proper type annotations."""
```

## Testing Strategy

The implementation includes unit tests covering key functionality:

1. **Text Enhancement**: Tests for proper section formatting
2. **Processing Logic**: Tests for the full processing workflow
3. **Embedding Removal**: Tests for proper cleanup of vectors

Tests use mocking to avoid actual API calls during testing.

## Future Considerations

1. **Vector Batching**: For high-volume processing, consider batching multiple embeddings in single API calls
2. **Caching**: Consider caching embeddings for frequently accessed talent sheets
3. **Refresh Strategies**: Implement scheduled refreshes for long-lived talent sheets
4. **Hybrid Search**: Explore combining embedding search with keyword-based filtering
