# Hiredar Model Structure

This document provides a comprehensive overview of all models in the Hiredar application, their attributes, relationships, and key methods.

## Overview Diagram

```mermaid
classDiagram
    User <|-- JobSeekerProfile : one-to-one
    User <|-- RecruiterProfile : one-to-one
    RecruiterProfile <|-- JobOpening : one-to-many
    JobSeekerProfile <|-- CandidateMatch : one-to-many
    JobOpening <|-- CandidateMatch : one-to-many
    JobSeekerProfile <|-- RoleRecommendation : one-to-many
    User <|-- Conversation : many-to-many
    User <|-- Message : one-to-many (sender)
    Conversation <|-- Message : one-to-many
    User <|-- Notification : one-to-many

    class User {
        +username: CharField
        +email: EmailField
        +first_name: CharField
        +last_name: CharField
        +user_type: CharField
        +bio: TextField
        +location: CharField
        +is_staff: BooleanField
        +is_active: BooleanField
        +date_joined: DateTimeField
    }
    
    class JobSeekerProfile {
        +user: OneToOneField(User)
        +skills: TextField
        +experience: TextField
        +years_of_experience: PositiveIntegerField
        +desired_role: CharField
        +current_position: CharField
        +about_me: TextField
        +linkedin_url: URLField
        +github_url: URLField
        +portfolio_url: URLField
    }
    
    class RecruiterProfile {
        +user: OneToOneField(User)
        +is_subscribed: BooleanField
        +subscription_tier: CharField
    }
    
    class JobOpening {
        +recruiter: ForeignKey(RecruiterProfile)
        +title: CharField
        +description: TextField
        +location: CharField
        +company: CharField
        +salary_min: DecimalField
        +salary_max: DecimalField
        +required_skills: TextField
        +experience_years: PositiveIntegerField
        +is_active: BooleanField
        +created_at: DateTimeField
        +updated_at: DateTimeField
    }
    
    class CandidateMatch {
        +job_opening: ForeignKey(JobOpening)
        +job_seeker: ForeignKey(JobSeekerProfile)
        +match_score: DecimalField
        +status: CharField
        +is_shortlisted: BooleanField
        +match_type: CharField
        +created_at: DateTimeField
        +updated_at: DateTimeField
    }
    
    class RoleRecommendation {
        +job_seeker: ForeignKey(JobSeekerProfile)
        +role_title: CharField
        +description: TextField
        +confidence_score: DecimalField
        +created_at: DateTimeField
    }
    
    class Conversation {
        +participants: ManyToManyField(User)
        +created_at: DateTimeField
        +updated_at: DateTimeField
    }
    
    class Message {
        +conversation: ForeignKey(Conversation)
        +sender: ForeignKey(User)
        +content: TextField
        +created_at: DateTimeField
        +is_read: BooleanField
    }
    
    class Notification {
        +user: ForeignKey(User)
        +notification_type: CharField
        +content: TextField
        +link: CharField
        +is_read: BooleanField
        +created_at: DateTimeField
    }
```

## Authentication App

### User

The custom User model that serves as the base for all user accounts.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `username` | CharField | Auto-generated username based on email (hidden from UI) |
| `email` | EmailField | Primary login field, must be unique |
| `first_name` | CharField | User's first name |
| `last_name` | CharField | User's last name |
| `user_type` | CharField | Either "job_seeker" or "recruiter" |
| `bio` | TextField | Brief user biography |
| `location` | CharField | User's location |
| `is_staff` | BooleanField | Whether user can access admin site |
| `is_active` | BooleanField | Whether user account is active |
| `date_joined` | DateTimeField | When the user joined |

**Key Methods:**
| Method | Description |
|--------|-------------|
| `get_full_name()` | Returns the user's full name |
| `get_short_name()` | Returns the user's first name |
| `to_dict()` | Converts user instance to a dictionary |
| `get_initials()` | Gets user initials for avatar display |
| `get_absolute_url()` | Returns URL for the user's profile |

## Job Seekers App

### JobSeekerProfile

Extended profile for job seekers with career-related information.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOneField | Link to User model (with user_type="job_seeker") |
| `skills` | TextField | Comma-separated list of skills |
| `experience` | TextField | Description of work experience |
| `years_of_experience` | PositiveIntegerField | Total years of experience |
| `desired_role` | CharField | Desired job role |
| `current_position` | CharField | Current job position |
| `about_me` | TextField | Detailed description about the job seeker |
| `linkedin_url` | URLField | LinkedIn profile URL |
| `github_url` | URLField | GitHub profile URL |
| `portfolio_url` | URLField | Portfolio website URL |

