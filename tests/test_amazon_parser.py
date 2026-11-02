"""
Amazon parser tests.
Covers: functional field mapping, positive/negative year filtering, edge cases.
"""
import pytest
from parsers.amazon_parser import parse_amazon_jobs


# ─── helpers ──────────────────────────────────────────────────────────────────

def _job(id_icims, title="Software Engineer", bq="", location="Bangalore, India",
         path="/en/jobs/123/sde", posted="2026-10-01"):
    return {
        "id_icims": id_icims,
        "title": title,
        "basic_qualifications": bq,
        "location": location,
        "job_path": path,
        "posted_date": posted,
    }

def _wrap(*jobs):
    return {"jobs": list(jobs)}


# ─── functional: field mapping ────────────────────────────────────────────────

class TestFieldMapping:
    def test_id_has_amazon_prefix(self):
        j = parse_amazon_jobs(_wrap(_job("12345")))[0]
        assert j["id"] == "amazon-12345"

    def test_title_extracted(self):
        j = parse_amazon_jobs(_wrap(_job("1", title="SDE I")))[0]
        assert j["title"] == "SDE I"

    def test_title_stripped(self):
        j = parse_amazon_jobs(_wrap(_job("1", title="  SDE I  ")))[0]
        assert j["title"] == "SDE I"

    def test_location_extracted(self):
        j = parse_amazon_jobs(_wrap(_job("1", location="Chennai, India")))[0]
        assert j["location"] == "Chennai, India"

    def test_url_built_from_job_path(self):
        j = parse_amazon_jobs(_wrap(_job("1", path="/en/jobs/999/role")))[0]
        assert j["url"] == "https://amazon.jobs/en/jobs/999/role"

    def test_posted_date_preserved(self):
        j = parse_amazon_jobs(_wrap(_job("1", posted="2026-11-01")))[0]
        assert j["posted"] == "2026-11-01"

    def test_source_is_amazon(self):
        j = parse_amazon_jobs(_wrap(_job("1")))[0]
        assert j["source"] == "Amazon"


# ─── positive: year-based filtering ──────────────────────────────────────────

class TestPositiveFilter:
    def test_no_year_in_bq_included(self):
        jobs = parse_amazon_jobs(_wrap(_job("1", bq="Experience building ML models for business.")))
        assert len(jobs) == 1

    def test_empty_bq_included(self):
        jobs = parse_amazon_jobs(_wrap(_job("1", bq="")))
        assert len(jobs) == 1

    def test_none_bq_included(self):
        j = _job("1")
        j["basic_qualifications"] = None
        assert len(parse_amazon_jobs({"jobs": [j]})) == 1

    def test_1_year_requirement_included(self):
        bq = "1+ years of non-internship professional software development experience"
        assert len(parse_amazon_jobs(_wrap(_job("1", bq=bq)))) == 1

    def test_2_year_requirement_included(self):
        bq = "2+ years of non-internship professional software development experience"
        assert len(parse_amazon_jobs(_wrap(_job("1", bq=bq)))) == 1

    def test_html_tags_stripped_before_year_check(self):
        bq = "<ul><li>1+ years of non-internship professional software development experience</li></ul>"
        assert len(parse_amazon_jobs(_wrap(_job("1", bq=bq)))) == 1


# ─── negative: year-based filtering ──────────────────────────────────────────

class TestNegativeFilter:
    def test_3_year_excluded(self):
        bq = "3+ years of non-internship professional software development experience"
        assert parse_amazon_jobs(_wrap(_job("1", bq=bq))) == []

    def test_5_year_senior_excluded(self):
        bq = "5+ years of non-internship professional software development experience"
        assert parse_amazon_jobs(_wrap(_job("1", bq=bq))) == []

    def test_7_year_manager_excluded(self):
        bq = "7+ years of engineering experience - 3+ years of engineering team management"
        assert parse_amazon_jobs(_wrap(_job("1", bq=bq))) == []

    def test_10_year_director_excluded(self):
        bq = "10+ years of engineering experience"
        assert parse_amazon_jobs(_wrap(_job("1", bq=bq))) == []

    def test_max_year_determines_exclusion(self):
        # BQ has 2+ AND 3+ → max=3 → excluded
        bq = "2+ years of architecture experience - 3+ years of software development experience"
        assert parse_amazon_jobs(_wrap(_job("1", bq=bq))) == []

    def test_missing_id_icims_skipped(self):
        j = {"title": "SDE", "basic_qualifications": "", "location": "India", "job_path": "/x", "posted_date": ""}
        assert parse_amazon_jobs({"jobs": [j]}) == []

    def test_empty_id_icims_skipped(self):
        assert parse_amazon_jobs(_wrap(_job(""))) == []

    def test_empty_jobs_list(self):
        assert parse_amazon_jobs({"jobs": []}) == []

    def test_missing_jobs_key(self):
        assert parse_amazon_jobs({}) == []


# ─── mixed inputs ─────────────────────────────────────────────────────────────

class TestMixedInputs:
    def test_only_entry_level_jobs_pass(self):
        data = _wrap(
            _job("1", bq="1+ years of experience"),     # entry → pass
            _job("2", bq="5+ years of experience"),     # senior → block
            _job("3", bq="Experience with Python"),     # no year → pass
            _job("4", bq="7+ years of management"),     # manager → block
            _job("5", bq="2+ years of architecture"),   # junior → pass
        )
        result = parse_amazon_jobs(data)
        ids = [j["id"] for j in result]
        assert set(ids) == {"amazon-1", "amazon-3", "amazon-5"}

    def test_returns_list_type(self):
        assert isinstance(parse_amazon_jobs({}), list)
