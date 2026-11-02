"""
IBM parser tests.
Covers: functional field mapping, location normalization, edge cases.
"""
import pytest
from parsers.ibm_parser import parse_ibm_jobs


def _hit(id_, title="Software Engineer", location="Bangalore, IN",
         url="https://careers.ibm.com/job/123"):
    return {
        "_id": id_,
        "_source": {
            "title": title,
            "field_keyword_19": location,
            "url": url,
        }
    }

def _data(*hits):
    return {"hits": {"hits": list(hits)}}


# ─── functional ───────────────────────────────────────────────────────────────

class TestFunctional:
    def test_id_has_ibm_prefix(self):
        jobs = parse_ibm_jobs(_data(_hit("job-id-001")))
        assert jobs[0]["id"].startswith("ibm-")

    def test_title_extracted(self):
        jobs = parse_ibm_jobs(_data(_hit("1", title="Data Scientist")))
        assert jobs[0]["title"] == "Data Scientist"

    def test_title_stripped(self):
        jobs = parse_ibm_jobs(_data(_hit("1", title="  ML Engineer  ")))
        assert jobs[0]["title"] == "ML Engineer"

    def test_url_from_source(self):
        jobs = parse_ibm_jobs(_data(_hit("1", url="https://careers.ibm.com/job/xyz")))
        assert jobs[0]["url"] == "https://careers.ibm.com/job/xyz"

    def test_source_is_ibm(self):
        jobs = parse_ibm_jobs(_data(_hit("1")))
        assert jobs[0]["source"] == "IBM"

    def test_all_required_keys_present(self):
        jobs = parse_ibm_jobs(_data(_hit("1")))
        for key in ("id", "title", "location", "url", "source"):
            assert key in jobs[0]


# ─── positive ────────────────────────────────────────────────────────────────

class TestPositive:
    def test_location_in_converted_to_india(self):
        jobs = parse_ibm_jobs(_data(_hit("1", location="Bangalore, IN")))
        assert jobs[0]["location"] == "Bangalore, India"

    def test_location_in_case_insensitive(self):
        jobs = parse_ibm_jobs(_data(_hit("1", location="Chennai, in")))
        assert jobs[0]["location"] == "Chennai, India"

    def test_multiple_cities_normalized(self):
        jobs = parse_ibm_jobs(_data(_hit("1", location="Multiple Cities")))
        assert jobs[0]["location"] == "India (Multiple Cities)"

    def test_url_fallback_when_missing(self):
        hit = {"_id": "FALLBACK-ID", "_source": {"title": "Dev", "field_keyword_19": "India"}}
        jobs = parse_ibm_jobs({"hits": {"hits": [hit]}})
        assert "ibm.com" in jobs[0]["url"] or "careers" in jobs[0]["url"]

    def test_id_truncated_to_20_chars(self):
        long_id = "a" * 40
        jobs = parse_ibm_jobs(_data(_hit(long_id)))
        assert len(jobs[0]["id"]) <= len("ibm-") + 20


# ─── negative ────────────────────────────────────────────────────────────────

class TestNegative:
    def test_none_data_returns_empty(self):
        assert parse_ibm_jobs(None) == []

    def test_empty_data_returns_empty(self):
        assert parse_ibm_jobs({}) == []

    def test_empty_hits_returns_empty(self):
        assert parse_ibm_jobs(_data()) == []

    def test_missing_title_skipped(self):
        hit = {"_id": "no-title", "_source": {"field_keyword_19": "India", "url": "https://x"}}
        assert parse_ibm_jobs({"hits": {"hits": [hit]}}) == []

    def test_missing_id_skipped(self):
        hit = {"_id": "", "_source": {"title": "Dev", "field_keyword_19": "India"}}
        assert parse_ibm_jobs({"hits": {"hits": [hit]}}) == []

    def test_returns_list_type(self):
        assert isinstance(parse_ibm_jobs(None), list)
