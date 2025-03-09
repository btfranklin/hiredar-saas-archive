"""
Management command to test the resume parsing functionality.

Usage:
    python manage.py test_resume_parser /path/to/test/resume.pdf
"""

import logging
import os
import time

from django.core.management.base import BaseCommand, CommandError

from apps.job_seekers.utils.llm_api import convert_text_resume_to_xml
from apps.job_seekers.utils.resume_parser import (
    calculate_years_experience,
    extract_bio,
    extract_most_recent_title,
    extract_skills_from_xml,
    extract_text_from_pdf,
)

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test the resume parsing functionality with a sample resume"

    def add_arguments(self, parser):
        # Optional path to a test resume PDF
        parser.add_argument(
            "resume_path",
            nargs="?",
            type=str,
            help="Path to a sample resume PDF file for testing",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting resume parser test"))

        resume_path = options.get("resume_path")
        if not resume_path:
            self.stdout.write(
                self.style.WARNING("No resume path provided. Using sample test data.")
            )
            # You could load sample test data here
            return

        if not os.path.exists(resume_path):
            raise CommandError(f"Resume file not found: {resume_path}")

        # Step 1: Extract text from PDF
        self.stdout.write("Step 1: Extracting text from PDF...")
        start_time = time.time()
        raw_text = extract_text_from_pdf(resume_path)
        if not raw_text:
            self.stdout.write(self.style.ERROR("Failed to extract text from PDF"))
            return

        pdf_time = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f"Text extracted successfully ({pdf_time:.2f}s)")
        )
        self.stdout.write(f"Extracted {len(raw_text)} characters")
        self.stdout.write("Sample text:")
        self.stdout.write(raw_text[:300] + "..." if len(raw_text) > 300 else raw_text)

        # Step 2: Use LLM to convert raw text to structured XML
        self.stdout.write("\nStep 2: Converting to XML with LLM...")
        start_time = time.time()
        xml_content = convert_text_resume_to_xml(raw_text)
        if not xml_content:
            self.stdout.write(
                self.style.ERROR("Failed to process resume text with LLM")
            )
            return

        llm_time = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f"XML generated successfully ({llm_time:.2f}s)")
        )
        self.stdout.write(f"XML length: {len(xml_content)} characters")
        self.stdout.write("Sample XML:")
        self.stdout.write(
            xml_content[:300] + "..." if len(xml_content) > 300 else xml_content
        )

        # Step 3: Extract skills and other information
        self.stdout.write("\nStep 3: Extracting information from XML...")

        skills = extract_skills_from_xml(xml_content)
        self.stdout.write(f'Skills: {", ".join(skills)}')

        title = extract_most_recent_title(xml_content)
        self.stdout.write(f"Most recent title: {title}")

        years = calculate_years_experience(xml_content)
        self.stdout.write(f"Years of experience: {years}")

        bio = extract_bio(xml_content)
        self.stdout.write(
            f"Bio: {bio[:100]}..." if bio and len(bio) > 100 else f"Bio: {bio}"
        )

        # Total processing time
        self.stdout.write(
            self.style.SUCCESS(f"\nTotal processing time: {pdf_time + llm_time:.2f}s")
        )
        self.stdout.write(
            self.style.SUCCESS("Resume parser test completed successfully")
        )
