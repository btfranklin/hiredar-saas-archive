# Hiredar Application Structure

This document describes the structure and organization of the Hiredar application to help new developers understand the codebase.

## Overview

Hiredar is a job matching platform that connects job seekers with recruiters using AI-powered matching algorithms. The application follows a modular Django architecture with separate apps for different functional areas. This document provides an overview of the codebase organization to help you navigate and understand the application.

> **Quick orientation for LLMs** – If you are a language model reading this file, start with the bullet-point "Cheat Sheet" below; then dive into the per-app sections only as needed.  Human readers may wish to do the same.

## Cheat Sheet (TL;DR)

- **Core Django apps**: `authentication`, `job_seekers`, `recruiters`, `matching`, `messaging`, **new** `resume_processing` (background parsing of resumes).
- **Primary user types**: *job seeker* and *recruiter* (custom `User.user_type`).
- **Key models**: `JobSeekerProfile`, `RecruiterProfile`, `JobOpening`, `TalentSheet`, `CandidateMatch`.
- **Async engine**: Celery; see `apps/resume_processing/tasks/` for task orchestration and `docs/SCHEDULED_TASKS.md` for periodic jobs.
- **Front-end stack**: Tailwind + DaisyUI, HTMX for interactivity.
- **Python 3.12 typing conventions**: built-ins (`list`, `dict`) and `| None` instead of `Optional`.
- **Recruiter monetization**: Recruiters use a credit-based system. Credits are purchased in bundles via Stripe and are required for premium actions (e.g., resume processing). No subscriptions or tiers exist.

## Application Architecture

The application is built using Django 5.2+ and follows a modular approach with the following key components:

- **Django project**: The main `hiredar` project configuration
- **Apps**: Separate Django apps for different functional areas
- **Templates**: HTML templates organized within each app
- **Static files**: CSS, JavaScript, and images
- **Media files**: User-uploaded content like resumes

## Apps Structure

The application is divided into the following apps:

### Core App (`apps/core`)

Handles global templates and core functionality:

- **Models**: No specific models
- **Views**:
  - `HomeView`: View for rendering the home page
- **Templates**:
  - `base.html`: The global base template extended by all pages
  - `core/`: Core-specific templates
  - `authentication/`: Custom authentication templates
  - `socialaccount/`: Django-allauth social account templates
- **URLs**:
  - `/`: Home page and other core routes

### Authentication App (`apps/authentication`)

Handles user authentication, user types, and base user profile:

- **Models**:
  - `User`: Custom user model with email authentication
  - `UserManager`: Custom manager for user creation and management
- **Views**:
  - `auth_views.py`:
    - `JobSeekerSignupView`: Handles job seeker registration
    - `RecruiterSignupView`: Handles recruiter registration
    - `CustomLoginView`: Handles user login with email
    - `CustomLogoutView`: Handles user logout
  - `account_views.py`: Account management views
- **Forms**:
  - `CustomAuthenticationForm`: Form for email-based authentication
- **Signals**:
  - Signal handlers for profile creation when a user is created
- **Adapters**:
  - `AccountAdapter`: Custom adapter for allauth integration
- **Templates**: Authentication-related templates
- **URLs**:
  - `/auth/login/`: User login
  - `/auth/logout/`: User logout
  - `/auth/signup/job-seeker/`: Job seeker registration
  - `/auth/signup/recruiter/`: Recruiter registration

### Job Seekers App (`apps/job_seekers`)

Manages job seeker–specific functionality:

- **Models**:
  - `JobSeekerProfile`: Extended profile for job seekers including skills, experience, education, certifications, contact information, and social media links
  - `RoleRecommendation`: Career recommendations for job seekers based on their skills and experience
  - `TalentSheet`: AI-generated talent sheet for job seekers in the talent pool
  - `UploadedResumePool`: Represents a batch of resumes uploaded by a recruiter for a specific job opening
