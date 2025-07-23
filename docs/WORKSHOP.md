# Job Seeker Workshop Tools

Hiredar’s **Workshop** provides a set of free, AI-powered utilities that help candidates polish their professional brand before they ever apply for a role.  These tools live directly in the web app under **Job Seekers → Workshop** and are available to every job-seeker account at no cost.

---

## Available Tools

| Tool | What it Does | Daily Usage Limit |
|------|--------------|------------------|
| **Upgrade My Resume** | Rewrites your resume to highlight quantified achievements, clarify impact, and subtly align wording to any roles you’ve marked as **Interested In**.  The output follows a modern, ATS-friendly format using Markdown headings so it can be copied, downloaded, or directly applied to your profile. | `JOBSEEKERS_WORKSHOP_DAILY_LIMIT` (default **10**)|
| **Optimize My LinkedIn** | Generates a compelling LinkedIn **Headline** (≤220 chars) and an engaging **About** section (≤2 600 chars) based on your profile and target roles. | `JOBSEEKERS_WORKSHOP_LINKEDIN_DAILY_LIMIT` (default **10**) |

> ℹ️ Daily limits reset every 24 hours UTC.  The quota is enforced server-side via Django’s cache so users cannot bypass it client-side.

---

## How to Use Each Tool

### 1 · Upgrade My Resume

1. Navigate to **Workshop → Upgrade My Resume**.
2. Click **Upgrade Resume**.  The button shows a spinner while the LLM works (~5–10 s).
3. Review the upgraded version rendered on the page.
4. Choose one of the follow-up actions:
   * **Download** – saves the Markdown as `upgraded_resume.txt`.
   * **Use This Version** – triggers the same ingestion pipeline as a normal resume upload so your profile, talent sheet, and downstream features stay in sync.

### 2 · Optimize My LinkedIn

1. Navigate to **Workshop → Optimize My LinkedIn**.
2. Press **Generate** to create a new Headline & About section.
3. Copy the text straight into LinkedIn (or save it for later).

---

## Under the Hood (Developers)

* **Service layer** – `apps/job_seekers/services/workshop_service.py` handles prompt loading, chat-completion requests, and markdown parsing.
* **Prompts** live in `apps/job_seekers/services/prompts/`:
  * `upgrade_resume.prompt.md`
  * `optimize_linkedin.prompt.md`
* **Rate-limiting** – helper functions in `apps/job_seekers/views/workshop_views.py` increment counters stored in the default Django cache (`CACHE_URL`).
* **Environment variables** (all optional; sensible defaults are baked into `settings.py`):

  ```bash
  # Model selection
  JOBSEEKERS_WORKSHOP_UPGRADE_MODEL="gpt-4o"
  JOBSEEKERS_WORKSHOP_LINKEDIN_MODEL="gpt-4o"

  # Temperature controls
  JOBSEEKERS_WORKSHOP_UPGRADE_TEMPERATURE=0.7
  JOBSEEKERS_WORKSHOP_LINKEDIN_TEMPERATURE=0.7

  # Quotas
  JOBSEEKERS_WORKSHOP_DAILY_LIMIT=10
  JOBSEEKERS_WORKSHOP_LINKEDIN_DAILY_LIMIT=10
  ```

---

## Future Ideas

* **Interview Prep** – Behavioural and technical question generator.
* **Portfolio Review** – AI feedback on personal websites or project repositories.
