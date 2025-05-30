# Various Implementation To-Do's

## New Features

- Add some way for users to deactivate their accounts
- Create some kind of standardized "back" button for navigation
- Add some logic that outright blocks job postings that are not US-based, to steer clear of GDPR issues
- Add ability to add more candidates to an existing pool, and to create an empty pool

## Refactors

- Clean up the whole "services" vs. "utils" issue across the codebase
- Break out all of the models.py files into models/ folders with individual model modules
- Ensure that all of the existing tasks/ folders have modules following the "one module per task, named the same as the task" pattern

## Quick wins

- Fix the "user dropdown" menu
- Add a "Give Us Feedback" button in the header

## Consider these

- Add password complexity rules
- Add a "resume de-duplication" process that doesn't process duplicted resumes
- Improve error reporting when a candidate fails to process
