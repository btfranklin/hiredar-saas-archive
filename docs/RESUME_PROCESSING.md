# Resume Processing Pipeline

This document outlines the resume processing pipeline in the Hiredar application, which converts uploaded PDF resumes into structured data that populates job seeker profiles.

## Overview

The resume processing pipeline follows these steps:

1. User uploads a PDF resume via the web interface
2. The PDF is saved temporarily to the server's storage
3. A background task is queued to process the resume asynchronously
4. The PDF is converted to plain text
5. The text is sent to an LLM (OpenAI API) to generate a structured XML representation
6. The XML representation is parsed to extract key information (skills, experience, etc.)
7. The job seeker's profile is updated with the extracted information
8. The original PDF is deleted to conserve storage space
9. The user is redirected to their dashboard with the updated profile

## Components

### Frontend Components

- **Upload Form**: Located in `apps/job_seekers/templates/job_seekers/profile_create.html`
  - Provides a file input for PDF uploads
  - Uses AJAX to submit the form asynchronously
  - Shows progress indicators during processing

- **Status Polling**: JavaScript function that polls the server for task status
  - Shows processing steps to the user
  - Redirects to the dashboard on completion

### Backend Components

- **Upload View**: `apps/job_seekers/views.py::ResumeUploadView`
  - Handles the initial file upload
  - Validates the file (must be PDF)
  - Saves the file to temporary storage
  - Queues the processing task
  - Returns a response with task ID and status URL

- **Status View**: `apps/job_seekers/views.py::ResumeProcessingTaskProgressView`
  - Checks the status of the queued processing task
  - Returns progress information to the frontend

- **Task Handler**: `apps/job_seekers/tasks.py::handle_resume_upload_task`
  - Entry point for the asynchronous task
  - Orchestrates the processing steps
  - Returns the processing result

- **Resume Processing**: `apps/job_seekers/utils/resume_processing/pipeline.py`
  - Main processing orchestration module
  - Provides both synchronous and asynchronous processing options
  - Calls the necessary utility modules

### Utility Modules

The resume processing utilities are organized in a modular structure:

- **PDF Text Extraction**: `apps/job_seekers/utils/resume_processing/extraction.py`
  - Uses pdfplumber to extract text from PDF files

- **LLM API Interaction**: `apps/job_seekers/utils/resume_processing/llm_processor.py`
  - Sends the extracted text to OpenAI API
  - Prompts the LLM to generate structured XML
  - Returns the XML representation

- **XML Parsing**: `apps/job_seekers/utils/resume_processing/xml_parser.py`
  - `parse_resume_xml`: Main parsing function
  - `extract_skills`: Extracts skills list
  - `extract_most_recent_title`: Finds the most recent job title
  - `calculate_years_experience`: Calculates total years of experience
  - `extract_bio`: Extracts personal summary/bio

- **Profile Updating**: `apps/job_seekers/utils/resume_processing/profile_updater.py`
  - Updates the profile with all extracted data

- **Vector Embeddings** (future): `apps/job_seekers/utils/resume_processing/embeddings.py`
  - Placeholder for future vector embedding generation for semantic search

### Models

- **JobSeekerProfile**: `apps/job_seekers/models.py::JobSeekerProfile`
  - Stores job seeker information
  - Contains the `resume_xml` field that stores the full XML representation
  - Contains fields for skills, experience, education, certifications, and phone number that are populated from the XML

- **ResumeProcessingTaskProgress**: `apps/job_seekers/models.py::ResumeProcessingTaskProgress`
  - Tracks the progress of resume processing tasks
  - Contains fields for task status, progress percentage, and current processing step
  - Used by the UI to display real-time progress updates to users

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM API calls

### Django Settings

- `MEDIA_ROOT`: Directory where uploaded files are stored
- `Q_CLUSTER`: Django Q2 settings for background tasks
- `LOGGING`: Logging configuration for the resume processing pipeline

## Testing

### Management Commands

Two management commands are provided for testing the resume processing functionality:

1. **Diagnose Resume**:
```bash
python manage.py diagnose_resume /path/to/test/resume.pdf
```

This command:
- Extracts text from the provided PDF
- Sends the text to the LLM API
- Parses the resulting XML
- Displays the extracted information

2. **Batch Ingest Resumes**:
```bash
python manage.py ingest_resumes /path/to/resume/directory
```

This command:
- Processes all PDF files in the specified directory
- Creates a test user for each resume
- Extracts and processes each resume
- Updates the corresponding user profiles
- Displays success/failure statistics

Use these commands for testing and populating the system with sample data.

## Flow Diagram

```
apps/job_seekers/views.py::ResumeUploadView.post()
│
├── apps/job_seekers/tasks.py::save_resume_file()
│   └── django.core.files.storage::default_storage.save()
│
└── django_q.tasks::async_task(handle_resume_upload_task)
    │
    └── apps/job_seekers/tasks.py::handle_resume_upload_task()
        │
        └── apps/job_seekers/utils/resume_processing/pipeline.py::process_resume()
            │
            ├── django.core.files.storage::default_storage.path()
            │
            ├── apps/job_seekers/utils/resume_processing/extraction.py::extract_text_from_pdf()
            │   └── pdfplumber::open() and extract_text()
            │
            ├── apps/job_seekers/utils/resume_processing/llm_processor.py::convert_text_to_xml()
            │   └── requests::post() to OpenAI API
            │
            ├── apps/job_seekers/utils/resume_processing/xml_parser.py::parse_resume_xml()
            │
            ├── apps/job_seekers/utils/resume_processing/profile_updater.py::update_profile()
            │
            └── django.core.files.storage::default_storage.delete()
```

## XML Data Extraction

The LLM generates a structured XML representation of the resume that includes:

- Personal information (name, email, phone, location, summary)
- Skills list
- Work experience (job titles, companies, dates, descriptions)
- Education (institutions, degrees, dates)
- Certifications (name, issuing organization, dates)

This XML is then parsed to extract relevant information for the JobSeekerProfile, including:
- Professional summary for the `professional_summary` field
- Skills list for the `skills` field
- Experience details for the `experience` field
- Education history for the `education` field
- Certification information for the `certifications` field 
- Phone number for the `phone` field
- Location for the User's `location` field

### Date Formatting

The extracted date information from the XML is formatted consistently across different sections:

- **Experience Dates**:
  - For jobs with both start and end dates: `Dates: [StartDate] - [EndDate]`
  - For current positions: `Dates: [StartDate] - Present`
  - For jobs with only start date: `Start Date: [StartDate]`
  - For jobs with only end date: `End Date: [EndDate]`

- **Education Dates**:
  - For education with both start and end dates: `Dates: [StartDate] - [EndDate]`
  - For education with only start date: `Start Date: [StartDate]`
  - For education with only end date: `End Date: [EndDate]`

- **Certification Dates**:
  - For certifications with a single date: `Date: [Date]`
  - For certifications with both start and end dates: `Dates: [StartDate] - [EndDate]`
  - For certifications with only start date: `Start Date: [StartDate]`
  - For certifications with only end date: `End Date: [EndDate]`

This consistent date formatting improves readability of the extracted information in the job seeker profile and provides a clear temporal context for each experience, education, and certification entry.
