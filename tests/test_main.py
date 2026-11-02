"""
Integration and regression tests for main.py.

Integration: apply_filters, load/save seen state, notify, email digest, fetch_all_jobs.
Regression: previously fixed bugs confirmed not to regress.
"""
import json
import sys
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import config
import main


# ─── helpers ──────────────────────────────────────────────────────────────────

def _job(id_, title="Software Engineer", location="Bangalore, India", source="Google"):
    return {"id": id_, "title": title, "location": location, "source": source,
            "url": f"https://example.com/{id_}", "posted": "2026-11-01"}


# ─── integration: apply_filters ───────────────────────────────────────────────

class TestApplyFilters:
    JOBS = [
        _job("1", title="Software Engineer",       location="Bangalore, India"),
        _job("2", title="Data Scientist",           location="Hyderabad, India"),
        _job("3", title="Product Manager",          location="Mumbai, India"),
        _job("4", title="Machine Learning Engineer",location="Pune, India"),
    ]

    def test_no_filters_passes_all(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  [])
        monkeypatch.setattr(config, "LOCATIONS", [])
        assert len(main.apply_filters(self.JOBS)) == 4

    def test_keyword_filter_case_insensitive(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  ["machine learning"])
        monkeypatch.setattr(config, "LOCATIONS", [])
        result = main.apply_filters(self.JOBS)
        assert len(result) == 1
        assert "Machine Learning" in result[0]["title"]

    def test_location_filter_case_insensitive(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  [])
        monkeypatch.setattr(config, "LOCATIONS", ["hyderabad"])
        result = main.apply_filters(self.JOBS)
        assert len(result) == 1
        assert result[0]["location"] == "Hyderabad, India"

    def test_keyword_filter_multiple_keywords_any_match(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  ["Data", "Machine Learning"])
        monkeypatch.setattr(config, "LOCATIONS", [])
        result = main.apply_filters(self.JOBS)
        assert len(result) == 2

    def test_empty_jobs_returns_empty(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  [])
        monkeypatch.setattr(config, "LOCATIONS", [])
        assert main.apply_filters([]) == []

    def test_keyword_no_match_returns_empty(self, monkeypatch):
        monkeypatch.setattr(config, "KEYWORDS",  ["Blockchain"])
        monkeypatch.setattr(config, "LOCATIONS", [])
        assert main.apply_filters(self.JOBS) == []


# ─── integration: seen state ──────────────────────────────────────────────────

class TestSeenState:
    def test_save_and_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "SEEN_FILE", tmp_path / "seen.json")
        seen = {"job-1", "job-2", "job-3"}
        main.save_seen(seen)
        loaded = main.load_seen()
        assert loaded == seen

    def test_load_missing_file_returns_empty_set(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "SEEN_FILE", tmp_path / "nonexistent.json")
        assert main.load_seen() == set()

    def test_save_creates_valid_json(self, tmp_path, monkeypatch):
        monkeypatch.setattr(main, "SEEN_FILE", tmp_path / "seen.json")
        main.save_seen({"id-a", "id-b"})
        data = json.loads((tmp_path / "seen.json").read_text())
        assert isinstance(data, list)
        assert set(data) == {"id-a", "id-b"}


# ─── integration: notify ──────────────────────────────────────────────────────

class TestNotify:
    def test_notify_skipped_when_no_topic(self, monkeypatch):
        monkeypatch.setattr(config, "NTFY_TOPIC", "")
        with patch("requests.post") as mock_post:
            main.notify(_job("1"))
            mock_post.assert_not_called()

    def test_notify_sends_post_to_ntfy(self, monkeypatch):
        monkeypatch.setattr(config, "NTFY_TOPIC", "my-topic")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            main.notify(_job("1", title="SDE I"))
            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            assert "ntfy.sh/my-topic" in url

    def test_notify_includes_job_title_in_body(self, monkeypatch):
        monkeypatch.setattr(config, "NTFY_TOPIC", "my-topic")
        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200)
            main.notify(_job("1", title="SDE at Amazon"))
            _, kwargs = mock_post.call_args
            body = kwargs.get("data", b"").decode("utf-8")
            assert "SDE at Amazon" in body

    def test_notify_network_error_handled_gracefully(self, monkeypatch):
        monkeypatch.setattr(config, "NTFY_TOPIC", "my-topic")
        with patch("requests.post", side_effect=Exception("network error")):
            main.notify(_job("1"))  # must not raise


# ─── integration: email digest ────────────────────────────────────────────────

class TestEmailDigest:
    def test_skipped_when_no_credentials(self, monkeypatch):
        monkeypatch.setattr(config, "GMAIL_ADDRESS",      "")
        monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "")
        with patch("smtplib.SMTP") as mock_smtp:
            main.notify_email_digest([_job("1")])
            mock_smtp.assert_not_called()

    def test_skipped_when_empty_job_list(self, monkeypatch):
        monkeypatch.setattr(config, "GMAIL_ADDRESS",      "user@gmail.com")
        monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "app-pass")
        with patch("smtplib.SMTP") as mock_smtp:
            main.notify_email_digest([])
            mock_smtp.assert_not_called()

    def test_smtp_error_handled_gracefully(self, monkeypatch):
        monkeypatch.setattr(config, "GMAIL_ADDRESS",      "user@gmail.com")
        monkeypatch.setattr(config, "GMAIL_APP_PASSWORD", "app-pass")
        with patch("smtplib.SMTP", side_effect=Exception("SMTP error")):
            main.notify_email_digest([_job("1")])  # must not raise


# ─── integration: fetch_all_jobs ──────────────────────────────────────────────