- **Views**:
  - Organized in subdirectories for maintainability:
    - `dashboard_views.py`: Dashboard and role recommendation views
    - `job_seeker_profile_views.py`: Profile, resume view, and settings
    - `resume_processing_views.py`: Resume upload and processing views (`ResumeUploadView`, `ResumeProcessingTaskProgressView`, `ProfileCreateView`)
    - `api_views.py`: API endpoints for HTMX and JSON responses (`ToggleRoleInterestView`, `ToggleTalentPoolView`, `TalentPoolStatusView`)
    - `mixins.py`: Reusable mixins (`HTMXViewMixin`, `ProfileAccessMixin`)
- **Services**:
  - Business logic encapsulated in services:
    - `profile_manager.py`: Services for job seeker profile operations
    - `talent_pool_manager.py`: Services for talent pool management
    - `recommendation/`: LLM-based recommendation processing (`llm_processor.py`, `xml_parser.py`)
    - `prompts/`: AI prompt templates
- **Tasks**:
  - Asynchronous tasks in `apps/job_seekers/tasks`:
    - `hooks.py`: Hook functions for task chaining
    - `pool_tasks.py`: Pool processing tasks (`process_resume_for_pool`, `cleanup_temp_resume_file`)
    - `personal_tagline_tasks.py`: Tasks for generating personal taglines
    - `recommendation_tasks.py`: Tasks for generating role recommendations
    - `talent_sheet_tasks.py`: Tasks for generating talent sheets
    - Imports from `apps.resume_processing.tasks`: `cleanup_resume_processing_progress` (now scheduled via Celery Beat), `save_resume_file`, `handle_resume_upload_task`
- **Templates**:
  - Job seeker–specific templates for signup, profiles, dashboards, and HTMX partials
- **Signals**:
  - Signal handlers for job seeker–specific actions
- **URLs**:
  - `/job-seekers/profile/`, `/job-seekers/profile/create/`, `/job-seekers/dashboard/`, `/job-seekers/settings/`
  - `/job-seekers/resume/<pk>/`, `/job-seekers/resume-upload/`, `/job-seekers/task-status/<task_id>/`
  - `/job-seekers/recommendations/`, `/job-seekers/talent-sheet/`
  - API endpoints under `/job-seekers/api/`

### Recruiters App (`apps/recruiters`)

Manages recruiter-specific functionality:

- **Models**:
  - `RecruiterProfile`: Extended profile for recruiters with credit balance fields (`credits_total`, `credits_available`). Recruiters purchase credits in bundles via Stripe; credits are required for actions like resume processing. No subscription or tier fields exist.
  - `JobOpening`: Job opening details posted by recruiters
- **Views**:
  - Various views for recruiter profile management and dashboard
  - Job opening management views (create, list, detail, edit, delete)
  - Candidate matching views for viewing potential candidates for job openings
  - **Credits management views**: Allow recruiters to view their credit balance, purchase more credits via Stripe, and see purchase history.
- **Templates**:
  - Recruiter-specific templates for signup, profiles, and dashboards
  - Job opening management templates
  - Candidate matching templates
  - **Credits templates**: Show credit balance and purchase options.
- **Signals**:
  - Signal handlers for recruiter-specific actions, including automatic deduction of credits when premium actions (like resume processing) are completed.
- **URLs**:
  - `/recruiters/profile/`: Recruiter profile
  - `/recruiters/dashboard/`: Recruiter dashboard
  - `/recruiters/settings/`: Recruiter settings
  - `/recruiters/job-openings/`: Job listings
  - `/recruiters/job-openings/create/`: Job creation
  - `/recruiters/job-openings/<id>/`: Job details
  - `/recruiters/job-openings/<id>/edit/`: Job editing
  - `/recruiters/job-openings/<id>/delete/`: Job deletion
  - `/recruiters/credits/`: View and purchase credits
  - `/recruiters/credits/create/<credits_amount>/`: Start Stripe checkout for credits
  - `/recruiters/credits/success/`: Stripe payment success and credit grant

### Matching App (`apps/matching`)

Manages candidate matching and embedding generation/storage:

- **Models**:
  - `CandidateMatch`: Matches between talent sheets and job openings
