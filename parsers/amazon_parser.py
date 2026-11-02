def parse_amazon_jobs(data):
    """Parse Amazon Jobs JSON API response."""
    jobs = []
    for j in data.get('jobs', []):
        jid = str(j.get('id_icims', ''))
        if not jid:
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
