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

- **Status View**: `apps/job_seekers/views.py::TaskStatusView`
  - Checks the status of the queued processing task
  - Returns progress information to the frontend

- **Task Handler**: `apps/job_seekers/tasks.py::handle_resume_upload_task`
  - Entry point for the asynchronous task
  - Orchestrates the processing steps
  - Returns the processing result

- **Resume Processing**: `apps/job_seekers/tasks.py::process_resume`
  - Main processing function
  - Calls the necessary utility functions
  - Updates the job seeker profile
  - Handles cleanup

### Utility Modules

- **PDF Text Extraction**: `apps/job_seekers/utils/resume_parser.py::extract_text_from_pdf`
  - Uses pdfplumber to extract text from PDF files

- **LLM API Interaction**: `apps/job_seekers/utils/llm_api.py::convert_text_resume_to_xml`
  - Sends the extracted text to OpenAI API
  - Prompts the LLM to generate structured XML
  - Returns the XML representation

- **XML Parsing**: Various functions in `apps/job_seekers/utils/resume_parser.py`
  - `extract_skills_from_xml`: Extracts skills list
  - `extract_most_recent_title`: Finds the most recent job title
  - `calculate_years_experience`: Calculates total years of experience
  - `extract_bio`: Extracts personal summary/bio
  - `update_profile_from_xml`: Updates the profile with all extracted data

### Models

- **JobSeekerProfile**: `apps/job_seekers/models.py::JobSeekerProfile`
  - Stores job seeker information
  - Contains the `resume_xml` field that stores the full XML representation
  - Contains fields for skills, experience, etc. that are populated from the XML

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for LLM API calls

### Django Settings

- `MEDIA_ROOT`: Directory where uploaded files are stored
- `Q_CLUSTER`: Django Q2 settings for background tasks
- `LOGGING`: Logging configuration for the resume processing pipeline

## Testing

### Management Command

A management command is provided for testing the resume parsing functionality:

```bash
python manage.py test_resume_parser /path/to/test/resume.pdf
```

This command:
1. Extracts text from the provided PDF
2. Sends the text to the LLM API
3. Parses the resulting XML
4. Displays the extracted information

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
        └── apps/job_seekers/tasks.py::process_resume()
            │
            ├── django.core.files.storage::default_storage.path()
            │
            ├── apps/job_seekers/utils/resume_parser.py::extract_text_from_pdf()
            │   └── pdfplumber::open() and extract_text()
            │
            ├── apps/job_seekers/utils/llm_api.py::convert_text_resume_to_xml()
            │   └── requests::post() to OpenAI API
            │
            ├── apps/job_seekers/utils/resume_parser.py::update_profile_from_xml()
            │   │
            │   ├── apps/job_seekers/utils/resume_parser.py::extract_skills_from_xml()
            │   │
            │   ├── apps/job_seekers/utils/resume_parser.py::extract_most_recent_title()
            │   │
            │   ├── apps/job_seekers/utils/resume_parser.py::calculate_years_experience()
            │   │
            │   └── apps/job_seekers/utils/resume_parser.py::extract_bio()
            │
            └── django.core.files.storage::default_storage.delete()
```

## XML Data Extraction

The LLM generates a structured XML representation of the resume that includes:
- Personal information (name, email, phone, location, summary)
- Skills list
- Work experience (job titles, companies, dates, descriptions)
- Education (institutions, degrees, dates)
- Certifications and other achievements

This XML is then parsed to extract relevant information for the JobSeekerProfile.

## Future Improvements (TODOs)

### Data Model Enhancements

- [ ] Create separate models for Experience, Education, and Skills 
- [ ] Create relationships between these models and JobSeekerProfile
- [ ] Update the parser to create and link these model instances

### LLM Integration Improvements

- [ ] Add fallback mechanisms for API failures
- [ ] Implement rate limiting and retry logic
- [ ] Consider alternative LLM providers or self-hosted models
- [ ] Fine-tune the prompt for better information extraction

### User Experience Enhancements

- [ ] Allow users to correct/verify extracted information
- [ ] Add a preview step before finalizing the profile
- [ ] Support for resume versioning (keeping history of uploaded resumes)
- [ ] Add visual indicators of which information was extracted from resume

### Performance Optimizations

- [ ] Implement caching for repeated API calls
- [ ] Add proper monitoring and instrumentation
- [ ] Optimize the XML parsing for large documents

### Additional Features

- [ ] Support for other file types (DOCX, TXT, etc.)
- [ ] Add resume scoring functionality
- [ ] Extract more detailed skills information (proficiency levels, years used)
- [ ] Implement job-matching algorithms based on extracted skills

### Security Enhancements

- [ ] Add additional validation for uploaded files
- [ ] Implement proper encryption for stored resumes and extracted data
- [ ] Add audit logging for resume uploads and processing

## Troubleshooting

### Common Issues

1. **PDF Extraction Fails**
   - Ensure the PDF is not password-protected
   - Check if the PDF contains actual text (not just images)
   - Try using OCR if the PDF contains scanned images

2. **LLM API Issues**
   - Verify the API key is valid and has sufficient credits
   - Check network connectivity to the API endpoint
   - Ensure the request payload is not too large

3. **Task Queue Problems**
   - Verify Django Q2 is properly configured and running
   - Check database connectivity for task storage
   - Look for task-specific errors in the logs 