- **Core**:
  - `matching.py`: Core matching algorithms using vector embeddings
  - `pinecone_client.py`: Interaction with Pinecone vector database
  - `retrieval.py`: Functions to retrieve section embeddings from Pinecone
  - `vector_operations.py`: Utility functions for vector math (e.g., averaging)
- **Tasks**:
  - `job_opening_tasks.py`: Asynchronous tasks for creating/removing job opening embeddings
  - `talent_sheet_tasks.py`: Asynchronous tasks for creating/removing talent sheet embeddings
  - `matching_tasks.py`: Tasks for handling match creation and analysis
  - `common.py`: Shared utilities for embedding tasks (e.g., Pinecone index access)
- **Signals**:
  - Signal handlers in `signals.py` trigger embedding tasks automatically when `JobOpening` or `TalentSheet` instances are saved or deleted.
- **Management/Commands**:
  - `create_candidate_matches.py`: Generates `CandidateMatch` objects based on vector similarity
  - `rematch_all_jobs.py`: Rematch all active jobs after changes in the matching algorithm
  - `match.py`: Manually triggers matching between a specific job/talent (for testing/debug)
  - `analyze_job_match.py`: Generates match analysis for job/talent combinations
  - `refresh_match.py`: Updates an existing match with fresh data
  - `examine_vector_metadata.py`: Examines metadata stored in vectors
  - `list_pinecone_vectors.py`: Lists vectors by namespace with optional section filters
  - `check_skill_match_with_section.py`: Tests matching with different section filter formats
  - `create_matching_index.py`: Creates a Pinecone index for matching
  - `delete_matching_index.py`: Deletes a Pinecone index
  - `flush_matches.py`: Removes all matches for cleanup
  - `inspect_job_seeker.py`: Inspects a job seeker's data for debugging
- **Views**:
  - `candidate_views.py`: Views for recruiters to see matched candidates for a job
  - `matching_views.py`: API endpoints for triggering matches
- **Templates**:
  - `candidate_match_detail.html`: Detailed view of a candidate match
  - `components/`: Reusable UI components like candidate cards
  - `includes/`: Partial templates for candidate match lists
- **Admin**:
  - Custom admin interfaces for the `CandidateMatch` model
- **URLs**:
  - `/matching/`: URL patterns for candidate matching views and APIs

### Messaging App (`apps/messaging`)

Handles conversations and notifications between users:

- **Models**:
  - `Conversation`: Conversation between users
  - `Message`: Individual messages in conversations
  - `Notification`: Notifications for users
- **Views**:
  - Organized in subdirectories for conversation and notification management
- **Templates**:
  - Messaging-related templates for conversations and notifications
- **Admin**:
  - Custom admin interfaces for messaging models
- **URLs**:
  - `/messaging/conversations/`: List of conversations
  - `/messaging/conversations/<id>/`: Specific conversation
  - `/messaging/notifications/`: User notifications

### Resume Processing App (`apps/resume_processing`)

Dedicated background processing pipeline for PDF resumes.

- **Models**:
  - `ResumeProcessingTaskProgress`: Tracks progress of the resume processing workflow
  - `ResumeProcessingJob`: Tracks completed resume processing events for quota enforcement
- **Utils**:
  - `pipeline.py`: Orchestrates the resume-processing workflow
  - `extraction.py`: Extracts raw text from PDF files
  - `xml_error_reporting.py`: Utilities for XML error reporting
  - `profile_updater.py`: Updates `JobSeekerProfile` with extracted data
  - `llm_processor.py`: Handles AI-powered data extraction
  - `xml_parser.py`: Parses structured XML into model fields
- **Tasks**:
  - `cleanup_tasks.py`: Cleanup of old or completed progress records
  - `resume_processing_tasks.py`: Tasks for saving and processing resume uploads (`save_resume_file`, `handle_resume_upload_task`)
- **Management/Commands**:
  - `ingest_resumes.py`: Batch ingest sample resumes
  - `diagnose_resume.py`: Diagnose resume parsing issues

This separation lets the heavy lifting run in its own app while job-seeker views remain thin.

## Key Relationships Between Apps

The application has several important relationships between models across apps:

