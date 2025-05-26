# Match Analysis Feature

## Overview

The Match Analysis feature provides AI-powered detailed analysis of why a candidate is a good match for a job opening. When a recruiter views a candidate match detail page, the system automatically triggers an LLM analysis if one hasn't been performed yet.

## How It Works

### 1. Automatic Analysis Triggering

When a recruiter visits a candidate match detail page (`/matching/{job_id}/candidates/{candidate_id}/`):

- If `CandidateMatch.is_analyzed` is `False`, the system automatically triggers an async analysis task
- The UI shows a loading state with spinners while analysis is in progress
- The page polls every 3 seconds for updates using HTMX

### 2. LLM Analysis Process

The analysis task (`analyze_candidate_match`) performs the following:

1. **Data Gathering**: Collects comprehensive information about:
   - Job opening details (title, description, requirements, etc.)
   - Candidate talent sheet information (experience, skills, qualifications)
   - Match scores from the vector similarity matching

2. **LLM Processing**: Sends data to o1-mini (reasoning model) with a specialized prompt that focuses on:
   - Specific results and achievements that demonstrate fit
   - Skills, qualifications, and strengths alignment
   - Future performance indicators based on past achievements

3. **Result Storage**: Updates the `CandidateMatch` with:
   - `match_summary`: A compelling 1-2 sentence headline
   - `match_analysis`: Detailed 3-5 paragraph analysis
   - `is_analyzed`: Set to `True` upon completion

### 3. UI Updates

- **Loading State**: Shows spinners and "Analyzing..." messages
- **Complete State**: Displays the AI-generated summary and detailed analysis
- **Polling**: Automatically updates when analysis completes (no page refresh needed)

## Technical Implementation

### Files Created/Modified

- `apps/matching/tasks/analyze_candidate_match.py` - Main analysis task
- `apps/matching/prompts/analyze_candidate_match.prompt.md` - LLM prompt
- `apps/matching/views/candidate_views.py` - Added status endpoint
- `apps/matching/urls.py` - Added analysis status URL
- `apps/matching/templates/matching/partials/analysis_loading.html` - Loading state
- `apps/matching/templates/matching/partials/analysis_complete.html` - Complete state
- `apps/matching/templates/matching/candidate_match_detail.html` - Updated main template
- `hiredar/settings.py` - Added MATCHING_ANALYSIS_MODEL setting

### Key Components

1. **Celery Task**: `analyze_candidate_match(candidate_match_id: int)`
2. **HTMX Endpoint**: `/matching/{job_id}/candidates/{candidate_id}/analysis-status/`
3. **Prompt Template**: Uses promptdown format with hiring manager persona
4. **Database Fields**: Uses existing `is_analyzed`, `match_summary`, `match_analysis` fields

## Usage

### For Recruiters

1. Navigate to any candidate match detail page
2. If analysis hasn't been performed, you'll see loading indicators
3. Wait 10-30 seconds for AI analysis to complete
4. View the detailed "Why This Match?" summary and analysis

### For Developers

```python
# Manually trigger analysis
from apps.matching.tasks.analyze_candidate_match import analyze_candidate_match
analyze_candidate_match.delay(candidate_match_id)

# Check analysis status
match = CandidateMatch.objects.get(id=candidate_match_id)
if match.is_analyzed:
    print(f"Summary: {match.match_summary}")
    print(f"Analysis: {match.match_analysis}")
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM analysis
- `MATCHING_ANALYSIS_MODEL`: Model to use (default: "o4-mini")
- Standard Celery configuration for task processing

### Model Settings

- Uses `o4-mini` reasoning model for enhanced analysis quality
- No custom temperature configuration is needed (fixed for reasoning models)
- Timeout: 60 seconds per analysis
- No system messages supported (reasoning model limitation)

## Error Handling

- Graceful degradation if OpenAI API is unavailable
- Retry logic through Celery's built-in mechanisms
- Fallback to generic match description if analysis fails
- Comprehensive logging for debugging

## Performance Considerations

- Analysis is performed asynchronously to avoid blocking the UI
- Results are cached in the database (no re-analysis unless manually triggered)
- Uses predictable task names to avoid duplicate analysis requests
- Polling stops automatically when analysis completes

## Future Enhancements

- Batch analysis for multiple matches
- Re-analysis triggers when job or candidate data changes significantly
- Analysis quality scoring and feedback mechanisms
- Integration with recruiter workflow tools 