# Asynchronous Task Polling – How-to

This project shows live progress for long-running background jobs (Django-Q)
without page reloads.  The pattern relies on three reusable building blocks:

1. `TaskMeta` model (apps/core/models.py) – one row per async job.
2. Generic HTMX component (`recruiters/components/pool_card*.html`) – shows
   spinners / progress and polls its own status.
3. Tiny status endpoint (`CandidatePoolStatusView`) that just re-renders the
   component fragment.

Follow the steps below **every time you add a new async job that should be
visible in the UI**.

---

## 1  Create or locate the *owner* object

Every `TaskMeta` row is *owned* by **one** model instance via
`content_object` (GenericForeignKey).  Typical owners:

* `CandidatePool` – bulk resume upload processing (already wired-up)
* `JobOpening`   – candidate matching
* `TalentSheet`  – LLM generation, etc.

If the owner row does **not** exist yet (e.g. bulk upload just started) create
it **before** you enqueue any background tasks so the dashboard has something
to render right away.

```python
candidate_pool = CandidatePool.objects.create(
    recruiter=request.user,
    name="April 2025 upload",
)
```

---

## 2  Insert a *placeholder* `TaskMeta`

This row drives the initial spinner.  Use a semantic `queue_id` so logs stay
readable, e.g. `import-<bulk_pk>`.

```python
from apps.core.models import TaskMeta

placeholder = TaskMeta.objects.create(
    queue_id=f"import-{bulk.pk}",
    name="Importing resumes",
    owner=request.user,
    content_object=candidate_pool,
    state=TaskMeta.State.PENDING,
)
```

### Why a placeholder?
* The browser starts polling immediately (pool.has_active_tasks == True).
* Once the real worker starts it flips the row to RUNNING / SUCCESS / FAILURE.

---

## 3  Enqueue the *real* task and **pass the owner id** (plus `meta_pk` when you
    want to update the placeholder)

```python
safe_async_task(
    unpack_and_process_zip,
    bulk.pk,
    candidate_pool.pk,      # pool_id -> reuse existing pool
    str(placeholder.pk),    # meta_pk  -> update placeholder state
)
```

Inside the worker, update the placeholder at key milestones:

```python
if meta_pk:
    meta = TaskMeta.objects.get(pk=meta_pk)
    meta.state = TaskMeta.State.RUNNING
    meta.save(update_fields=["state"])

# … do the heavy work …

meta.state    = TaskMeta.State.SUCCESS  # or FAILURE
meta.progress = 100
meta.save(update_fields=["state", "progress"])
```

For per-file or per-subtask work you can create additional `TaskMeta` rows with
friendly `queue_id`s like `resume-<resume_pk>` – the pool card will list all of
them automatically (`pool.active_tasks`).

---

## 4  Add / reuse a **template component**

For any owner object you display in the UI, wrap its markup with the HTMX
attributes that make it *self-poll*:

```django
<div
  id="job-opening-{{ job.pk }}"
  hx-get="{% url 'jobs:status_fragment' job.pk %}"
  hx-trigger="load{% if job.has_active_tasks %}, every 5s{% endif %}"
  hx-swap="innerHTML"
>
  {% include 'jobs/components/job_card_body.html' with job=job %}
</div>
```

Inside `job_card_body.html` iterate over `job.active_tasks` to show spinners.

### Helper properties
Add to the owner model (pattern shown on `CandidatePool`):

```python
from django.contrib.contenttypes.fields import GenericRelation
from apps.core.models import TaskMeta

class JobOpening(models.Model):
    tasks = GenericRelation(TaskMeta, related_query_name="job_openings")

    @property
    def active_tasks(self):
        return self.tasks.filter(state__in=(TaskMeta.State.PENDING,
                                            TaskMeta.State.RUNNING))

    @property
    def has_active_tasks(self):
        return self.active_tasks.exists()
```

---

## 5  Status endpoint (HTMX fragment view)

For each page section create a lightweight view that returns only the card's
HTML.  Example (`CandidatePoolStatusView`):

```python
class JobStatusFragment(LoginRequiredMixin, TemplateView):
    template_name = "jobs/components/job_card_body.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["job"] = get_object_or_404(JobOpening, pk=self.kwargs["pk"],
                                        recruiter=self.request.user)
        return ctx
```

The fragment automatically stops polling once `has_active_tasks` is False.

---

## 6  Log hygiene

* Use semantic `queue_id`s (e.g. `resume-1234`, `match-5678`) when creating
  `TaskMeta` rows **before** enqueueing the job.
* After you receive the real queue id from `safe_async_task` feel free to
  overwrite `meta.queue_id` so staff can cross-reference with Django-Q's admin.

---

## 7  Troubleshooting checklist

1. **Card never appears** – did you create the owner object synchronously?
2. **Spinner never stops** – make sure every code path in the worker updates
   `TaskMeta.state` to SUCCESS or FAILURE.
3. **Duplicate key error on `queue_id`** – guarantee uniqueness (semantic id +
   primary-key is easiest).

---

Happy async-task wiring!  Whenever you forget the steps:
Create owner → placeholder TaskMeta → enqueue task with `pool_id` & `meta_pk` →
update states in the worker → enjoy auto-refreshing UI. 