class TestFetchAllJobs:
    def test_returns_list(self):
        with patch.object(main, "_get", return_value="<html></html>"), \
             patch.object(main, "_post_json", return_value={}), \
             patch.object(main, "fetch_amazon_jobs", return_value=[]):
            result = main.fetch_all_jobs()
            assert isinstance(result, list)

    def test_calls_all_sources(self):
        fetched_sources = []

        original_fetch = main.fetch_all_jobs.__wrapped__ if hasattr(main.fetch_all_jobs, "__wrapped__") else None

        with patch.object(main, "_get", return_value="<html></html>") as mock_get, \
             patch.object(main, "_post_json", return_value={}) as mock_post, \
             patch.object(main, "fetch_amazon_jobs", return_value=[]):
            main.fetch_all_jobs()
            # At minimum Google, Apple, Deloitte, ServiceNow are fetched via _get
            assert mock_get.call_count >= 4


# ─── regression tests ─────────────────────────────────────────────────────────

class TestRegression:
    def test_fetch_all_jobs_function_exists(self):
        """Regression: fetch_all_jobs was accidentally deleted during an edit."""
        assert hasattr(main, "fetch_all_jobs")
        assert callable(main.fetch_all_jobs)

    def test_fetch_amazon_jobs_function_exists(self):
        """Regression: fetch_amazon_jobs must exist separately from fetch_all_jobs."""
        assert hasattr(main, "fetch_amazon_jobs")
        assert callable(main.fetch_amazon_jobs)

    def test_amazon_url_question_mark_before_ampersand(self):
        """Regression: AMAZON_URL must start with ? not &, so &offset=N appends correctly."""
        url = config.AMAZON_URL
        assert "?" in url, "AMAZON_URL must contain ?"
        q_idx   = url.index("?")
        first_amp = url.index("&") if "&" in url else len(url)
        assert q_idx < first_amp, "? must appear before first & in AMAZON_URL"

    def test_amazon_url_plus_offset_is_valid(self):
        """Regression: config.AMAZON_URL + '&offset=0' must be a valid URL with proper ? placement."""
        full = config.AMAZON_URL + "&offset=0"
        assert full.count("?") == 1
        assert full.index("?") < full.index("&")

    def test_bulk_seed_caps_notifications_at_preview_count(self, monkeypatch, tmp_path):
        """Regression: when > BULK_THRESHOLD new jobs arrive, only PREVIEW_COUNT are notified."""
        monkeypatch.setattr(main, "SEEN_FILE", tmp_path / "seen.json")
        monkeypatch.setattr(config, "NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(config, "KEYWORDS",   [])
        monkeypatch.setattr(config, "LOCATIONS",  [])

        many_jobs = [_job(str(i)) for i in range(25)]  # 25 > BULK_THRESHOLD (20)

        notify_calls = []
        with patch.object(main, "fetch_all_jobs",       return_value=many_jobs), \
             patch.object(main, "notify",                side_effect=notify_calls.append), \
             patch.object(main, "notify_email_digest"), \
             patch.object(main, "save_seen"), \
             patch.object(main, "load_seen",             return_value=set()), \
             patch("time.sleep"):
            main.main()

        assert len(notify_calls) <= main.PREVIEW_COUNT, (
            f"Expected <= {main.PREVIEW_COUNT} notifications for bulk seed, got {len(notify_calls)}"
        )

    def test_ntfy_capped_at_10_per_run(self, monkeypatch, tmp_path):
        """Regression: ntfy must send at most 10 push notifications per run (rate limit)."""
        monkeypatch.setattr(main, "SEEN_FILE", tmp_path / "seen.json")
        monkeypatch.setattr(config, "NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(config, "KEYWORDS",   [])
        monkeypatch.setattr(config, "LOCATIONS",  [])

        # 15 jobs: below BULK_THRESHOLD (20) so all 15 go to notify_jobs,
        # but ntfy_limit=10 means only first 10 call notify()
        fifteen_jobs = [_job(str(i)) for i in range(15)]

        notify_calls = []
        with patch.object(main, "fetch_all_jobs",       return_value=fifteen_jobs), \
             patch.object(main, "notify",                side_effect=notify_calls.append), \
             patch.object(main, "notify_email_digest"), \
             patch.object(main, "save_seen"), \
             patch.object(main, "load_seen",             return_value=set()), \
             patch("time.sleep"):
            main.main()

        assert len(notify_calls) <= 10, (
            f"Expected <= 10 ntfy calls per run, got {len(notify_calls)}"
        )

    def test_all_new_jobs_marked_seen_even_when_bulk(self, monkeypatch, tmp_path):
        """Regression: ALL new jobs must be marked seen, not just the notified preview."""
        seen_file = tmp_path / "seen.json"
        monkeypatch.setattr(main, "SEEN_FILE", seen_file)
        monkeypatch.setattr(config, "NTFY_TOPIC", "test-topic")
        monkeypatch.setattr(config, "KEYWORDS",   [])
        monkeypatch.setattr(config, "LOCATIONS",  [])

        many_jobs = [_job(str(i)) for i in range(25)]

        saved_seen = []
        def fake_save(seen):
            saved_seen.append(set(seen))

        with patch.object(main, "fetch_all_jobs",       return_value=many_jobs), \
             patch.object(main, "notify"), \
             patch.object(main, "notify_email_digest"), \
             patch.object(main, "save_seen",             side_effect=fake_save), \
             patch.object(main, "load_seen",             return_value=set()), \
             patch("time.sleep"):
            main.main()

        assert len(saved_seen) == 1
        assert len(saved_seen[0]) == 25, "All 25 jobs must be marked seen"
