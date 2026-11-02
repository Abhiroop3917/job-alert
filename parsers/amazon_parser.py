import re

# Amazon's JSON API ignores the industry_experience=less_than_1_year URL filter.
# We filter by parsing the basic_qualifications text instead:
#   - keep jobs where max year requirement <= 2 (SDE I / SDE II)
#   - keep jobs with no year pattern at all (PhD/research roles with no year floor)
_YEAR_RE = re.compile(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', re.IGNORECASE)
_MAX_YEARS = 2


def _is_entry_level(basic_qualifications):
    bq = re.sub(r'<[^>]+>', ' ', basic_qualifications or '')
    years = [int(n) for n in _YEAR_RE.findall(bq)]
    if not years:
        return True
    return max(years) <= _MAX_YEARS


def parse_amazon_jobs(data):
    jobs = []
    for j in data.get('jobs', []):
        jid = str(j.get('id_icims', ''))
        if not jid:
            continue
        if not _is_entry_level(j.get('basic_qualifications', '')):
            continue
        jobs.append({
            'id':       f'amazon-{jid}',
            'title':    j.get('title', '').strip(),
            'location': j.get('location', ''),
            'url':      f"https://amazon.jobs{j.get('job_path', '')}",
            'posted':   j.get('posted_date', ''),
            'source':   'Amazon',
        })
    return jobs
