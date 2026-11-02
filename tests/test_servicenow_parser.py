"""
ServiceNow parser tests.
Covers: functional field mapping, India filtering, edge cases.
"""
import pytest
from parsers.servicenow_parser import parse_servicenow_jobs


INDIA_XML = """<?xml version="1.0"?>
<jobs>
  <job>
    <title><![CDATA[Software Engineer I]]></title>
    <apijobid><![CDATA[SN-IND-001]]></apijobid>
    <url><![CDATA[https://careers.servicenow.com/jobs/SN-IND-001/]]></url>
    <city><![CDATA[Hyderabad]]></city>
    <country><![CDATA[India]]></country>
  </job>
</jobs>"""

US_XML = """<?xml version="1.0"?>
<jobs>
  <job>
    <title><![CDATA[Software Engineer]]></title>
    <apijobid><![CDATA[SN-US-001]]></apijobid>
    <url><![CDATA[https://careers.servicenow.com/jobs/SN-US-001/]]></url>
    <city><![CDATA[San Jose]]></city>
    <country><![CDATA[United States]]></country>
  </job>
</jobs>"""

MULTI_XML = """<?xml version="1.0"?>
<jobs>
  <job>
    <title><![CDATA[Backend Developer]]></title>
    <apijobid><![CDATA[SN-002]]></apijobid>
    <url><![CDATA[https://careers.servicenow.com/jobs/SN-002/]]></url>
    <city><![CDATA[Bangalore]]></city>
    <country><![CDATA[India]]></country>
  </job>
  <job>
    <title><![CDATA[Frontend Developer]]></title>
    <apijobid><![CDATA[SN-003]]></apijobid>
    <url><![CDATA[https://careers.servicenow.com/jobs/SN-003/]]></url>
    <city><![CDATA[New York]]></city>
    <country><![CDATA[United States]]></country>
  </job>
  <job>
    <title><![CDATA[Data Scientist]]></title>
    <apijobid><![CDATA[SN-004]]></apijobid>
    <url><![CDATA[https://careers.servicenow.com/jobs/SN-004/]]></url>
    <city><![CDATA[Pune]]></city>
    <country><![CDATA[India]]></country>
  </job>
</jobs>"""


# ─── functional ───────────────────────────────────────────────────────────────

class TestFunctional:
    def test_id_has_sn_prefix(self):
        jobs = parse_servicenow_jobs(INDIA_XML)
        assert jobs[0]["id"] == "sn-SN-IND-001"

    def test_title_extracted(self):
        jobs = parse_servicenow_jobs(INDIA_XML)
        assert jobs[0]["title"] == "Software Engineer I"

    def test_location_city_india(self):
        jobs = parse_servicenow_jobs(INDIA_XML)
        assert jobs[0]["location"] == "Hyderabad, India"

    def test_url_extracted(self):
        jobs = parse_servicenow_jobs(INDIA_XML)
        assert jobs[0]["url"] == "https://careers.servicenow.com/jobs/SN-IND-001/"

    def test_source_is_servicenow(self):
        jobs = parse_servicenow_jobs(INDIA_XML)
        assert jobs[0]["source"] == "ServiceNow"


# ─── positive ────────────────────────────────────────────────────────────────

class TestPositive:
    def test_india_job_included(self):
        assert len(parse_servicenow_jobs(INDIA_XML)) == 1

    def test_only_india_jobs_from_mixed_feed(self):
        jobs = parse_servicenow_jobs(MULTI_XML)
        assert len(jobs) == 2
        for j in jobs:
            assert "India" in j["location"]

    def test_location_defaults_to_india_when_no_city(self):
        xml = """<jobs><job>
          <title><![CDATA[Dev]]></title>
          <apijobid><![CDATA[SN-NO-CITY]]></apijobid>
          <url><![CDATA[https://x.com/]]></url>
          <country><![CDATA[India]]></country>
        </job></jobs>"""
        jobs = parse_servicenow_jobs(xml)
        assert jobs[0]["location"] == "India"

    def test_url_fallback_when_missing(self):
        xml = """<jobs><job>
          <title><![CDATA[Dev]]></title>
          <apijobid><![CDATA[FALLBACK-1]]></apijobid>
          <country><![CDATA[India]]></country>
        </job></jobs>"""
        jobs = parse_servicenow_jobs(xml)
        assert jobs[0]["url"] == "https://careers.servicenow.com/jobs/FALLBACK-1/"


# ─── negative ────────────────────────────────────────────────────────────────

class TestNegative:
    def test_non_india_job_filtered_out(self):
        assert parse_servicenow_jobs(US_XML) == []

    def test_empty_xml_returns_empty(self):
        assert parse_servicenow_jobs("<jobs></jobs>") == []

    def test_no_jobs_tag_returns_empty(self):
        assert parse_servicenow_jobs("") == []

    def test_job_missing_title_skipped(self):
        xml = """<jobs><job>
          <apijobid><![CDATA[SN-NO-TITLE]]></apijobid>
          <url><![CDATA[https://x.com/]]></url>
          <country><![CDATA[India]]></country>
        </job></jobs>"""
        assert parse_servicenow_jobs(xml) == []

    def test_job_missing_id_skipped(self):
        xml = """<jobs><job>
          <title><![CDATA[Dev]]></title>
          <url><![CDATA[https://x.com/]]></url>
          <country><![CDATA[India]]></country>
        </job></jobs>"""
        assert parse_servicenow_jobs(xml) == []

    def test_duplicate_ids_deduplicated(self):
        xml = """<jobs>
          <job><title><![CDATA[Dev]]></title><apijobid><![CDATA[DUP]]></apijobid>
               <url><![CDATA[https://x]]></url><country><![CDATA[India]]></country></job>
          <job><title><![CDATA[Dev2]]></title><apijobid><![CDATA[DUP]]></apijobid>
               <url><![CDATA[https://x]]></url><country><![CDATA[India]]></country></job>
        </jobs>"""
        assert len(parse_servicenow_jobs(xml)) == 1

    def test_returns_list_type(self):
        assert isinstance(parse_servicenow_jobs(""), list)
