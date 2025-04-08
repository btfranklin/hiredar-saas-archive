import logging
from typing import Any

from django.core.management.base import BaseCommand

from apps.matching.tasks.common import get_embedding, get_index


class Command(BaseCommand):
    help = (
        "Check skills match between a job opening and talent with proper section filter"
    )

    def add_arguments(self, parser):
        parser.add_argument("job_id", type=int, help="ID of the job opening")
        parser.add_argument("talent_id", type=int, help="ID of the talent sheet")
        parser.add_argument(
            "--section-format",
            choices=["original", "lowercase", "lowercase_underscores"],
            default="original",
            help="Format to use for the section filter ('original', 'lowercase', 'lowercase_underscores')",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        job_id = options["job_id"]
        talent_id = options["talent_id"]
        section_format = options["section_format"]

        # Get the Pinecone index
        index = get_index()

        # Check if vectors exist
        job_vector_id = f"job_{job_id}_required_skills"
        talent_vector_id = f"talent_{talent_id}_skill_overview"

        self.stdout.write(f"Checking for job vector: {job_vector_id}")
        job_result = index.fetch(ids=[job_vector_id], namespace="job_openings")

        if not job_result.vectors or job_vector_id not in job_result.vectors:
            self.stdout.write(
                self.style.ERROR(f"Job vector '{job_vector_id}' not found")
            )
            return

        self.stdout.write(f"Checking for talent vector: {talent_vector_id}")
        talent_result = index.fetch(ids=[talent_vector_id], namespace="talent_sheets")

        if not talent_result.vectors or talent_vector_id not in talent_result.vectors:
            self.stdout.write(
                self.style.ERROR(f"Talent vector '{talent_vector_id}' not found")
            )
            return

        # Output existing metadata for reference
        job_metadata = job_result.vectors[job_vector_id].metadata
        talent_metadata = talent_result.vectors[talent_vector_id].metadata

        self.stdout.write(self.style.SUCCESS("\n=== Existing Metadata ==="))
        self.stdout.write(f"Job vector metadata: {job_metadata}")
        self.stdout.write(f"Talent vector metadata: {talent_metadata}")

        # Extract the actual section values
        job_section = job_metadata.get("section", "")
        talent_section = talent_metadata.get("section", "")

        self.stdout.write(self.style.SUCCESS("\n=== Actual Section Values ==="))
        self.stdout.write(f"Job section: '{job_section}'")
        self.stdout.write(f"Talent section: '{talent_section}'")

        # Prepare section filter based on the specified format
        if section_format == "lowercase":
            section_filter = talent_section.lower()
        elif section_format == "lowercase_underscores":
            section_filter = talent_section.lower().replace(" ", "_")
        else:  # original
            section_filter = talent_section

        self.stdout.write(
            self.style.SUCCESS("\n=== Testing Match with Section Filter ===")
        )
        self.stdout.write(f"Using section filter: '{section_filter}'")

        # Get job embedding (query vector)
        job_embedding = job_result.vectors[job_vector_id].values

        # Format the filter correctly
        filter_dict = {"section": section_filter}

        # Query Pinecone with the section filter
        results = index.query(
            vector=job_embedding,
            namespace="talent_sheets",
            top_k=20,
            include_metadata=True,
            filter=filter_dict,
        )

        # Process results
        self.stdout.write(f"Query with filter returned {len(results.matches)} matches")

        if not results.matches:
            self.stdout.write(self.style.WARNING("No matches found with this filter"))

            # Try without filter to verify the issue is with the filter
            self.stdout.write(
                self.style.SUCCESS("\n=== Testing Match without Filter ===")
            )
            no_filter_results = index.query(
                vector=job_embedding,
                namespace="talent_sheets",
                top_k=20,
                include_metadata=True,
            )

            self.stdout.write(
                f"Query without filter returned {len(no_filter_results.matches)} matches"
            )

            matching_vector = None
            if no_filter_results.matches:
                for match in no_filter_results.matches:
                    if match.id == talent_vector_id:
                        matching_vector = match
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"Found target talent ({match.id}) without filter at position "
                                f"{no_filter_results.matches.index(match) + 1} with score {match.score:.2f}"
                            )
                        )
                        break

                if not matching_vector:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Target talent ({talent_vector_id}) not found in the top 20 results"
                        )
                    )

            # If we found the vector without filter, print its metadata for diagnosis
            if matching_vector and hasattr(matching_vector, "metadata"):
                self.stdout.write(
                    self.style.SUCCESS("\n=== Metadata of Target Vector ===")
                )
                self.stdout.write(f"{matching_vector.metadata}")

                # Suggest correct filter format
                self.stdout.write(self.style.SUCCESS("\n=== Suggested Filter ==="))
                suggested_section = matching_vector.metadata.get("section", "")
                self.stdout.write(
                    f"Try using filter: {{'section': '{suggested_section}'}}"
                )
        else:
            # Display matches found
            self.stdout.write(self.style.SUCCESS("\n=== Top Matches ==="))
            target_found = False

            for i, match in enumerate(results.matches):
                position = i + 1
                score = match.score * 100  # Convert to percentage

                if match.id == talent_vector_id:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{position}. {match.id} (MATCH!) - Score: {score:.2f}%"
                        )
                    )
                    target_found = True
                else:
                    self.stdout.write(f"{position}. {match.id} - Score: {score:.2f}%")

                # Show metadata for the first few matches
                if i < 3:
                    self.stdout.write(f"   Metadata: {match.metadata}")

            if not target_found:
                self.stdout.write(
                    self.style.WARNING(
                        f"Target talent ({talent_vector_id}) not found in the results"
                    )
                )