1. **User to Profiles**: The `User` model in the authentication app has one-to-one relationships with `JobSeekerProfile` in the job_seekers app and `RecruiterProfile` in the recruiters app.

2. **JobOpenings to Recruiters**: The `JobOpening` model in the recruiters app is linked to a `RecruiterProfile` via a foreign key.

3. **CandidateMatches**: The `CandidateMatch` model in the matching app connects `JobOpening` instances with `TalentSheet` instances through foreign keys.

4. **Conversations**: The `Conversation` model links multiple `User` instances through a many-to-many relationship, while `Message` instances are linked to a specific `Conversation` and a `User` sender.

## Architecture Patterns

The application uses several architecture patterns for better organization and maintainability:

### Service Layer Pattern

The service layer pattern separates business logic from presentation logic. Key aspects:

- **Services**: Classes that encapsulate business logic with no HTTP/presentation concerns
- **Views**: Classes that handle HTTP requests/responses and use services for business logic
- **Benefits**:
  - Cleaner separation of concerns
  - Improved testability
  - Reusable business logic across different views

Example services in the job_seekers app:

- `ProfileManager`: Handles job seeker profile operations
- `ResumeProcessor`: Manages resume processing tasks
- `TalentPoolManager`: Handles talent pool and role recommendation operations

### Mixin Pattern

Mixins provide reusable functionality that can be applied to multiple views:

- **HTMXViewMixin**: Handles HTMX-specific request detection and response rendering
- **ProfileAccessMixin**: Controls access permissions for job seekers
- **Benefits**:
  - Avoids code duplication
  - Promotes consistent behavior across views
  - Simplifies view classes by moving common functionality to mixins

## Frontend Structure

The application uses a modern frontend approach:

