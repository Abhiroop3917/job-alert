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
MICROSOFT_URL = (
    "https://apply.careers.microsoft.com/careers"
    "?start=0&location=India&sort_by=recent"
    "&filter_include_remote=1&filter_seniority=Entry"
)
AMAZON_URL    = (
    "https://amazon.jobs/en/search.json?result_limit=100&sort=recent"
    "&category[]=software-development&category[]=data-science"
    "&category[]=fulfillment-warehouse-associate"
    "&category[]=machine-learning-science&category[]=systems-quality-security-engineering"
    "&category[]=operations-it-support-engineering&category[]=business-merchant-development"
    "&category[]=project-program-product-management-technical&category[]=business-intelligence"
    "&industry_experience=less_than_1_year&country=IND"
)
META_PAGE_URL = (
    "https://www.metacareers.com/jobsearch/?sort_by_new=true"
    "&offices[0]=Mumbai%2C%20India&offices[1]=Gurgaon%2C%20India"
    "&offices[2]=Bangalore%2C%20India&offices[3]=Hyderabad%2C%20India"
    "&offices[4]=New%20Delhi%2C%20India&roles[0]=Full%20time%20employment"
)
NVIDIA_URL = (
    "https://jobs.nvidia.com/api/pcsx/search"
    "?domain=nvidia.com&query=&location=India&start=0&num_rec=100"
    "&sort_by=timestamp&filter_include_remote=1"
    "&filter_job_category=engineering&filter_job_type=regular+employee"
    "&filter_time_type=full+time"
)
