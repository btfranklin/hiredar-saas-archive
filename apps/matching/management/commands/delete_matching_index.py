import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from pinecone import PineconeApiException, PineconeException
from pinecone.grpc import PineconeGRPC as Pinecone


class Command(BaseCommand):
    """
    Delete an existing Pinecone index for the job matching system.

    This command removes a vector index from Pinecone, which is useful for
    cleaning up or recreating indexes during development or maintenance.
    """

    help = "Delete the Pinecone index for the job matching system."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force deletion without confirmation",
        )
        parser.add_argument(
            "--name",
            help="Override the index name from .env file",
        )
        parser.add_argument(
            "--project",
            default="Hiredar",
            help="Pinecone project name (default: Hiredar)",
        )

    def handle(self, *args: Any, **options: dict[str, Any]) -> None:
        # Retrieve configuration from environment variables
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise CommandError("PINECONE_API_KEY is not set in .env file.")

        # Use command-line override if provided, otherwise use .env
        name_override = options.get("name")
        index_name = str(
            name_override
            if name_override is not None
            else os.getenv("PINECONE_INDEX_NAME", "job-matcher")
        )
        project_name = options.get("project") or os.getenv(
            "PINECONE_PROJECT_NAME", "Hiredar"
        )
        force = options.get("force", False)

        self.stdout.write(
            f"Preparing to delete Pinecone index '{index_name}' from project '{project_name}'."
        )

        try:
            # Initialize Pinecone client with the API key and project
            pc = Pinecone(api_key=api_key, project_name=project_name)

            # Check if index exists
            existing_indexes = pc.list_indexes()
            if index_name not in [idx.name for idx in existing_indexes]:
                self.stdout.write(
                    self.style.WARNING(
                        f"Index '{index_name}' does not exist in project '{project_name}'. Nothing to delete."
                    )
                )
                return

            # Confirm deletion if not forced
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        f"You are about to delete the index '{index_name}' from project '{project_name}'. "
                        f"This operation cannot be undone."
                    )
                )
                confirm = input("Continue? [y/N]: ")
                if confirm.lower() not in ["y", "yes"]:
                    self.stdout.write("Operation cancelled.")
                    return

            # Delete the index
            pc.delete_index(index_name)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Index '{index_name}' deleted successfully from project '{project_name}'."
                )
            )
        except PineconeApiException as e:
            raise CommandError(f"Pinecone API error: {e}") from e
        except PineconeException as e:
            raise CommandError(f"Pinecone error: {e}") from e
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}") from e
