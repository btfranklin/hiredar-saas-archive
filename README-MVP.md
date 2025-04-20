# Hiredar MVP (Recruiter‑Focused)

## Elevator Pitch

**Hiredar** is an AI‑powered resume management and candidate matching platform built for busy recruiters. By automating PDF parsing, structured data extraction, and multi‑lens matching, Hiredar transforms large batches of resumes into prioritized, actionable candidate lists—eliminating manual sorting and surfacing top talent in seconds.

## MVP Scope

This initial version is designed exclusively for **recruiters**. There is no public job‑seeker signup or in‑app candidate interactions. Recruiters will:

1. **Bulk‑upload** PDF resumes for a specific job opening
2. **Run** the AI pipeline to extract skills, experience, and generate concise taglines
3. **Receive** ranked candidate matches against the job criteria
4. **Export** or review match lists, then reach out to candidates externally

## Key Problems Solved

- **Resume Overload**: Rapidly ingest hundreds (or thousands) of PDFs without manual parsing.
- **Data Extraction**: Automatically convert unstructured resumes into searchable, structured profiles.
- **Multi‑Lens Matching**: Match candidates by skills, experience level, and role‑specific criteria tailored to your opening.
- **Insights & Conversation Starters**: Generate AI‑driven personal taglines to help recruiters quickly understand and engage candidates.

## Core Features

1. **Bulk Resume Ingestion**
   - Securely upload a folder or ZIP of PDF resumes.
   - Each file is queued for background processing.

2. **AI‑Driven Parsing Pipeline**
   - **Text Extraction**: PDF → Plain text
   - **LLM Conversion**: Text → Structured XML
   - **XML Parsing**: Extract skills, experience, education, certifications
   - **Tagline Generation**: Personal identity snippets for recruiter outreach
   - **Progress Tracking**: Real‑time stepper to monitor pipeline stages

3. **Candidate Matching Engine**
   - Provide a job description or role specification.
   - AI matches the parsed resume data to your criteria.
   - Receive a ranked list of top candidates.

4. **Recruiter Dashboard**
   - View upload history and processing status.
   - Drill into individual candidate profiles.
   - Export match results as CSV or PDF.

## Competitive Research Context

To guide an automated deep-dive competitor analysis, include these details:

- **Primary User Persona**: Experienced technical recruiters managing high-volume hiring for multiple roles, struggling with manual resume screening and lacking unified candidate insights.
- **Core Workflows**:
  1. Bulk upload of PDF resumes tied to a specific job opening
  2. AI-powered parsing pipeline (text extraction, LLM XML conversion, XML parsing, tagline generation, progress tracking)
  3. Matching engine that ranks candidates by skill fit, experience level, and role criteria
  4. Exporting or reviewing match lists for external outreach
- **Key Features & Value Props**:
  - Automated structured data extraction from unstructured resumes
  - Multi‑lens AI matching (skills lens, experience lens, role‑specific criteria)
  - AI-generated personal taglines for rapid candidate understanding
  - Real‑time progress dashboard and status tracking
  - Ease of integration: Django backend, HTMX interactivity, Tailwind/DaisyUI styling
- **Technical Architecture**:
  - Python 3.12, Django 4.x (class‑based views)
  - Django Q2 for background tasks
  - OpenAI GPT-4 for resume-to-XML conversion and tagline generation
  - Tailwind CSS & DaisyUI for UI, HTMX for AJAX-like interactions without heavy JS
- **Business Objectives**:
  - Reduce time-to-hire by automating resume intake and screening
  - Improve match quality with data-driven AI ranking and insights
  - Minimize recruiter workload by surfacing top candidates instantaneously
- **Competitive Landscape**:
  - Applicant Tracking Systems (ATS) with resume parsing
  - AI-powered sourcing tools and screening platforms
  - Resume screening software, candidate rediscovery features
  - Diversity & inclusion AI solutions and blind screening tools

## Technology Stack

- **Django 5.2** with class‑based views for backend
- **Tailwind CSS** + **DaisyUI** for rapid UI styling
- **HTMX** for dynamic status updates without JS frameworks
- **OpenAI APIs** for XML conversion and AI features

## Going Forward

After validating the recruiter workflow, future versions will:

- Introduce in‑app candidate profiles and communication tools
- Add job‑seeker signup and self‑service resumes
- Support interview scheduling and feedback loops
- Expand matching filters and analytics dashboards