**Key Methods:**
| Method | Description |
|--------|-------------|
| `skills_list` | Property that returns a list of skill names |
| `get_matched_skills_count()` | Calculate how many required skills this job seeker has |

## Recruiters App

### RecruiterProfile

Extended profile for recruiters with subscription information.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `user` | OneToOneField | Link to User model (with user_type="recruiter") |
| `is_subscribed` | BooleanField | Whether recruiter has an active subscription |
| `subscription_tier` | CharField | Subscription tier (basic/professional/enterprise) |

## Jobs App

### JobOpening

Model for job openings posted by recruiters.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `recruiter` | ForeignKey | Link to RecruiterProfile that posted the job |
| `title` | CharField | Job title |
| `description` | TextField | Detailed job description |
| `location` | CharField | Job location |
| `company` | CharField | Company offering this position |
| `salary_min` | DecimalField | Minimum salary offered |
| `salary_max` | DecimalField | Maximum salary offered |
| `required_skills` | TextField | Comma-separated list of required skills |
| `experience_years` | PositiveIntegerField | Required years of experience |
| `is_active` | BooleanField | Whether the job opening is active |
| `created_at` | DateTimeField | When the job was created |
| `updated_at` | DateTimeField | When the job was last updated |

**Key Methods:**
| Method | Description |
|--------|-------------|
| `required_skills_list` | Property that returns a list of required skill names |

### CandidateMatch

Model for matching job seekers to job openings.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `job_opening` | ForeignKey | Link to the JobOpening |
| `job_seeker` | ForeignKey | Link to the JobSeekerProfile |
| `match_score` | DecimalField | Match score between 0 and 100 |
| `status` | CharField | Status of the match (pending/accepted/rejected/withdrawn) |
| `is_shortlisted` | BooleanField | Whether the candidate is shortlisted |
| `match_type` | CharField | Type of match (top/wildcard) |
| `created_at` | DateTimeField | When the match was created |
| `updated_at` | DateTimeField | When the match was last updated |

### RoleRecommendation

Model for AI-generated role recommendations for job seekers.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `job_seeker` | ForeignKey | Link to the JobSeekerProfile |
| `role_title` | CharField | Title of the recommended role |
| `description` | TextField | Description of the recommended role |
| `confidence_score` | DecimalField | AI confidence score between 0 and 100 |
| `created_at` | DateTimeField | When the recommendation was created |

## Messaging App

### Conversation

Model for conversations between users.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `participants` | ManyToManyField | Users participating in the conversation |
| `created_at` | DateTimeField | When the conversation was created |
| `updated_at` | DateTimeField | When the conversation was last updated |

**Key Methods:**
| Method | Description |
|--------|-------------|
| `get_other_participant()` | Get the other participant in a conversation |
| `other_participant` | Property to get the other participant (for templates) |

### Message

Model for messages within a conversation.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `conversation` | ForeignKey | Link to the Conversation |
| `sender` | ForeignKey | User who sent the message |
| `content` | TextField | Message content |
| `created_at` | DateTimeField | When the message was sent |
| `is_read` | BooleanField | Whether the message has been read |

### Notification

Model for user notifications.

**Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `user` | ForeignKey | User to notify |
| `notification_type` | CharField | Type of notification (message/match/application/system) |
| `content` | TextField | Notification content |
| `link` | CharField | URL to link to |
| `is_read` | BooleanField | Whether the notification has been read |
| `created_at` | DateTimeField | When the notification was created |

## Model Relationships

### User Relationships
- One-to-One with JobSeekerProfile (for job seeker users)
- One-to-One with RecruiterProfile (for recruiter users)
- Many-to-Many with Conversation (as participants)
- One-to-Many with Message (as sender)
- One-to-Many with Notification (as recipient)

### JobSeekerProfile Relationships
- One-to-One with User
- One-to-Many with CandidateMatch (as job_seeker)
- One-to-Many with RoleRecommendation (as job_seeker)

### RecruiterProfile Relationships
- One-to-One with User
- One-to-Many with JobOpening (as recruiter)

### JobOpening Relationships
- Many-to-One with RecruiterProfile (as recruiter)
- One-to-Many with CandidateMatch (as job_opening)

### Conversation Relationships
- Many-to-Many with User (as participants)
- One-to-Many with Message (as conversation)

## Database Schema Notes

- The application uses a custom User model with email-based authentication
- Profiles are created automatically via signals when a user is created
- All models use proper foreign key constraints for data integrity
- Most models include timestamps for created_at/updated_at 