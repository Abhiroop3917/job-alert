import re

QUAL_RE = re.compile(r'"qualifications":"((?:[^"\\]|\\.)*)"')

META_GRAPHQL_URL = 'https://www.metacareers.com/graphql'
META_DOC_ID = '27129360303422352'

META_VARIABLES = {
    "search_input": {
        "q": None,
        "divisions": [],
        "offices": ["Mumbai, India", "Gurgaon, India", "Bangalore, India", "Hyderabad, India", "New Delhi, India"],
        "roles": ["Full time employment"],
        "leadership_levels": [],
        "saved_jobs": [],
        "saved_searches": [],
        "sub_teams": [],
        "teams": [],
        "is_leadership": False,
        "is_remote_only": False,
        "sort_by_new": True,
        "results_per_page": None,
    },
    "viewasUserID": None,
    "isLoggedIn": False,
}


def parse_meta_jobs(data):
    """Parse GraphQL JSON response → list of job dicts."""
    jobs = []
    all_jobs = ((data or {}).get('data') or {}).get('job_search_with_featured_jobs_v2', {}).get('all_jobs', [])
    for j in all_jobs:
        job_id = str(j.get('id', ''))
        if not job_id:
            continue
        locations = j.get('locations', [])
        location = ', '.join(locations) if locations else 'India'
        jobs.append({
            'id':       f'meta-{job_id}',
            'title':    (j.get('title') or '').strip(),
            'location': location,
            'url':      f'https://www.metacareers.com/jobs/{job_id}/',
            'source':   'Meta',
        })
    return jobs


def parse_meta_job_detail(html):
    """Extract qualifications text from a Meta job detail page HTML."""
    m = QUAL_RE.search(html)
    if not m:
        return ''
    raw = m.group(1)
    return raw.replace('\\n', '\n').replace('\\"', '"').replace('\\/', '/').replace('\\\\', '\\')
