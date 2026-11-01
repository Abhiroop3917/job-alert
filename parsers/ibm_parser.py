import re


def parse_ibm_jobs(data):
    hits = (data or {}).get('hits', {}).get('hits', [])
    jobs = []

    for hit in hits:
        src    = hit.get('_source', {})
        raw_id = hit.get('_id', '')
        if not raw_id or not src.get('title'):
            continue

        location = src.get('field_keyword_19') or 'India'
        location = re.sub(r',\s*IN\s*$', ', India', location, flags=re.IGNORECASE)
        location = re.sub(r'^Multiple Cities$', 'India (Multiple Cities)', location, flags=re.IGNORECASE)

        jobs.append({
            'id':       f'ibm-{raw_id[:20]}',
            'title':    src['title'].strip(),
            'location': location,
            'url':      src.get('url') or f'https://careers.ibm.com/careers/JobDetail?jobId={raw_id}',
            'source':   'IBM',
        })

    return jobs
