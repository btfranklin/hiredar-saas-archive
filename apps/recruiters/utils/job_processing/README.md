# Job Processing Utilities

This directory contains utility functions for processing job descriptions into structured data and creating job openings.

## Overview

The job processing utilities work together to:

1. Process freeform text job descriptions
2. Convert them to structured XML using LLM
3. Parse the XML into JobOpening model instances

## Module Structure

- `pipeline.py`: Orchestrates the entire job processing workflow
- `llm_processor.py`: Handles interactions with the LLM API for text-to-XML conversion
- `xml_parser.py`: Parses XML and extracts data to create JobOpening instances

## Pipeline Flow

```
Process Job Description
│
├── Preprocess text 
│
├── Convert to XML via LLM (llm_processor.py)
│   └── Create structured XML from job description
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
        <job_level>Job level</job_level>
        <employment_type>Employment type</employment_type>
        <salary_min>Minimum salary</salary_min>
        <salary_max>Maximum salary</salary_max>
        <benefits>Benefits description</benefits>
        <perks>Additional perks</perks>
    </details>
    <responsibilities>
        <responsibility>Responsibility 1</responsibility>
        <responsibility>Responsibility 2</responsibility>
    </responsibilities>
    <working_conditions>
        <hours>Working hours</hours>
        <environment>Work environment</environment>
        <reporting_to>Reports to</reporting_to>
        <travel>Travel requirements</travel>
    </working_conditions>
</job>
```

## Usage

These utilities are typically used through the task functions in `apps.recruiters.tasks`, rather than being called directly. 