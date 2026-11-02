import os

# ntfy.sh topic — set this as a GitHub Secret named NTFY_TOPIC
# Never hardcode it here if the repo is public
NTFY_TOPIC         = os.environ.get("NTFY_TOPIC", "")
GMAIL_ADDRESS      = os.environ.get("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")

# Keywords to match (case-insensitive substring match on job title)
# Empty list = match all jobs
KEYWORDS  = []  # URLs already handle filtering
LOCATIONS = []  # URLs already handle filtering

# Job source URLs
GOOGLE_URL    = "https://www.google.com/about/careers/applications/jobs/results?target_level=EARLY&employment_type=FULL_TIME&sort_by=date&location=India"
SERVICENOW_URL = "https://careers.servicenow.com/jobs/xml/?rss=true"
APPLE_URL     = "https://jobs.apple.com/en-in/search?sort=newest&location=india-INDC&key=Ai&lang=english-us-en_US"
DELOITTE_URL  = "https://southasiacareers.deloitte.com/search/?q=&title=Developer&sortColumn=referencedate&sortDirection=desc&searchby=location"
IBM_ENABLED   = True
AMAZON_URL    = (
    "https://amazon.jobs/en/search.json?result_limit=100&sort=recent"
    "&category[]=software-development&category[]=data-science"
    "&category[]=machine-learning-science&category[]=systems-quality-security-engineering"
    "&category[]=operations-it-support-engineering&category[]=business-merchant-development"
    "&category[]=project-program-product-management-technical&category[]=business-intelligence"
    "&industry_experience=less_than_1_year&country=IND"
)
