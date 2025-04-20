"""
Management command to diagnose resume parsing issues and test the resume parsing functionality.

Usage:
    python manage.py diagnose_resume /path/to/test/resume.pdf
"""

import logging
import os
import sys
import time
import xml.etree.ElementTree as ET

from django.core.management.base import BaseCommand

from apps.resume_processing.utils.extraction import extract_text_from_pdf
from apps.resume_processing.utils.llm_processor import convert_text_to_xml
from apps.resume_processing.utils.xml_error_reporting import (
    format_error_for_console,
    save_diagnostic_xml,
)
from apps.resume_processing.utils.xml_parser import parse_resume_xml

# Setup logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Diagnose resume parsing issues and test the functionality with a sample resume"
    )

    def add_arguments(self, parser):
        # Optional path to a test resume PDF
        parser.add_argument(
            "resume_path",
            nargs="?",
            type=str,
            help="Path to a sample resume PDF file for diagnostics",
        )

        # Add option to save XML to file
        parser.add_argument(
            "--save-xml",
            action="store_true",
            help="Save the generated XML to a file",
        )

        # Option to continue on error instead of exiting
        parser.add_argument(
            "--continue-on-error",
            action="store_true",
            help="Continue processing even if steps fail (default is to exit on first error)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting resume parsing diagnostic"))

        resume_path = options.get("resume_path")
        save_xml = options.get("save_xml", False)
        continue_on_error = options.get("continue_on_error", False)

        if not resume_path:
            self.stdout.write(
                self.style.WARNING("No resume path provided. Using sample test data.")
            )
            # You could load sample test data here
            return

        if not os.path.exists(resume_path):
            self.stdout.write(self.style.ERROR(f"Resume file not found: {resume_path}"))
            sys.exit(1)

        # Step 1: Extract text from PDF
        self.stdout.write("Step 1: Extracting text from PDF...")
        start_time = time.time()
        raw_text = ""  # Initialize with empty string to avoid None

        try:
            raw_text = extract_text_from_pdf(resume_path)
            if not raw_text:
                self.stdout.write(
                    self.style.ERROR("Failed to extract text from PDF (empty result)")
                )
                if not continue_on_error:
                    sys.exit(1)
                raw_text = ""  # Ensure it's not None
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error extracting text from PDF: {e}"))
            if not continue_on_error:
                sys.exit(1)
            raw_text = ""  # Ensure it's not None

        pdf_time = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f"Text extracted successfully ({pdf_time:.2f}s)")
        )
        self.stdout.write(f"Extracted {len(raw_text)} characters")
        self.stdout.write("Sample text:")
        sample_text = raw_text[:300] + "..." if len(raw_text) > 300 else raw_text
        self.stdout.write(sample_text)

        # Step 2: Use LLM to convert raw text to structured XML
        self.stdout.write("\nStep 2: Converting to XML with LLM...")
        start_time = time.time()
        xml_content = "<resume></resume>"  # Initialize with minimal valid XML

        try:
            xml_content = convert_text_to_xml(raw_text)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating XML: {e}"))
            if not continue_on_error:
                sys.exit(1)
            # xml_content already has minimal default value

        llm_time = time.time() - start_time
        self.stdout.write(
            self.style.SUCCESS(f"XML generated successfully ({llm_time:.2f}s)")
        )
        self.stdout.write(f"XML length: {len(xml_content)} characters")

        # Optionally save the XML to a file for inspection
        if save_xml:
            xml_file_path = resume_path + ".xml"
            try:
                with open(xml_file_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                self.stdout.write(self.style.SUCCESS(f"Saved XML to {xml_file_path}"))
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"Failed to save XML to file: {e}")
                )

        # Display a preview of the XML
        self.stdout.write("Sample XML:")
        sample_xml = (
            xml_content[:500] + "..." if len(xml_content) > 500 else xml_content
        )
        self.stdout.write(sample_xml)

        # Validate XML structure
        try:
            root = ET.fromstring(xml_content)
            if root.tag != "resume":
                self.stdout.write(
                    self.style.WARNING(f"Root element is '{root.tag}', not 'resume'")
                )
        except ET.ParseError as e:
            self.stdout.write(self.style.ERROR(f"XML validation error: {e}"))

            # Use centralized error reporting to show detailed error location
            self.stdout.write("\n")  # Add a newline for clarity
            for line in format_error_for_console(e, xml_content):
                self.stdout.write(self.style.ERROR(line))

            # Save the failed XML to a file with error indicators
            error_xml_path = save_diagnostic_xml(e, xml_content, resume_path, "parsing")
            if error_xml_path:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Saved XML with error markers to {error_xml_path}"
                    )
                )

            if not continue_on_error:
                sys.exit(1)

        # Step 3: Extract information from XML using the parser
        self.stdout.write("\nStep 3: Parsing XML to extract structured data...")
        start_time = time.time()
        resume_data = {}  # Initialize with empty dict

        try:
            resume_data = parse_resume_xml(xml_content)
            parse_time = time.time() - start_time
            self.stdout.write(
                self.style.SUCCESS(f"XML parsed successfully ({parse_time:.2f}s)")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error parsing XML: {e}"))
            parse_time = time.time() - start_time
            if not continue_on_error:
                sys.exit(1)
            # resume_data already has empty dict default value

        # Display extracted information
        if resume_data.get("skills"):
            skills_preview = (
                resume_data["skills"][:100] + "..."
                if len(resume_data["skills"]) > 100
                else resume_data["skills"]
            )
            self.stdout.write(f"Skills: {skills_preview}")
        else:
            self.stdout.write(self.style.WARNING("No skills were extracted"))

        if resume_data.get("most_recent_title"):
            self.stdout.write(f"Most recent title: {resume_data['most_recent_title']}")
        else:
            self.stdout.write(self.style.WARNING("No most recent title found"))

        if resume_data.get("years_of_experience") is not None:
            self.stdout.write(
                f"Years of experience: {resume_data['years_of_experience']}"
            )
        else:
            self.stdout.write(
                self.style.WARNING("No years of experience were calculated")
            )

        if resume_data.get("professional_summary"):
            bio = resume_data["professional_summary"]
            bio_summary = (
                f"Summary: {bio[:100]}..."
                if bio and len(bio) > 100
                else f"Summary: {bio}"
            )
            self.stdout.write(bio_summary)
        else:
            self.stdout.write(
                self.style.WARNING("No professional summary was extracted")
            )

        # Education is now a formatted string
        self.stdout.write("\nEducation:")
        if resume_data.get("education"):
            # Show a preview or the entire education section
            education_preview = (
                resume_data["education"][:200] + "..."
                if len(resume_data["education"]) > 200
                else resume_data["education"]
            )
            for line in education_preview.splitlines():
                self.stdout.write(f"  {line}")
            if len(resume_data["education"]) > 200:
                self.stdout.write("  ... (more education details available)")
        else:
            self.stdout.write(
                self.style.WARNING("  No education information was extracted")
            )

        # Display personal details (still a dictionary)
        self.stdout.write("\nPersonal Details:")
        personal_details = resume_data.get("personal_details", {})
        if personal_details:
            for field, value in personal_details.items():
                if value:
                    self.stdout.write(f"  {field.capitalize()}: {value}")
                else:
                    self.stdout.write(self.style.WARNING(f"  No {field} extracted"))
        else:
            self.stdout.write(self.style.WARNING("  No personal details extracted"))

        # Experience is already a formatted string
        self.stdout.write("\nExperience:")
        if resume_data.get("experience"):
            # Show a preview for readability
            experience_preview = (
                resume_data["experience"][:300] + "..."
                if len(resume_data["experience"]) > 300
                else resume_data["experience"]
            )
            for line in experience_preview.splitlines():
                self.stdout.write(f"  {line}")
            if len(resume_data["experience"]) > 300:
                self.stdout.write("  ... (more experience details available)")
        else:
            self.stdout.write(
                self.style.WARNING("  No experience information extracted")
            )

        # Certifications is now a formatted string
        self.stdout.write("\nCertifications:")
        if resume_data.get("certifications"):
            # Show a preview or the entire certifications section
            certifications_preview = (
                resume_data["certifications"][:200] + "..."
                if len(resume_data["certifications"]) > 200
                else resume_data["certifications"]
            )
            for line in certifications_preview.splitlines():
                self.stdout.write(f"  {line}")
            if len(resume_data["certifications"]) > 200:
                self.stdout.write("  ... (more certification details available)")
        else:
            self.stdout.write(self.style.WARNING("  No certifications extracted"))

        # Total processing time
        total_time = pdf_time + llm_time + parse_time
        self.stdout.write(
            self.style.SUCCESS(f"\nTotal processing time: {total_time:.2f}s")
        )

        # Final status report
        missing_data = []
        if not resume_data.get("skills"):
            missing_data.append("skills")
        if not resume_data.get("most_recent_title"):
            missing_data.append("most recent title")
        if resume_data.get("years_of_experience") is None:
            missing_data.append("years of experience")

        if missing_data:
            self.stdout.write(
                self.style.WARNING(
                    f"Resume parsed with missing data: {', '.join(missing_data)}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Resume parsed successfully with all essential data extracted"
                )
            )

        # Check for common issues
        self.stdout.write(self.style.NOTICE("\n4. Validation:"))

        # Check if skills were extracted
        if not resume_data.get("skills"):
            self.stdout.write(self.style.ERROR("✕ No skills were extracted"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Skills were extracted"))

        # Check for current position
        if not resume_data.get("most_recent_title"):
            self.stdout.write(self.style.ERROR("✕ No most recent title was extracted"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ Most recent title was extracted"))
