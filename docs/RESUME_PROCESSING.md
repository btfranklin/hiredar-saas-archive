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
  - Contains fields for skills, experience, etc. that are populated from the XML

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

1. **Test Resume Parser**:
```bash
python manage.py test_resume_parser /path/to/test/resume.pdf
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
        └── apps/job_seekers/utils/resume_processing/pipeline.py::process_resume_async()
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

## Code Examples

### Initiating resume processing

```python
# In views.py
from django_q.tasks import async_task
from apps.job_seekers.tasks import handle_resume_upload_task

def resume_upload_handler(request):
    # ... handle file upload ...
    
    # Queue the processing task
    task_id = async_task(
        handle_resume_upload_task,
        user_id=request.user.id,
        resume_path=saved_file_path,
        hook='apps.job_seekers.tasks.handle_resume_processing_complete'
    )
    
    return task_id
```

### Processing pipeline

```python
# In apps/job_seekers/utils/resume_processing/pipeline.py
def process_resume_async(user_id: int, resume_path: str) -> dict:
    """Process a resume asynchronously and return structured data."""
    
    # Get file path from storage
    file_path = default_storage.path(resume_path)
    
    # Extract text from PDF
    resume_text = extract_text_from_pdf(file_path)
    
    # Convert to structured XML via LLM
    resume_xml = convert_text_to_xml(resume_text)
    
    # Parse the XML into structured data
    resume_data = parse_resume_xml(resume_xml)
    
    # Update the user's profile with the extracted data
    profile = update_profile(user_id, resume_data)
    
    # Clean up - delete the temporary file
    default_storage.delete(resume_path)
    
    return resume_data
```

### Extracting text from PDF

```python
# In apps/job_seekers/utils/resume_processing/extraction.py
import pdfplumber

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text(x_tolerance=1) or ""
                text += page_text + "\n\n"
        return text.strip()
    except Exception as e:
        logging.error(f"Error extracting text from PDF: {e}")
        raise
```

### Converting resume text to structured XML

```python
# In apps/job_seekers/utils/resume_processing/llm_processor.py
import os
import requests
import logging
from typing import Optional

def convert_text_to_xml(resume_text: str) -> str:
    """Convert plain text resume to structured XML using OpenAI API."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
            
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gpt-4-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that processes resumes..."
                    },
                    {
                        "role": "user",
                        "content": f"Convert this resume to XML format:\n\n{resume_text}"
                    }
                ],
                "temperature": 0.2
            },
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logging.error(f"Error calling OpenAI API: {e}")
        raise
```

### Parsing XML into structured data

```python
# In apps/job_seekers/utils/resume_processing/xml_parser.py
from bs4 import BeautifulSoup
import logging
from typing import Dict, List, Any

def parse_resume_xml(xml_content: str) -> dict:
    """Parse resume XML into structured data."""
    try:
        soup = BeautifulSoup(xml_content, 'xml')
        if not soup.resume:
            raise ValueError("Invalid XML format: No resume tag found")
            
        # Initialize result structure
        result = {
            "personal_info": extract_personal_info(soup),
            "skills": extract_skills(soup),
            "experience": extract_experience(soup),
            "education": extract_education(soup),
            "summary": extract_summary(soup)
        }
        
        return result
    except Exception as e:
        logging.error(f"Error parsing resume XML: {e}")
        raise

def extract_skills(soup: BeautifulSoup) -> List[str]:
    """Extract skills from the resume XML."""
    skills_section = soup.find('skills')
    if not skills_section:
        return []
        
    skills = []
    for skill in skills_section.find_all('skill'):
        if skill.string:
            skills.append(skill.string.strip())
    return skills

def extract_summary(soup: BeautifulSoup) -> str:
    """Extract the professional summary from the resume XML."""
    summary_section = soup.find('summary')
    if summary_section and summary_section.string:
        return summary_section.string.strip()
    return ""
```

### Updating user profile with resume data

```python
# In apps/job_seekers/utils/resume_processing/profile_updater.py
from apps.job_seekers.models import JobSeekerProfile
from django.contrib.auth.models import User
import logging

def update_profile(user_id: int, resume_data: dict) -> JobSeekerProfile:
    """Update user profile with extracted resume data."""
    try:
        user = User.objects.get(id=user_id)
        profile, created = JobSeekerProfile.objects.get_or_create(user=user)
        
        # Update skills
        if resume_data.get("skills"):
            profile.skills = resume_data["skills"]
            
        # Update job title from most recent experience
        if resume_data.get("experience") and len(resume_data["experience"]) > 0:
            most_recent = resume_data["experience"][0]  # Assuming sorted by recency
            profile.current_title = most_recent.get("title", "")
            
        # Update summary/bio
        if resume_data.get("summary"):
            profile.bio = resume_data["summary"]
            
        # Calculate total experience
        if resume_data.get("experience"):
            profile.years_experience = calculate_total_experience(resume_data["experience"])
            
        profile.save()
        return profile
    except User.DoesNotExist:
        logging.error(f"User with ID {user_id} not found")
        raise
    except Exception as e:
        logging.error(f"Error updating profile: {e}")
        raise
        
def calculate_total_experience(experiences: List[dict]) -> float:
    """Calculate total years of experience from experience entries."""
    # Implementation details...
    return total_years 