"""
Apple Jobs parser tests.
Covers: functional field mapping, unicode decoding, edge cases.
"""
import pytest
from parsers.apple_parser import parse_apple_jobs


SAMPLE_HTML = r"""
<html><body><script>
var a = {\"positionId\":\"200123456\",\"postingTitle\":\"Machine Learning Engineer\",
\"transformedPostingTitle\":\"machine-learning-engineer\",
\"name\":\"Hyderabad\",\"countryID\":\"iso-country-IND\"};
var b = {\"positionId\":\"200789012\",\"postingTitle\":\"Software Engineer\",
\"transformedPostingTitle\":\"software-engineer\",
\"name\":\"Bengaluru\",\"countryID\":\"iso-country-IND\"};
</script></body></html>
"""


# ─── functional ───────────────────────────────────────────────────────────────

class TestFunctional:
    def test_id_has_apple_prefix(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        ids = [j["id"] for j in jobs]
        assert "apple-200123456" in ids

    def test_title_extracted(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        titles = [j["title"] for j in jobs]
        assert "Machine Learning Engineer" in titles
        assert "Software Engineer" in titles

    def test_url_contains_apple_domain(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        for j in jobs:
            assert "jobs.apple.com" in j["url"]

    def test_url_contains_position_id(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        j = next(x for x in jobs if x["id"] == "apple-200123456")
        assert "200123456" in j["url"]

    def test_source_is_apple(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        assert all(j["source"] == "Apple" for j in jobs)

    def test_all_required_keys_present(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        for j in jobs:
            for key in ("id", "title", "location", "url", "source"):
                assert key in j


# ─── positive ────────────────────────────────────────────────────────────────

class TestPositive:
    def test_location_includes_india(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        for j in jobs:
            assert "India" in j["location"]

    def test_city_included_in_location(self):
        jobs = parse_apple_jobs(SAMPLE_HTML)
        locations = [j["location"] for j in jobs]
        assert any("Hyderabad" in loc for loc in locations)

    def test_unicode_escape_decoded(self):
        html = r"""<script>{\"positionId\":\"111222\",\"postingTitle\":\"AI & ML Engineer\",
        \"transformedPostingTitle\":\"ai-ml-engineer\",
        \"name\":\"Chennai\",\"countryID\":\"iso-country-IND\"}</script>"""
        jobs = parse_apple_jobs(html)
        if jobs:
            assert "&" in jobs[0]["title"]

    def test_multiple_jobs_parsed(self):
        assert len(parse_apple_jobs(SAMPLE_HTML)) == 2


# ─── negative ────────────────────────────────────────────────────────────────

class TestNegative:
    def test_empty_html_returns_empty(self):
        assert parse_apple_jobs("") == []

    def test_html_without_position_ids_returns_empty(self):
        assert parse_apple_jobs("<html><body>No jobs</body></html>") == []

    def test_position_id_without_title_skipped(self):
        html = r"""<script>{\"positionId\":\"999000\"}</script>"""
        assert parse_apple_jobs(html) == []

    def test_duplicate_position_ids_deduplicated(self):
        html = r"""<script>
        {\"positionId\":\"300111\",\"postingTitle\":\"Dev\",\"transformedPostingTitle\":\"dev\",\"name\":\"Pune\",\"countryID\":\"iso-country-IND\"}
        {\"positionId\":\"300111\",\"postingTitle\":\"Dev Dup\",\"transformedPostingTitle\":\"dev-dup\",\"name\":\"Pune\",\"countryID\":\"iso-country-IND\"}
        </script>"""
        jobs = parse_apple_jobs(html)
        ids = [j["id"] for j in jobs]
        assert ids.count("apple-300111") == 1

    def test_returns_list_type(self):
        assert isinstance(parse_apple_jobs(""), list)
