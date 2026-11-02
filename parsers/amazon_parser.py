import re

# Amazon's JSON API ignores the industry_experience=less_than_1_year URL filter.
# We filter by parsing the basic_qualifications text instead:
#   - keep jobs where max year requirement <= 2 (SDE I / SDE II)
#   - keep jobs with no year pattern at all (PhD/research roles with no year floor)
_YEAR_RE = re.compile(r'(\d+)\+?\s*(?:to\s*\d+\s*)?years?', re.IGNORECASE)
_MAX_YEARS = 2


def _max_years_in_text(text):
    """Return the highest year number found in text, or 0 if none found."""
    cleaned = re.sub(r'<[^>]+>', ' ', text or '')
    nums = [int(n) for n in _YEAR_RE.findall(cleaned)]
    return max(nums) if nums else 0


def _is_entry_level(basic_qualifications, description):
    """True if both basic_qualifications and description pass the year threshold."""
    bq_max   = _max_years_in_text(basic_qualifications)
    desc_max = _max_years_in_text(description)
    # Use whichever field is stricter (higher year requirement)
    max_req = max(bq_max, desc_max)
    if max_req == 0:
        return True   # no year requirement found in either field → include
    return max_req <= _MAX_YEARS


def parse_amazon_jobs(data):
    jobs = []
    for j in data.get('jobs', []):
        jid = str(j.get('id_icims', ''))
        if not jid:
            continue
        if not _is_entry_level(j.get('basic_qualifications', ''), j.get('description', '')):
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
