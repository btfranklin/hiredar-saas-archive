"""
LLM processing utilities for job descriptions.

This module contains functions for using Large Language Models (LLMs)
to convert job description text into structured XML format.
"""

import logging
import xml.etree.ElementTree as ET

import requests
from django.conf import settings

# Setup logging
logger = logging.getLogger(__name__)

# XML structure template for job openings
JOB_XML_TEMPLATE = """
<job>
    <title>Job Title</title>
    <company>Company Name</company>
    <location>Job Location</location>
    <description>Full job description</description>
    <requirements>
        <skills>
            <skill>Skill 1</skill>
            <skill>Skill 2</skill>
            ...
        </skills>
        <qualifications>
            <qualification>Qualification 1</qualification>
            <qualification>Qualification 2</qualification>
            ...
        </qualifications>
        <experience>Required experience details</experience>
    </requirements>
    <details>
        <job_level>Job level (entry, junior, mid, senior, manager, executive)</job_level>
        <employment_type>Employment type (full_time, part_time, contract, temporary, internship)</employment_type>
        <salary_min>Minimum salary (numeric, no currency symbol)</salary_min>
        <salary_max>Maximum salary (numeric, no currency symbol)</salary_max>
        <benefits>Benefits description</benefits>
        <perks>Additional perks</perks>
    </details>
    <responsibilities>
        <responsibility>Responsibility 1</responsibility>
        <responsibility>Responsibility 2</responsibility>
        ...
    </responsibilities>
    <working_conditions>
        <hours>Working hours</hours>
        <environment>Work environment (office, remote, hybrid)</environment>
        <reporting_to>Reports to</reporting_to>
        <travel>Travel requirements</travel>
    </working_conditions>
</job>
"""


def convert_text_to_xml(job_title: str, job_description: str) -> str:
    """
    Convert job description text to structured XML using LLM.

    Args:
        job_title: The title of the job
        job_description: The full text description of the job

    Returns:
        XML string representation of the job or empty string if processing fails
    """
    try:
        # Check if OpenAI API key is configured
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            logger.error("OpenAI API key not configured")
            return ""

        # Prepare the prompt for the LLM
        prompt = _create_llm_prompt(job_title, job_description)

        # Call OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a job description parser. Your task is to extract structured information from job descriptions and format it as XML.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
            },
            timeout=60,
        )

        # Process the response
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Extract XML content from the response
            xml_content = content
            if "<job>" in content:
                start_idx = content.find("<job>")
                end_idx = content.find("</job>") + 6
                xml_content = content[start_idx:end_idx]

            # Validate XML
            ET.fromstring(xml_content)  # This will raise an exception if XML is invalid

            # Log success
            logger.info(
                "Successfully converted job description to XML: %s (%d chars)",
                job_title,
                len(xml_content),
            )

            return xml_content
        else:
            logger.error(
                f"Error from OpenAI API: {response.status_code} - {response.text}"
            )
            return ""

    except ET.ParseError as e:
        logger.error(f"XML parsing error: {str(e)}")
        return ""
    except requests.RequestException as e:
        logger.error(f"API request error: {str(e)}")
        return ""
    except Exception as e:
        logger.error(f"Error converting text to XML: {str(e)}")
        return ""


def _create_llm_prompt(job_title: str, job_description: str) -> str:
    """
    Create a detailed prompt for the LLM to convert job description to XML.

    Args:
        job_title: The title of the job
        job_description: The full text description of the job

    Returns:
        Formatted prompt for the LLM
    """
    return f"""
    Convert the following job description into structured XML format:
    
    Job Title: {job_title}
    
    Job Description:
    {job_description}
    
    Format the response as valid XML with the following structure:
    
    {JOB_XML_TEMPLATE}
    
    Make sure to extract as much information as possible from the job description.
    If any information is not available, leave the corresponding XML element empty.
    
    IMPORTANT GUIDELINES:
    1. Focus on extracting meaningful, descriptive information from the text
    2. For skills, extract specific technical skills, tools, and software
    3. Salary values should be numbers only, without currency symbols or formatting
    4. For job_level, use one of: entry, junior, mid, senior, manager, executive
    5. For employment_type, use one of: full_time, part_time, contract, temporary, internship
    6. Make sure the XML is well-formed and valid
    """
