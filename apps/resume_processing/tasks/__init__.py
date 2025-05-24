"""Resume-processing task package.

Celery's Django integration will automatically import ``apps.resume_processing.tasks``
for task discovery.  When this directory lacked an ``__init__`` module the import
worked thanks to Python's *namespace-package* semantics, but none of the actual
task functions living in the sibling modules were brought into memory – which
meant the Celery worker never registered them.

To ensure every task is visible we explicitly import each sub-module here and
re-export their public callables via ``__all__``.  Keep this list in sync when
adding new task modules.
"""

# ---------------------------------------------------------------------------
#  Public sub-modules
# ---------------------------------------------------------------------------

from apps.resume_processing.tasks.cleanup_tasks import (
    cleanup_resume_processing_progress,  # noqa: F401 – re-export
)
from apps.resume_processing.tasks.resume_processing_tasks import (  # noqa: F401 – re-export
    handle_resume_upload_task,
    save_resume_file,
)

# The public names that are meant to be imported when users run
# ``from apps.resume_processing import tasks`` or
# ``from apps.resume_processing.tasks import *``.

__all__ = [
    # Resume-processing helpers
    "save_resume_file",
    "handle_resume_upload_task",
    # Cleanup helpers
    "cleanup_resume_processing_progress",
]
