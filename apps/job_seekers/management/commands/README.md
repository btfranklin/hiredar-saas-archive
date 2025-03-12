# Job Seekers Management Commands

This directory contains Django management commands for the job seekers app, primarily focused on resume processing functionality.

## Available Commands

### Test Resume Parser

The `test_resume_parser` command allows you to test the resume parsing functionality on a single resume file.

```bash
# Basic usage
python manage.py test_resume_parser /path/to/resume.pdf

# With increased verbosity
python manage.py test_resume_parser /path/to/resume.pdf -v 2
```

This command will:

1. Extract text from the provided PDF
2. Send the text to the LLM API for conversion to structured XML
3. Parse the resulting XML to extract structured data
4. Display the extracted information, such as skills, experience, education, etc.

This is useful for testing changes to the resume processing pipeline and for troubleshooting issues with specific resume formats.

### Batch Ingest Resumes

The `ingest_resumes` command allows you to batch-process multiple resume PDF files to test the resume ingestion pipeline and populate the system with sample data.

```bash
# Basic usage
python manage.py ingest_resumes /path/to/resumes/directory

# With minimal output
python manage.py ingest_resumes /path/to/resumes/directory -v 0

# With detailed output
python manage.py ingest_resumes /path/to/resumes/directory -v 2
```

For each PDF file in the specified directory, the command will:

1. Create a temporary job seeker user with a unique email
2. Process the resume using the same pipeline that would be used in production
3. Update the job seeker's profile with the extracted information
4. Display a summary of the extracted information

### Delete Job Seekers

The `delete_job_seekers` command allows you to delete all job seeker users and their associated data. By default, it only deletes test users (those with emails starting with "test_user_").

```bash
# Delete test users only (interactive confirmation)
python manage.py delete_job_seekers

# Delete test users without confirmation
python manage.py delete_job_seekers --force

# Delete ALL job seekers (including real users)
python manage.py delete_job_seekers --all

# Delete ALL job seekers with detailed output
python manage.py delete_job_seekers --all -v 2
```

This command is useful for:

- Cleaning up test data after testing the resume ingestion pipeline
- Resetting the system to a clean state before batch ingesting new resumes
- Removing old test users that may have accumulated during development

**⚠️ CAUTION:** Using the `--all` flag will delete ALL job seeker users, including any that may have been created by real users. Use with care, especially in production environments.

### List Job Seekers

The `list_job_seekers` command displays a list of all job seeker users with basic information.

```bash
# List all job seekers (shows ID, Name, Username)
python manage.py list_job_seekers

# List only test users
python manage.py list_job_seekers --test-only

# List with detailed information (adds Email, Position, Skills, Experience)
python manage.py list_job_seekers -v 2
```

This command is useful for:

- Quickly seeing all job seekers in the system
- Identifying test users by their usernames (which start with "test_user_")
- Checking the results of batch ingestion
- Verifying which test users exist before deletion

## Verbosity Levels

All commands support Django's standard verbosity levels:

- **0 (minimal)**: Only critical errors and final summaries
- **1 (normal)**: Default level, shows basic progress and success/failure messages
- **2 (verbose)**: Shows detailed information including profile data and processing times
- **3 (very verbose)**: Includes debug information and full stack traces on errors

## Typical Workflows

### Testing Resume Processing

A common workflow when testing the resume processing pipeline:

1. **Clean up old test data**:

   ```bash
   python manage.py delete_job_seekers --force
   ```

2. **Batch ingest a directory of sample resumes**:

   ```bash
   python manage.py ingest_resumes /path/to/sample/resumes -v 2
   ```

3. **Check the results** in the admin interface or via direct database queries.

### Debugging a Specific Resume

When a particular resume isn't being processed correctly:

1. **Test the specific resume**:

   ```bash
   python manage.py test_resume_parser /path/to/problematic/resume.pdf -v 3
   ```

2. **Analyze the output** to identify where the processing fails:
   - Text extraction issues
   - LLM conversion problems
   - XML parsing errors

3. **Fix the issue** in the relevant module and test again.

## Troubleshooting

If you encounter errors when running these commands:

1. **OpenAI API Key**: Make sure the `OPENAI_API_KEY` environment variable is set
2. **PDF Extraction Issues**: Ensure that PDFs are not password protected or corrupted
3. **Import Errors**: Make sure you're running the command with the Django environment properly set
4. **Permissions Issues**: Ensure the command has permission to read from the specified directory
