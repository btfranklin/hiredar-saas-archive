# Job Processing Utilities

This directory contains utility functions for processing job descriptions into structured data and creating job openings.

## Overview

The job processing utilities work together to:

1. Process freeform text job descriptions
2. Convert them to structured XML using LLM with Promptdown templates
3. Parse the XML into JobOpening model instances

## Module Structure

- `pipeline.py`: Orchestrates the entire job processing workflow
- `llm_processor.py`: Handles interactions with the LLM API for text-to-XML conversion using Promptdown
- `xml_parser.py`: Parses XML and extracts data to create JobOpening instances

## Prompt Structure

The LLM interactions use Promptdown templates located in:
- `apps/recruiters/utils/prompts/convert_job_description_to_xml.prompt.md`

These templates follow the Promptdown format which provides:
- System/Developer message to set the LLM's role and context
- Clearly defined task instructions
- Response format specification
- Template placeholders for dynamic content

## Pipeline Flow

```
Process Job Description
│
├── Preprocess text 
│
├── Convert to XML via LLM (llm_processor.py)
│   ├── Load Promptdown template
│   ├── Apply template values (job title, description)
│   ├── Convert to chat completion messages
│   ├── Send to OpenAI API
│   ├── Sanitize XML response
│   └── Validate XML structure
│
└── Parse XML and create JobOpening (xml_parser.py)
    └── Extract data and create database record
```

## XML Structure

The job opening XML follows this structure:

```xml
<job>
    <title>Job Title</title>
    <company>Company Name</company>
    <location>Job Location</location>
    <description>Full job description</description>
    <requirements>
        <skills>
            <skill>Skill 1</skill>
            <skill>Skill 2</skill>
        </skills>
        <qualifications>
            <qualification>Qualification 1</qualification>
            <qualification>Qualification 2</qualification>
        </qualifications>
        <experience>Required experience details</experience>
    </requirements>
    <details>
        <job_level>entry|junior|mid|senior|manager|executive</job_level>
        <employment_type>full_time|part_time|contract|temporary|internship</employment_type>
        <salary_min>Minimum salary (numeric only)</salary_min>
        <salary_max>Maximum salary (numeric only)</salary_max>
        <benefits>Benefits description</benefits>
        <perks>Additional perks</perks>
    </details>
    <responsibilities>
        <responsibility>Responsibility 1</responsibility>
        <responsibility>Responsibility 2</responsibility>
    </responsibilities>
    <working_conditions>
        <hours>Working hours</hours>
        <environment>office|remote|hybrid</environment>
        <reporting_to>Reports to</reporting_to>
        <travel>Travel requirements</travel>
    </working_conditions>
</job>
```

## Error Handling

The llm_processor module includes comprehensive error handling:
- API connection issues
- Malformed XML responses
- XML sanitization for common LLM output issues
- Detailed logging for troubleshooting

## Usage

These utilities are typically used through the task functions in `apps.recruiters.tasks`, rather than being called directly. 

## Dependencies

- OpenAI Python client
- Promptdown (for structured prompt templates)
- Python XML libraries (xml.etree.ElementTree) 