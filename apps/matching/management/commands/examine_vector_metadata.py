"""
Management command to examine vector metadata in Pinecone.

This command fetches specific vectors by ID from Pinecone and dumps their
metadata structure to help diagnose filtering issues.
"""

import logging
from typing import Any

from django.core.management.base import BaseCommand
from pinecone.openapi_support.exceptions import NotFoundException

from apps.matching.tasks.common import get_index


class Command(BaseCommand):
    """Examine vector metadata in Pinecone."""

    help = "Examine the metadata structure of a vector in Pinecone and test various filter formats"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "vector_id",
            type=str,
            help="ID of the vector to fetch",
        )
        parser.add_argument(
            "--namespace",
            type=str,
            default="talent_sheets",
            help="Namespace to fetch from (default: talent_sheets)",
        )
        parser.add_argument(
            "--list-namespaces",
            action="store_true",
            help="List all available namespaces before fetching the vector",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        vector_id = options["vector_id"]
        namespace = options["namespace"]
        list_namespaces = options["list_namespaces"]

        try:
            index = get_index()

            # List namespaces if requested
            if list_namespaces:
                self.stdout.write(self.style.SUCCESS("=== Available Namespaces ==="))
                stats = index.describe_index_stats()
                for ns_name, ns_details in stats.namespaces.items():
                    self.stdout.write(f"{ns_name} ({ns_details.vector_count} vectors)")
                self.stdout.write("\n")

            self.stdout.write(
                f"Fetching vector '{vector_id}' from namespace '{namespace}'"
            )

            # Try to fetch the vector
            try:
                vector_data = index.fetch(ids=[vector_id], namespace=namespace)

                if not vector_data.vectors:
                    self.stdout.write(
                        f"Vector '{vector_id}' not found in namespace '{namespace}'"
                    )
                    return

                vector = vector_data.vectors.get(vector_id)
                if not vector:
                    self.stdout.write(f"Vector '{vector_id}' returned empty result")
                    return

                # Print the metadata structure
                self.stdout.write(
                    self.style.SUCCESS("\n=== Vector Metadata Structure ===")
                )
                self.stdout.write("Metadata:")

                # Get metadata if it exists
                metadata = getattr(vector, "metadata", {})

                if metadata:
                    for key, value in metadata.items():
                        # Print the key, value, and the Python type of the value
                        self.stdout.write(
                            f"  {key}: {value} (type: {type(value).__name__})"
                        )
                else:
                    self.stdout.write("  No metadata found")

                # Print vector information
                self.stdout.write(self.style.SUCCESS("\n=== Vector Info ==="))
                self.stdout.write(f"ID: {vector_id}")

                # Print raw vector data
                self.stdout.write(self.style.SUCCESS("\n=== Raw Vector Data ==="))
                self.stdout.write(str(vector))

                # Test different filter formats to see which ones work
                self.stdout.write(
                    self.style.SUCCESS("\n=== Testing Filter Queries ===")
                )

                # Get the section value from metadata if it exists
                section_value = metadata.get("section", "unknown")

                # Test filters with different formats
                filters_to_test = [
                    {"section": "skill_overview"},
                    {"section": "Skill Overview"},
                    {"section": "SKILL_OVERVIEW"},
                    {"metadata": {"section": "skill_overview"}},
                    None,  # No filter
                ]

                for filter_dict in filters_to_test:
                    try:
                        # Create a dummy vector for querying
                        dimensions = len(vector.values)
                        dummy_vector = [0.0] * dimensions
                        dummy_vector[0] = 0.1  # Set non-zero value

                        # Print the filter we're testing
                        filter_str = (
                            str(filter_dict) if filter_dict else "None (no filter)"
                        )
                        self.stdout.write(f"\nTesting filter: {filter_str}")

                        # Execute query with filter
                        results = index.query(
                            vector=dummy_vector,
                            namespace=namespace,
                            top_k=5,
                            include_metadata=True,
                            filter=filter_dict,
                        )

                        # Print results
                        self.stdout.write(
                            f"  Query returned {len(results.matches)} results"
                        )

                        # Check if our target vector is in the results
                        found = False
                        for match in results.matches:
                            if match.id == vector_id:
                                self.stdout.write(
                                    f"  ✓ Target vector found with score: {match.score}"
                                )
                                found = True
                                break

                        if not found and results.matches:
                            self.stdout.write("  ✗ Target vector not found in results")

                    except Exception as e:
                        self.stdout.write(
                            f"  Error with filter {filter_dict}: {str(e)}"
                        )

            except NotFoundException:
                self.stdout.write(
                    f"Vector '{vector_id}' not found in namespace '{namespace}'"
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
