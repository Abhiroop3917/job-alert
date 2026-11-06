"""
Microsoft parser tests.
Covers: functional field mapping, positive filtering, edge cases.
"""
import pytest
from parsers.microsoft_parser import parse_microsoft_jobs


# ─── helpers ──────────────────────────────────────────────────────────────────

def _position(pid, name="Software Engineer", locations=None,
              posted_ts=1793600000, position_url="/careers/job/123"):
    return {
        "id": pid,
        "name": name,
        "locations": locations or ["India, Karnataka, Bangalore"],
        "postedTs": posted_ts,
        "positionUrl": position_url,
    }

def _wrap(*positions):
    return {"data": {"positions": list(positions)}}


# ─── functional: field mapping ────────────────────────────────────────────────

class TestFieldMapping:
    def test_id_has_microsoft_prefix(self):
        j = parse_microsoft_jobs(_wrap(_position(999)))[0]
        assert j["id"] == "microsoft-999"

    def test_title_extracted(self):
        j = parse_microsoft_jobs(_wrap(_position(1, name="SDE I")))[0]
        assert j["title"] == "SDE I"

    def test_title_stripped(self):
        j = parse_microsoft_jobs(_wrap(_position(1, name="  SDE I  ")))[0]
        assert j["title"] == "SDE I"

    def test_location_joins_list(self):
        j = parse_microsoft_jobs(_wrap(_position(1, locations=["India, KA, Bangalore", "India, TS, Hyderabad"])))[0]
        assert j["location"] == "India, KA, Bangalore, India, TS, Hyderabad"

    def test_single_location(self):
        j = parse_microsoft_jobs(_wrap(_position(1, locations=["India, KA, Bangalore"])))[0]
        assert j["location"] == "India, KA, Bangalore"

    def test_url_built_from_position_url(self):
        j = parse_microsoft_jobs(_wrap(_position(1, position_url="/careers/job/99")))[0]
        assert j["url"] == "https://apply.careers.microsoft.com/careers/job/99"

    def test_posted_date_converted_from_timestamp(self):
        # postedTs=1793596349 → 2026-11-02
        j = parse_microsoft_jobs(_wrap(_position(1, posted_ts=1793596349)))[0]
        assert j["posted"] == "2026-11-02"

    def test_source_is_microsoft(self):
        j = parse_microsoft_jobs(_wrap(_position(1)))[0]
        assert j["source"] == "Microsoft"


# ─── positive: valid job included ─────────────────────────────────────────────

class TestPositiveFilter:
    def test_normal_job_included(self):
        assert len(parse_microsoft_jobs(_wrap(_position(1)))) == 1

    def test_multiple_jobs_all_included(self):
        data = _wrap(_position(1), _position(2), _position(3))
        assert len(parse_microsoft_jobs(data)) == 3

    def test_empty_positions_list_ok(self):
        assert parse_microsoft_jobs({"data": {"positions": []}}) == []

    def test_returns_list_type(self):
        assert isinstance(parse_microsoft_jobs({}), list)


# ─── negative / edge cases ────────────────────────────────────────────────────

class TestEdgeCases:
    def test_missing_id_skipped(self):
        p = {"name": "SDE", "locations": ["India"], "postedTs": 0, "positionUrl": "/x"}
        assert parse_microsoft_jobs({"data": {"positions": [p]}}) == []

    def test_missing_data_key_returns_empty(self):
        assert parse_microsoft_jobs({}) == []

    def test_missing_positions_key_returns_empty(self):
        assert parse_microsoft_jobs({"data": {}}) == []

    def test_none_name_becomes_empty_string(self):
        p = _position(1)
        p["name"] = None
        j = parse_microsoft_jobs({"data": {"positions": [p]}})[0]
        assert j["title"] == ""

    def test_missing_locations_becomes_empty_string(self):
        p = _position(1)
        del p["locations"]
        j = parse_microsoft_jobs({"data": {"positions": [p]}})[0]
        assert j["location"] == ""

    def test_zero_posted_ts_becomes_empty_string(self):
        j = parse_microsoft_jobs(_wrap(_position(1, posted_ts=0)))[0]
        assert j["posted"] == ""

    def test_missing_position_url_gives_base_url(self):
        p = _position(1)
        del p["positionUrl"]
        j = parse_microsoft_jobs({"data": {"positions": [p]}})[0]
        assert j["url"] == "https://apply.careers.microsoft.com"


# ─── integration: real-shaped response ────────────────────────────────────────

class TestIntegration:
    def test_real_response_shape(self):
        """Matches the shape returned by the live API."""
        data = {
            "status": 200,
            "error": {"message": "", "body": ""},
            "metadata": None,
            "data": {
                "positions": [
                    {
                        "id": 1970393556997609,
                        "displayJobId": "200055581",
                        "name": "Software Engineer II - AI/ML Infrastructure CoreAI",
                        "locations": ["India, Karnataka, Bangalore"],
                        "standardizedLocations": ["Bengaluru, KA, IN"],
                        "postedTs": 1793772219,
                        "solrScore": None,
                        "stars": 0,
                        "department": "Software Engineering",
                        "creationTs": 1789362759,
                        "isHot": 0,
                        "workLocationOption": "onsite",
                        "locationFlexibility": None,
                        "atsJobId": "200055581",
                        "positionUrl": "/careers/job/1970393556997609",
                    }
                ],
                "count": 1,
            },
        }
        jobs = parse_microsoft_jobs(data)
        assert len(jobs) == 1
        j = jobs[0]
        assert j["id"] == "microsoft-1970393556997609"
        assert j["title"] == "Software Engineer II - AI/ML Infrastructure CoreAI"
        assert j["location"] == "India, Karnataka, Bangalore"
        assert j["url"] == "https://apply.careers.microsoft.com/careers/job/1970393556997609"
        assert j["posted"] == "2026-11-04"
        assert j["source"] == "Microsoft"
