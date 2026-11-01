import os

# ntfy.sh topic — set this as a GitHub Secret named NTFY_TOPIC
# Never hardcode it here if the repo is public
NTFY_TOPIC         = os.environ.get("NTFY_TOPIC", "")
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# Keywords to match (case-insensitive substring match on job title)
# Empty list = match all jobs
KEYWORDS = [
    "Software Engineer",
    "Software Engineering",
    "Machine Learning",
    "AI",
    "Artificial Intelligence",
    "Generative AI",
    "Python",
    "Backend",
    "Cloud",
    "Data",
]

# Location filter (case-insensitive substring match)
LOCATIONS = ["India"]

# Job source URLs
GOOGLE_URL    = "https://www.google.com/about/careers/applications/jobs/results?target_level=EARLY&employment_type=FULL_TIME&sort_by=date&location=India"
SERVICENOW_URL = "https://careers.servicenow.com/jobs/xml/?rss=true"
APPLE_URL     = "https://jobs.apple.com/en-in/search?sort=newest&location=india-INDC&key=Ai&lang=english-us-en_US"
DELOITTE_URL  = "https://southasiacareers.deloitte.com/search/?q=&title=Developer&sortColumn=referencedate&sortDirection=desc&searchby=location"
IBM_ENABLED   = True
