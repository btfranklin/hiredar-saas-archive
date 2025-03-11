# Hiredar Scripts

This directory contains utility scripts for the Hiredar application.

## Resume Ingestion Script

The `ingest_resumes.py` script allows you to batch-process multiple resume PDF files to test the resume ingestion pipeline and populate the system with sample data.

### Prerequisites

- Python 3.12
- Running Django app with all dependencies installed
- OpenAI API key configured in the environment variables or in settings

### Usage

```bash
# Basic usage
pdm run ./scripts/ingest_resumes.py /path/to/resumes/directory

# Enable verbose output
pdm run ./scripts/ingest_resumes.py /path/to/resumes/directory --verbose
```

### How It Works

For each PDF file in the specified directory, the script will:

1. Create a temporary job seeker user with a unique email
2. Process the resume using the same pipeline that would be used in production
3. Update the job seeker's profile with the extracted information
4. Display a summary of the extracted information

### Example Output

```
Found 3 resume files to process

[1/3] Processing: resume1.pdf
  - Extracting text from PDF...
  - Converting to structured XML using LLM...
  - Extracting information and updating profile...
  - SUCCESS: Profile updated successfully
✅ Successfully processed resume for test_user_1_a1b2c3d4@example.com
  - Current position: Software Engineer
  - Years of experience: 5
  - Skills: Python, Django, JavaScript, SQL, AWS...

[2/3] Processing: resume2.pdf
  - Extracting text from PDF...
  - Converting to structured XML using LLM...
  - Extracting information and updating profile...
  - SUCCESS: Profile updated successfully
✅ Successfully processed resume for test_user_2_e5f6g7h8@example.com
  - Current position: Data Scientist
  - Years of experience: 3
  - Skills: Python, R, SQL, Machine Learning, TensorFlow...

[3/3] Processing: resume3.pdf
  - Extracting text from PDF...
  - ERROR: Could not extract text from PDF
❌ Failed to process resume for test_user_3_i9j0k1l2@example.com

==================================================
SUMMARY: Processed 3 resumes
SUCCESS: 2 resumes
FAILURE: 1 resumes
==================================================
```

### Troubleshooting

If you encounter errors when running the script:

1. **OpenAI API Key**: Make sure the `OPENAI_API_KEY` environment variable is set
2. **PDF Extraction Issues**: Ensure that PDFs are not password protected or corrupted
3. **Import Errors**: Make sure you're running the script with the Django environment properly set
4. **Permissions Issues**: Ensure the script has permission to read from the specified directory

### Best Practices

For testing purposes, create a directory of sample resumes with a variety of formats and content to thoroughly test the ingestion pipeline. 