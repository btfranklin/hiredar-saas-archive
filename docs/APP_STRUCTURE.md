# Hiredar Application Structure

This document describes the structure and organization of the Hiredar application to help new developers understand the codebase.

## Overview

Hiredar is a job matching platform that connects job seekers with recruiters using AI-powered matching algorithms. The application follows a modular Django architecture with separate apps for different functional areas. This document provides an overview of the codebase organization to help you navigate and understand the application.

## Application Architecture

The application is built using Django 5.1.7 and follows a modular approach with the following key components:

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

Manages job seeker-specific functionality:

- **Models**:
  - `JobSeekerProfile`: Extended profile for job seekers including skills, experience, education, certifications, contact information, and social media links
  - `ResumeProcessingTaskProgress`: Tracks progress of resume processing tasks
  - `RoleRecommendation`: Career recommendations for job seekers based on their skills and experience
- **Views**:
  - Organized in subdirectories for better maintainability:
    - `dashboard_views.py`: Dashboard view for job seekers
    - `job_seeker_profile_views.py`: Profile and settings views
    - `resume_processing_views.py`: Resume upload and processing views
- **Templates**:
  - Job seeker-specific templates for signup, profiles, and dashboards
- **Signals**:
  - Signal handlers for job seeker-specific actions
- **Tasks**:
  - Background tasks for resume processing and AI analysis
- **URLs**:
  - `/job-seekers/profile/`: Job seeker profile
  - `/job-seekers/profile/create/`: Profile creation
  - `/job-seekers/dashboard/`: Job seeker dashboard
  - `/job-seekers/settings/`: Job seeker settings
  - `/job-seekers/recommendations/`: Role recommendations for job seekers

### Recruiters App (`apps/recruiters`)

Manages recruiter-specific functionality:

- **Models**:
  - `RecruiterProfile`: Extended profile for recruiters with subscription information
  - `JobOpening`: Job opening details posted by recruiters
- **Views**:
  - Various views for recruiter profile management and dashboard
  - Job opening management views (create, list, detail, edit, delete)
  - Candidate matching views for viewing potential candidates for job openings
- **Templates**:
  - Recruiter-specific templates for signup, profiles, and dashboards
  - Job opening management templates
  - Candidate matching templates
- **Signals**:
  - Signal handlers for recruiter-specific actions
- **URLs**:
  - `/recruiters/profile/`: Recruiter profile
  - `/recruiters/dashboard/`: Recruiter dashboard
  - `/recruiters/settings/`: Recruiter settings
  - `/recruiters/job-openings/`: Job listings
  - `/recruiters/job-openings/create/`: Job creation
  - `/recruiters/job-openings/<id>/`: Job details
  - `/recruiters/job-openings/<id>/edit/`: Job editing
  - `/recruiters/job-openings/<id>/delete/`: Job deletion

### Matching App (`apps/matching`)

Manages candidate matching:

- **Models**:
  - `CandidateMatch`: Matches between job seekers and job openings
- **Views**:
  - Views for matching candidates to job openings
- **Templates**:
  - Templates for candidate matching (organized within the matching directory)
- **Admin**:
  - Custom admin interfaces for the CandidateMatch model
- **URLs**:
  - `/matching/`: URL patterns for candidate matching functionality

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

## Key Relationships Between Apps

The application has several important relationships between models across apps:

1. **User to Profiles**: The `User` model in the authentication app has one-to-one relationships with `JobSeekerProfile` in the job_seekers app and `RecruiterProfile` in the recruiters app.

2. **JobOpenings to Recruiters**: The `JobOpening` model in the recruiters app is linked to a `RecruiterProfile` via a foreign key.

3. **CandidateMatches**: The `CandidateMatch` model in the matching app connects `JobOpening` instances from the recruiters app with `JobSeekerProfile` instances from the job_seekers app through foreign keys.

4. **Conversations**: The `Conversation` model links multiple `User` instances through a many-to-many relationship, while `Message` instances are linked to a specific `Conversation` and a `User` sender.

## Frontend Structure

The application uses a modern frontend approach:

- **Templates**: Django templates with HTMX for dynamic interactions
- **CSS**: Tailwind CSS from CDN (<https://cdn.tailwindcss.com>)
- **UI Components**: DaisyUI from CDN (<https://cdn.jsdelivr.net/npm/daisyui@latest/dist/full.css>)
- **Dynamic Interactions**: HTMX from CDN (<https://unpkg.com/htmx.org@1.9.2>)

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
3. **Skill Extraction**: AI processes extract skills and experience from resumes.
4. **Matching Algorithm**: The system matches job seekers to job openings based on skills and requirements.
5. **Match Presentation**: Recruiters are shown matching candidates for their job openings.

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

The application uses Django Q for background tasks:

- **Resume Processing**: Asynchronous processing of uploaded resumes
- **AI Analysis**: Background AI analysis for matching and recommendations
- **Email Notifications**: Sending emails in the background

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

## Project Configuration

The project's main configuration is in the `hiredar/settings.py` file. Key settings include:

- Custom user model: `AUTH_USER_MODEL = "authentication.User"`
- Authentication backends for django-allauth
- Media and static file configuration
- Django Q cluster configuration for background tasks

## Deployment and Environment Configuration

The application is designed to be deployed in various environments with different configurations:

### Environment Variables

The application uses environment variables for configuration, loaded through a `.env` file in development:

- `SECRET_KEY`: Django secret key
- `DEBUG`: Debug mode (True/False)
- `DATABASE_URL`: Database connection string (for production)
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `EMAIL_*`: Email configuration settings

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
