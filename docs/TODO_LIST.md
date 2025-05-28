# Various Implementation To-Do's

- Add some way for users to deactivate their accounts
- Finish converting all the UI elements to DaisyUI v5 (from v4)
- Create some kind of standardized "back" button for navigation
- Add some logic that outright blocks job postings that are not US-based, to steer clear of GDPR issues
- Add ability to add more candidates to an existing pool, and to create an empty pool
- Break out all of the models.py files into models/ folders with individual model modules
- Ensure that all of the existing tasks/ folders have modules following the "one module per task, named the same as the task" pattern
- Clean up the whole "services" vs. "utils" issue across the codebase
- Fix the "user dropdown" menu
- Add a "Give Us Feedback" button in the header
- Fix the double-bar on the match view
- Add resume view on the match view

## Consider these

- Add password complexity rules
- Add a "resume de-duplication" process that doesn't process duplicted resumes
- Improve error reporting when a candidate fails to process

## In Progress

- Sign-up and log-in with LinkedIn
  - Need to make sure name gets set from Oauth, not left as "New User"
