"""Tests for _is_valid_paper_directory and _find_most_recent_output in api.py."""

import os
import time
from pathlib import Path

import pytest

from scientific_writer.api import _is_valid_paper_directory, _find_most_recent_output


@pytest.fixture
def output_folder(tmp_path):
    """Create a temporary output folder."""
    return tmp_path / "writing_outputs"


def _make_paper_dir(parent: Path, name: str, markers: list[str] | None = None) -> Path:
    """Helper to create a paper directory with optional marker subdirectories/files."""
    d = parent / name
    d.mkdir(parents=True, exist_ok=True)
    for m in (markers or []):
        if "." in m:
            (d / m).write_text("")
        else:
            (d / m).mkdir(exist_ok=True)
    return d


def _set_mtime(path: Path, mtime: float):
    """Set modification time of a directory."""
    os.utime(path, (mtime, mtime))


# --- _is_valid_paper_directory tests ---

class TestIsValidPaperDirectory:
    def test_valid_directory_with_drafts(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["drafts"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_final(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["final"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_references(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["references"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_figures(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["figures"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_progress_md(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["progress.md"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_multiple_markers(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["drafts", "final", "references"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_tex_file_only(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["paper.tex"])
        assert _is_valid_paper_directory(d) is True

    def test_valid_directory_with_pdf_file_only(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", ["paper.pdf"])
        assert _is_valid_paper_directory(d) is True

    def test_rejects_no_timestamp_prefix(self, tmp_path):
        d = _make_paper_dir(tmp_path, "random_folder", ["drafts"])
        assert _is_valid_paper_directory(d) is False

    def test_valid_directory_with_date_only_prefix(self, tmp_path):
        """YYYYMMDD_ without HHMMSS is valid — agents may use shorter timestamps."""
        d = _make_paper_dir(tmp_path, "20260226_test_paper", ["drafts"])
        assert _is_valid_paper_directory(d) is True

    def test_rejects_short_timestamp(self, tmp_path):
        """Less than 8 digits before underscore is invalid."""
        d = _make_paper_dir(tmp_path, "202602_test_paper", ["drafts"])
        assert _is_valid_paper_directory(d) is False

    def test_rejects_no_markers(self, tmp_path):
        d = _make_paper_dir(tmp_path, "20260226_120000_test_paper", [])
        assert _is_valid_paper_directory(d) is False

    def test_rejects_file_not_directory(self, tmp_path):
        f = tmp_path / "20260226_120000_test_paper"
        f.write_text("not a directory")
        assert _is_valid_paper_directory(f) is False

    def test_rejects_dotdir(self, tmp_path):
        d = _make_paper_dir(tmp_path, ".hidden_folder", ["drafts"])
        assert _is_valid_paper_directory(d) is False

    def test_rejects_letters_in_timestamp(self, tmp_path):
        d = _make_paper_dir(tmp_path, "2026022X_12000Y_test_paper", ["drafts"])
        assert _is_valid_paper_directory(d) is False


# --- _find_most_recent_output tests ---

class TestFindMostRecentOutput:
    def test_returns_none_for_empty_folder(self, output_folder):
        output_folder.mkdir(parents=True)
        result = _find_most_recent_output(output_folder, time.time())
        assert result is None

    def test_returns_none_for_nonexistent_folder(self, tmp_path):
        result = _find_most_recent_output(tmp_path / "nonexistent", time.time())
        assert result is None

    def test_returns_none_when_no_valid_dirs(self, output_folder):
        output_folder.mkdir(parents=True)
        _make_paper_dir(output_folder, "random_folder", ["drafts"])
        _make_paper_dir(output_folder, "another_folder", ["final"])
        result = _find_most_recent_output(output_folder, time.time())
        assert result is None

    def test_finds_valid_recent_directory(self, output_folder):
        output_folder.mkdir(parents=True)
        start_time = time.time() - 30  # 30 seconds ago
        d = _make_paper_dir(output_folder, "20260226_120000_my_paper", ["drafts", "references"])
        # st_mtime is ~now, which is after start_time
        result = _find_most_recent_output(output_folder, start_time)
        assert result == d

    def test_ignores_invalid_dirs_among_valid(self, output_folder):
        output_folder.mkdir(parents=True)
        start_time = time.time() - 30

        _make_paper_dir(output_folder, "not_a_paper_dir", ["drafts"])
        valid = _make_paper_dir(output_folder, "20260226_120000_real_paper", ["drafts"])

        result = _find_most_recent_output(output_folder, start_time)
        assert result == valid

    def test_returns_most_recently_modified(self, output_folder):
        output_folder.mkdir(parents=True)
        start_time = time.time() - 120

        older = _make_paper_dir(output_folder, "20260226_100000_older_paper", ["drafts"])
        _set_mtime(older, time.time() - 60)  # 60s ago

        newer = _make_paper_dir(output_folder, "20260226_100500_newer_paper", ["drafts"])
        # newer has st_mtime ~now (most recent)

        result = _find_most_recent_output(output_folder, start_time)
        assert result == newer

    def test_no_fallback_to_old_directories(self, output_folder):
        """The dangerous fallback is removed — old dirs should NOT be returned."""
        output_folder.mkdir(parents=True)
        old_dir = _make_paper_dir(output_folder, "20200101_000000_old_paper", ["drafts"])
        # Set mtime to long ago
        _set_mtime(old_dir, time.time() - 86400)  # 1 day ago

        # start_time is now, so the old dir is way outside the 60s buffer
        result = _find_most_recent_output(output_folder, time.time())
        assert result is None

    def test_60_second_buffer(self, output_folder):
        """Directories modified within 60s before start_time should still be found."""
        output_folder.mkdir(parents=True)
        now = time.time()
        d = _make_paper_dir(output_folder, "20260226_120000_buffered_paper", ["drafts"])
        # Set mtime to 30s before start_time (within 60s buffer)
        _set_mtime(d, now - 30)

        # start_time is now — dir was modified 30s ago, within 60s buffer
        result = _find_most_recent_output(output_folder, now)
        assert result == d

    def test_directory_just_outside_buffer(self, output_folder):
        """Directories modified more than 60s before start_time should NOT be found."""
        output_folder.mkdir(parents=True)
        now = time.time()
        d = _make_paper_dir(output_folder, "20260226_120000_too_old_paper", ["drafts"])
        # Set mtime to 120s before start_time (outside 60s buffer)
        _set_mtime(d, now - 120)

        result = _find_most_recent_output(output_folder, now)
        assert result is None
