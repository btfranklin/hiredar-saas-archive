"""
Management command to list vector IDs and metadata in Pinecone.

This is a diagnostic command to help understand what's in the vector database.
"""

import logging
from typing import Any

from django.core.management.base import BaseCommand

from apps.matching.tasks.common import get_index


class Command(BaseCommand):
    """List vectors in Pinecone by namespace and optionally filter by section."""

    help = "Lists all namespaces and vectors in Pinecone"

    def handle(self, *args: Any, **options: Any) -> None:
        """Execute the command."""
        try:
            pinecone_index = get_index()

            # Get stats about the index
            stats = pinecone_index.describe_index_stats()

            # Display all namespaces
            self.stdout.write(self.style.SUCCESS("=== Pinecone Index Stats ==="))
            self.stdout.write(f"Total vector count: {stats.total_vector_count}")
            self.stdout.write(f"Dimension: {stats.dimension}")

            self.stdout.write(self.style.SUCCESS("\n=== Namespaces ==="))

            if not stats.namespaces:
                self.stdout.write("No namespaces found")
            else:
                for namespace, details in stats.namespaces.items():
                    self.stdout.write(f"\nNamespace: {namespace}")
                    self.stdout.write(f"  Vector count: {details.vector_count}")

                    # Fetch some vector IDs from this namespace
                    if details.vector_count > 0:
                        self.stdout.write("  Sample vector IDs:")
                        try:
                            # The list method returns batches of vector IDs
                            for batch in pinecone_index.list(
                                namespace=namespace, limit=100
                            ):
                                # Each batch is a list of vector IDs
                                for vector_id in batch:
                                    # Print vector ID with section and entity information if available
                                    if "_" in vector_id:
                                        parts = vector_id.split("_")
                                        if len(parts) >= 3 and parts[0] in [
                                            "job",
                                            "talent",
                                        ]:
                                            entity_type = parts[0]
                                            entity_id = parts[1]
                                            section = "_".join(parts[2:])
                                            self.stdout.write(
                                                f"    - {vector_id} ({entity_type} {entity_id}, section: {section})"
                                            )
                                        else:
                                            self.stdout.write(f"    - {vector_id}")
                                    else:
                                        self.stdout.write(f"    - {vector_id}")
                                break  # Only print the first batch
                        except Exception as list_error:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  Error listing vectors: {str(list_error)}"
                                )
                            )

                            # Try an alternative approach using a dummy query
                            try:
                                self.stdout.write(
                                    "  Trying alternative method to list vectors..."
                                )
                                # Create a dummy vector with the right dimensions
                                dimensions = stats.dimension
                                dummy_vector = [0.0] * dimensions
                                dummy_vector[0] = 0.1  # One non-zero value

                                # Query with the dummy vector to get IDs
                                results = pinecone_index.query(
                                    namespace=namespace,
                                    top_k=20,
                                    include_metadata=True,
                                    vector=dummy_vector,
                                )

                                if hasattr(results, "matches") and results.matches:
                                    for match in results.matches:
                                        vector_id = match.id
                                        metadata = getattr(match, "metadata", {})
                                        section = metadata.get("section", "N/A")
                                        self.stdout.write(
                                            f"    - {vector_id} (section: {section})"
                                        )
                                else:
                                    self.stdout.write(
                                        "    No vectors found with query method"
                                    )
                            except Exception as query_error:
                                self.stdout.write(
                                    self.style.ERROR(
                                        f"  Error with query method: {str(query_error)}"
                                    )
                                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
