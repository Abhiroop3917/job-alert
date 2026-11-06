import datetime


def parse_nvidia_jobs(data):
    """Parse NVIDIA Careers API response (Eightfold /api/pcsx/search endpoint)."""
    positions = (data or {}).get('data', {}).get('positions', [])
    jobs = []
    for p in positions:
        pid = str(p.get('id', ''))
        if not pid:
            continue
        posted_ts = p.get('postedTs', 0)
        posted = (
            datetime.datetime.fromtimestamp(posted_ts).strftime('%Y-%m-%d')
            if posted_ts else ''
        )
        jobs.append({
            'id':       f'nvidia-{pid}',
            'title':    (p.get('name') or '').strip(),
            'location': ', '.join(p.get('locations') or []),
            'url':      f"https://jobs.nvidia.com{p.get('positionUrl', '')}",
            'posted':   posted,
            'source':   'NVIDIA',
        })
    return jobs


def parse_nvidia_job_detail(data):
    """Extract jobDescription HTML from a NVIDIA position_details API response."""
    return (data or {}).get('data', {}).get('jobDescription', '')
