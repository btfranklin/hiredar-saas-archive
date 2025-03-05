# Hiredar

Our AI-powered job matching platform revolutionizes hiring by eliminating the noise and inefficiencies of traditional job searching. Job seekers create rich, detailed profiles for free, while recruiters pay for access to curated candidate lists tailored to their job postings. Unlike other platforms, our AI engine doesn’t just rank candidates—-it explains why they’re a great fit, providing recruiters with clear, data-backed insights. We also introduce *multiple candidate views*, including top matches and wildcard selections, ensuring hidden talent isn’t overlooked. With *no ghost jobs* and *AI-driven transparency*, we streamline the hiring process for both sides, making recruitment faster, smarter, and fairer.

Elevator Pitch:

Finding the right job—-or the right hire—-shouldn’t feel like a broken system. Our AI-driven recruitment platform levels the playing field by allowing job seekers to create rich, free profiles, while recruiters gain access to curated, data-driven candidate lists. Unlike traditional job boards, we don’t just show résumés; we explain why candidates are a great fit, offering *multiple match views* that surface both top talent and hidden gems. No more endless applications. No more ghost jobs. Just smarter, fairer hiring for everyone.

## Example User Flows

### Recruiter User Flow

1. Onboarding & Sign-Up:
The recruiter visits the Welcome & Sign-Up Screen, selects "Sign Up as Recruiter," and enters their email and basic details.
After account creation, they are directed to the Recruiter Dashboard.
2. Job Opening Creation:
From the dashboard, the recruiter clicks “Create New Job Opening.”
They fill in job details (title, description, required skills, and advanced criteria) on the Job Posting Creation Screen and then hit Create Job Opening.”
The system confirms the job opening is saved and immediately begins matching candidates using the AI engine.
3. Reviewing Candidate Matches:
The recruiter navigates to the Candidate List Screen via the dashboard.
They see a segmented list with “Top Matches” and “Wildcard Candidates” for the newly posted job.
Sorting and filtering options allow them to focus on key criteria (e.g., years of experience, specific skills).
4. Candidate Details & Engagement:
The recruiter clicks on a candidate card to open the Candidate Detail Screen.
The screen shows detailed profile information along with an AI-generated explanation for the match.
The recruiter uses action buttons to send a message or schedule an interview directly through the platform.
5. Account Management:
The recruiter accesses the Account & Settings Screen to update billing information or modify notification settings as needed.

### Job Seeker User Flow

1. Onboarding & Sign-Up:
The job seeker lands on the Welcome & Sign-Up Screen and selects “Sign Up as Job Seeker.”
They create an account using their email (or social login) and are then guided to the Profile Creation Screen.
2. Profile Creation:
On the Profile Creation Screen, the job seeker uploads a PDF of a résumé, which is used to extract all the relevant information about them.
After the PDF has processed, they are taken to the Job Seeker Dashboard.
3. Dashboard & Role Recommendations:
Here, they see a summary of their profile and an AI-generated personal tagline, and a list of role recommendations with brief AI-generated explanations (e.g., “Your 5 years in project management align well with a Project Manager role”). These are conceptual roles, not specific job listings.
They can click on a role card to view more details about that type of role.
4. Profile Updates & Notifications:
The job seeker can return to the Dashboard at any time to check notifications, such as messages sent by recruiters in response to matches.
They can also visit the Profile & Settings Screen to update their information or adjust notification preferences.

## Tech Stack

- Django for serving pages and API
- Allauth Django plugin for user auth management
- HTMX for interactivity
- TailwindCSS with DaisyUI for UI styling
- Django Q2 for asynchronous task processing
