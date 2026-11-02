"""
Google Careers parser tests.
Covers: functional field mapping, positive/negative cases, edge cases.
"""
import pytest
from parsers.google_parser import parse_google_jobs


SAMPLE_HTML = """
<html><body>
<div>
  <h3 class="QJPWVe">Software Engineer, Tools</h3>
  <p>Hyderabad, Telangana, India</p>
  <p>2 days ago</p>
  <a href="/about/careers/applications/jobs/results/1234567890123">Apply</a>
</div>
<div>
  <h3 class="QJPWVe">Machine Learning Engineer</h3>
  <p>Bangalore, Karnataka, India</p>
  <p>1 day ago</p>
  <a href="/about/careers/applications/jobs/results/9876543210987">Apply</a>
</div>
</body></html>
"""


# ─── functional ───────────────────────────────────────────────────────────────

class TestFunctional:
    def test_parses_multiple_job_ids(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        ids = [j["id"] for j in jobs]
        assert "1234567890123" in ids
        assert "9876543210987" in ids

    def test_source_is_google(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        assert all(j["source"] == "Google" for j in jobs)

    def test_url_format(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        for j in jobs:
            assert j["url"].startswith(
                "https://www.google.com/about/careers/applications/jobs/results/"
            )
            assert j["id"] in j["url"]

    def test_all_required_keys_present(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        for j in jobs:
            for key in ("id", "title", "location", "url", "source"):
                assert key in j, f"Missing key: {key}"


# ─── positive ────────────────────────────────────────────────────────────────

class TestPositive:
    def test_title_extracted_from_h3(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        titles = [j["title"] for j in jobs]
        assert any("Software Engineer" in t for t in titles)
        assert any("Machine Learning Engineer" in t for t in titles)

    def test_html_entity_decoded_in_title(self):
        html = """
        <h3>Software &amp; Data Engineer</h3>
        <a href="/about/careers/applications/jobs/results/1111111111111">x</a>
        """
        jobs = parse_google_jobs(html)
        assert any("&" in j["title"] for j in jobs)

    def test_duplicate_job_id_deduplicated(self):
        html = SAMPLE_HTML + """
        <a href="/about/careers/applications/jobs/results/1234567890123">Duplicate</a>
        """
        jobs = parse_google_jobs(html)
        ids = [j["id"] for j in jobs]
        assert ids.count("1234567890123") == 1

    def test_returns_correct_count(self):
        jobs = parse_google_jobs(SAMPLE_HTML)
        assert len(jobs) == 2


# ─── negative ────────────────────────────────────────────────────────────────

class TestNegative:
    def test_empty_html_returns_empty(self):
        assert parse_google_jobs("") == []

    def test_html_without_job_ids_returns_empty(self):
        assert parse_google_jobs("<html><h3>Title</h3><p>Some text</p></html>") == []

    def test_job_id_without_preceding_h3_skipped(self):
        # No <h3> before the job link
        html = '<a href="/about/careers/applications/jobs/results/9999999999999">Apply</a>'
        assert parse_google_jobs(html) == []

    def test_returns_list_type(self):
        assert isinstance(parse_google_jobs(""), list)
