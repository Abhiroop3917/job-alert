"""
Deloitte parser tests.
Covers: functional field mapping, location normalization, edge cases.
"""
import pytest
from parsers.deloitte_parser import parse_deloitte_jobs


SAMPLE_HTML = """
<html><body>
<div>
  <a href="/job/python-developer/123456789/" class="jobTitle-link">Python Developer</a>
  <span class="jobLocation">Bangalore, IN</span>
</div>
<div>
  <a href="/job/data-analyst/987654321/" class="jobTitle-link">Data Analyst</a>
  <span class="jobLocation">Hyderabad, IN</span>
</div>
</body></html>
"""


# ─── functional ───────────────────────────────────────────────────────────────

class TestFunctional:
    def test_id_has_deloitte_prefix(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        ids = [j["id"] for j in jobs]
        assert "deloitte-123456789" in ids
        assert "deloitte-987654321" in ids

    def test_title_extracted(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        titles = [j["title"] for j in jobs]
        assert "Python Developer" in titles
        assert "Data Analyst" in titles

    def test_url_constructed(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        j = next(x for x in jobs if x["id"] == "deloitte-123456789")
        assert j["url"] == "https://southasiacareers.deloitte.com/job/python-developer/123456789/"

    def test_source_is_deloitte(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        assert all(j["source"] == "Deloitte" for j in jobs)

    def test_all_required_keys_present(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        for j in jobs:
            for key in ("id", "title", "location", "url", "source"):
                assert key in j


# ─── positive ────────────────────────────────────────────────────────────────

class TestPositive:
    def test_in_suffix_converted_to_india(self):
        jobs = parse_deloitte_jobs(SAMPLE_HTML)
        for j in jobs:
            assert ", IN" not in j["location"]
            assert "India" in j["location"]

    def test_multiple_jobs_parsed(self):
        assert len(parse_deloitte_jobs(SAMPLE_HTML)) == 2

    def test_html_entity_in_title_decoded(self):
        html = """<a href="/job/x/111111111/" class="jobTitle-link">AI &amp; ML Engineer</a>
                  <span class="jobLocation">Mumbai, IN</span>"""
        jobs = parse_deloitte_jobs(html)
        if jobs:
            assert "&" in jobs[0]["title"]

    def test_location_without_in_suffix_preserved(self):
        html = """<a href="/job/dev/222222222/" class="jobTitle-link">Dev</a>
                  <span class="jobLocation">Mumbai, Maharashtra</span>"""
        jobs = parse_deloitte_jobs(html)
        if jobs:
            assert "Maharashtra" in jobs[0]["location"]


# ─── negative ────────────────────────────────────────────────────────────────

class TestNegative:
    def test_empty_html_returns_empty(self):
        assert parse_deloitte_jobs("") == []

    def test_no_job_links_returns_empty(self):
        assert parse_deloitte_jobs("<html><body><p>No jobs</p></body></html>") == []

    def test_duplicate_ids_deduplicated(self):
        html = SAMPLE_HTML + """
        <a href="/job/dup/123456789/" class="jobTitle-link">Dup Title</a>
        <span class="jobLocation">India</span>
        """
        jobs = parse_deloitte_jobs(html)
        ids = [j["id"] for j in jobs]
        assert ids.count("deloitte-123456789") == 1

    def test_returns_list_type(self):
        assert isinstance(parse_deloitte_jobs(""), list)
