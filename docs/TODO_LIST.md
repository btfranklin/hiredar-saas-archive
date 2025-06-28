# Various Implementation To-Do's

## Job Seeker Enhancements

- Add a resume improvement tool
- Add a 'career coach' that builds on role recommendations
- Update the "How it works" on the homepage to show new features

## New Features

- Add some logic that outright blocks job postings that are not US-based, to steer clear of GDPR issues
- Add ability to add more candidates to an existing pool, and to create an empty pool
- Add some way for users to deactivate their accounts

## Refactors

- Clean up the whole "services" vs. "utils" issue across the codebase
- Break out all of the models.py files into models/ folders with individual model modules
- Ensure that all of the existing tasks/ folders have modules following the "one module per task, named the same as the task" pattern

## Consider these

- Add password complexity rules
- Add a "resume de-duplication" process that doesn't process duplicated resumes
- Improve error reporting when a candidate fails to process