- **Templates**: Django templates with HTMX for dynamic interactions
- **CSS**: Tailwind CSS from CDN (<https://cdn.tailwindcss.com>)
- **UI Components**: DaisyUI from CDN (<https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css>)
- **Dynamic Interactions**: HTMX from CDN (<https://unpkg.com/htmx.org@1.9.2>)

### HTMX Integration

The application uses HTMX for dynamic interactions without writing custom JavaScript:

- **HTMXViewMixin**: Provides helper methods to detect HTMX requests and render appropriate responses
- **Response Headers**: Uses special HTMX response headers (HX-Redirect, HX-Trigger, etc.)
- **Partial Templates**: Many templates have partial versions for HTMX requests that return just the HTML fragment needed
- **Progressive Enhancement**: Fallbacks to standard form submissions when JavaScript is disabled

## Authentication Flow

The authentication system uses Django's built-in authentication combined with django-allauth for social authentication:

1. **Registration**: Users can sign up as either job seekers or recruiters through custom forms extending allauth's `SignupForm`.
2. **Email Authentication**: The system uses email for authentication instead of usernames, though usernames are auto-generated from email addresses in the format `emailprefix_randomsuffix`.
3. **Profile Creation**: After signup, users are directed to create their profile based on their user type.
4. **Social Authentication**: Users can authenticate using social accounts (Google, LinkedIn) with user type specified in the URL.
5. **Username Generation**: Usernames are automatically generated from email addresses using allauth's `populate_username` hook.
6. **User Type Assignment**: Social logins capture the user type from URL parameters, hidden form fields, or session data.
7. **Dashboard Redirection**: After login, users are redirected to their appropriate dashboard based on their user type.

The auth flow uses the following custom adapters:

- **AccountAdapter**: Customizes the account signup flow, including username generation and redirection
- **SocialAccountAdapter**: Handles social account integration, ensuring user types are correctly assigned

## Template Organization and Allauth Integration

The application integrates with django-allauth but also uses custom authentication views. This dual approach requires careful template organization:

1. **Custom Authentication Templates**: Located in `apps/authentication/templates/authentication/`, these templates are used by custom views (e.g., `CustomLoginView`, `CustomLogoutView`). These templates use custom URL patterns like `{% url 'authentication:login' %}`.

2. **Allauth Template Overrides**: Located in `apps/authentication/templates/account/`, these templates override django-allauth's default templates when using allauth's views. These templates use allauth URL patterns like `{% url 'account_login' %}`.

**Important considerations**:

- Custom views should use templates from the `authentication/` directory with custom URLs
- When extending or using allauth views directly, templates from the `account/` directory should be used
- Avoid mixing URL patterns between the two approaches (e.g., don't use `account_login` URLs in custom templates)
- For password reset and other functionality handled by allauth, use the appropriate URL patterns (either custom or allauth's, depending on the approach)

## Job Matching Process

The job matching process is one of the key features of the application:

1. **Job Creation**: Recruiters create job openings with required skills and details.
2. **Resume Upload**: Job seekers upload their resumes, which are processed by the system.
3. **Resume Processing Pipeline**:
   - Text extraction from PDF files
   - Conversion to structured XML using LLM integration
   - Parsing XML to extract key information
   - Updating JobSeekerProfile with extracted information
4. **Talent Sheet Generation**:
   - When job seekers join the talent pool, a basic placeholder talent sheet is created immediately
   - An asynchronous task then enhances this talent sheet using LLM with a structured prompt
   - The LLM-generated talent sheet includes a promotional blurb, skill overview, and ideal roles
   - For job seekers who have shown interest in role recommendations, these are incorporated into the talent sheet
5. **Vector Generation**: The system creates embeddings for both jobs and talent sheets.
6. **Matching Algorithm**: Vector similarity is used to match job seekers to job openings based on skills, experience, and other factors.
7. **Match Presentation**: Recruiters are shown matching candidates for their job openings with rating scores out of 10.
8. **Match Analysis**: AI analyzes why a match is suitable and provides detailed summaries.

## URL Structure

The application uses namespaced URLs for each app:

- `/`: Home page and core functionality (`core` namespace)
- `/auth/`: User authentication and account management (`authentication` namespace)
- `/job-seekers/`: Job seeker-specific functionality (`job_seekers` namespace)
- `/recruiters/`: Recruiter-specific functionality, including job opening management (`recruiters` namespace)
- `/matching/`: Candidate matching functionality (`matching` namespace)
- `/messaging/`: Conversations and notifications (`messaging` namespace)

## Python 3.12 Compatibility

This application is built with Python 3.12, which has some important differences in type annotations compared to earlier Python versions:

### Type Annotation Changes

- **Native vs Imported Types**: Use native types when possible (`list` and `dict`) rather than importing from `typing`
- **QuerySet Type**: Import from `django.db.models.query` instead of `typing`
- **Type Hints**: The application uses type hints extensively for better code quality and IDE support
- **Union Syntax**: Use `Type | None` instead of `Optional[Type]` for optional values

### Common Type Annotation Issues

The project uses custom linter rules to enforce consistent type annotations:

1. **Union Type Syntax**: Always use `Type | None` instead of `Optional[Type]` for nullable types
2. **QuerySet Type**: Import `QuerySet` from `django.db.models.query` instead of `typing`
3. **Native Types**: Use built-in types like `list[str]` and `dict[str, Any]` instead of importing from `typing`
4. **Type Parameters**: Always include type parameters for generic types (e.g., `list[str]` instead of just `list`)

### Development Guidelines for Type Annotations

- Always specify return types for functions and methods
- Use type parameters for generic types like `list`, `dict`, and `QuerySet`
- When working with Django querysets, import `QuerySet` from `django.db.models.query`
- Run type checking tools like mypy periodically to catch type-related issues

## Background Tasks

The application uses Celery for background tasks:

- **Resume Processing**: Asynchronous processing of uploaded resumes via the `process_resume` pipeline in `apps/resume_processing/utils/pipeline.py`
- **Talent Sheet Generation**: Asynchronous enhancement of talent sheets using LLM via `generate_talent_sheet_task`
- **AI Analysis**: Background AI analysis for matching and recommendations
- **Email Notifications**: Sending emails in the background
- **Vector Generation**: Creating embeddings for jobs and talent sheets in the background
- **Match Creation**: Finding and creating matches in the background

## Development Guidelines

When working with this codebase:

1. **Follow the existing modular structure**
2. **Use class-based views** for consistency
3. **Add comprehensive docstrings** to new code
4. **Include type annotations** for all function parameters and return values
5. **Use HTMX for dynamic interactions** where appropriate
6. **Handle errors gracefully** with proper error messages
7. **Use Django messages framework** for user feedback
8. **Follow Django's best practices** for URL naming and organization
9. **Separate business logic into services** to maintain clean separation of concerns
10. **Use mixins for reusable view functionality** rather than duplicating code

## Working with the User Model

The application uses a custom user model with email authentication:

```python
# Using the User model
from apps.authentication.models import User

# Creating a user
user = User.objects.create_user(
    email="example@example.com",
    password="password",
    name="Full Name",
    user_type="job_seeker"
)
```

## Working with Profiles

Job seeker and recruiter profiles are automatically created through signals:

```python
# Accessing a job seeker profile
user = User.objects.get(email="jobseeker@example.com")
profile = user.job_seeker_profile

# Accessing a recruiter profile
user = User.objects.get(email="recruiter@example.com")
profile = user.recruiter_profile
```

## Using Service Classes

Service classes encapsulate business logic separately from views:

```python
# Using a service class
from apps.job_seekers.services import ProfileManager, ResumeProcessor, TalentPoolManager

# Get a profile
profile = ProfileManager.get_profile(user)

# Update a profile
updated_profile = ProfileManager.create_or_update_profile(user, profile_data)

# Process a resume (using the pipeline)
from apps.job_seekers.utils.resume_processing.pipeline import process_resume
result = process_resume(file_path, profile, task_id)

# Manage talent pool
talent_sheet = TalentPoolManager.create_or_update_talent_sheet(profile, talent_sheet_data)
```

## Project Configuration

The project's main configuration is in the `hiredar/settings.py` file. Key settings include:

- Custom user model: `AUTH_USER_MODEL = "authentication.User"`
- Authentication backends for django-allauth
- Media and static file configuration
- Celery configuration for background tasks

## Deployment and Environment Configuration

The application is designed to be deployed in various environments with different configurations:

### Environment Variables

The application uses environment variables for configuration, loaded through a `.env` file in development:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DATABASE_URL`: Database connection string (for production)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `EMAIL_*`: Email configuration settings
- `PINECONE_API_KEY`: API key for Pinecone vector database
- `PINECONE_ENVIRONMENT`: Pinecone environment
- `OPENAI_API_KEY`: API key for OpenAI services

## Security Considerations

Security is a critical aspect of the application. Here are key security considerations:

### Authentication and Authorization

- User authentication is handled through Django's authentication system and django-allauth
- Email verification is required for new accounts
- User permissions are based on user types (job seeker or recruiter)
- Sensitive views are protected with LoginRequiredMixin

### Data Protection

- Passwords are hashed using Django's password hashers
- CSRF protection is enabled for all forms
- Sensitive data is not exposed in templates or APIs
- File uploads are validated and sanitized

### Production Security Measures

- Debug mode is disabled in production
- Secret keys and credentials are stored as environment variables
- HTTPS is enforced for all connections
- Security headers are set appropriately
- Regular security updates are applied

### Security Best Practices

When developing new features:

1. Validate all user inputs
2. Escape outputs to prevent XSS attacks
3. Use parameterized queries to prevent SQL injection
4. Implement proper access controls
5. Follow the principle of least privilege

## Recruiter Credits System

Recruiters use credits to access premium features such as resume processing. Credits can be purchased in bundles via Stripe and are deducted automatically as features are used.

- **Purchasing Credits**: Recruiters can purchase credits from the Credits page. Each bundle (e.g., 10, 50, 100 credits) is linked to a Stripe price. After successful payment, credits are added to the recruiter's account.
- **Spending Credits**: Credits are deducted for actions such as resume processing. If a recruiter has insufficient credits, they are prompted to purchase more.
- **Stripe Integration**: Stripe Checkout is used for secure payments. Price IDs are managed in Django settings. Credits are only granted after payment is confirmed.
- **Admin and UI**: Admins can view and search recruiter credit balances. Recruiters see their credit balance in the sidebar and on the credits page.
