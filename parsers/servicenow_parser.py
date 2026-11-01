import re

JOB_BLOCK_RE = re.compile(r'<job>([\s\S]*?)</job>')
TITLE_RE     = re.compile(r'<title><!\[CDATA\[([\s\S]*?)\]\]></title>',      re.IGNORECASE)
ID_RE        = re.compile(r'<apijobid><!\[CDATA\[([\s\S]*?)\]\]></apijobid>', re.IGNORECASE)
URL_RE       = re.compile(r'<url><!\[CDATA\[([\s\S]*?)\]\]></url>',          re.IGNORECASE)
CITY_RE      = re.compile(r'<city><!\[CDATA\[([\s\S]*?)\]\]></city>',        re.IGNORECASE)
COUNTRY_RE   = re.compile(r'<country><!\[CDATA\[([\s\S]*?)\]\]></country>',  re.IGNORECASE)


def parse_servicenow_jobs(xml):
    jobs = []
    seen = set()

    for m in JOB_BLOCK_RE.finditer(xml):
        block = m.group(1)

        country_m = COUNTRY_RE.search(block)
        if not country_m or country_m.group(1).strip() != 'India':
            continue

        id_m = ID_RE.search(block)
        if not id_m:
            continue
        job_id = id_m.group(1).strip()
        if job_id in seen:
            continue
        seen.add(job_id)

        title_m = TITLE_RE.search(block)
        if not title_m:
            continue

        url_m  = URL_RE.search(block)
        city_m = CITY_RE.search(block)
        city   = city_m.group(1).strip() if city_m else ''

        jobs.append({
            'id':       f'sn-{job_id}',
            'title':    title_m.group(1).strip(),
            'location': f'{city}, India' if city else 'India',
            'url':      url_m.group(1).strip() if url_m else f'https://careers.servicenow.com/jobs/{job_id}/',
            'source':   'ServiceNow',
        })

    return jobs
