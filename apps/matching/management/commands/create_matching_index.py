import os
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from pinecone import PineconeApiException, PineconeException, ServerlessSpec
from pinecone.grpc import PineconeGRPC as Pinecone


class Command(BaseCommand):
    """
    Create a new Pinecone index for the job matching system.

    This command initializes a new vector index in Pinecone with the
    specified configuration for storing and searching job embeddings.
    """

    help = "Create Pinecone index for the job matching system."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--cloud",
            default="aws",
            choices=["aws", "gcp", "azure"],
            help="Cloud provider to host the index (default: aws)",
        )
        parser.add_argument(
            "--region",
            default="us-east-1",
            help="Region to host the index (default: us-east-1)",
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

        index_name = os.getenv("PINECONE_INDEX_NAME", "job-matcher")
        project_name = options.get("project") or os.getenv(
            "PINECONE_PROJECT_NAME", "Hiredar"
        )

        # Get dimension with validation
        dimension_str = os.getenv("PINECONE_DIMENSIONS", "3072")
        try:
            dimension = int(dimension_str)
            if dimension <= 0:
                raise CommandError(
                    f"PINECONE_DIMENSIONS must be a positive integer, got {dimension}"
                )
        except ValueError as e:
            raise CommandError(
                f"PINECONE_DIMENSIONS must be a valid integer, got '{dimension_str}'"
            ) from e

        metric = "cosine"
        cloud = str(options.get("cloud", "aws"))
        region = str(options.get("region", "us-east-1"))

        self.stdout.write(
            f"Creating Pinecone index '{index_name}' in project '{project_name}' with dimension {dimension}, "
            f"metric '{metric}' in {cloud}/{region}."
        )

        try:
            # Initialize Pinecone client with the API key and project
            pc = Pinecone(api_key=api_key, project_name=project_name)

            # Check if index already exists
            existing_indexes = pc.list_indexes()
            if index_name in [idx.name for idx in existing_indexes]:
                self.stdout.write(
                    self.style.WARNING(
                        f"Index '{index_name}' already exists in project '{project_name}'. Skipping creation."
                    )
                )
                return

            # Define a serverless spec
            spec = ServerlessSpec(cloud=cloud, region=region)

            # Create the index
            pc.create_index(
                name=index_name, dimension=dimension, metric=metric, spec=spec
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Index '{index_name}' created successfully in project '{project_name}'."
                )
            )
        except PineconeApiException as e:
            raise CommandError(f"Pinecone API error: {e}") from e
        except PineconeException as e:
            raise CommandError(f"Pinecone error: {e}") from e
        except Exception as e:
            raise CommandError(f"Unexpected error: {e}") from e
