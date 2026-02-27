"""Tests for setup_claude_skills workspace creation in core.py."""

import tempfile
from pathlib import Path

import pytest

from scientific_writer.core import setup_claude_skills


@pytest.fixture
def package_dir(tmp_path):
    """Create a mock package directory with .claude/ structure."""
    pkg = tmp_path / "scientific_writer"
    pkg.mkdir()
    claude = pkg / ".claude"
    claude.mkdir()

    # WRITER.md
    (claude / "WRITER.md").write_text("# Test WRITER instructions")

    # Skill scripts that should be flattened
    skills = claude / "skills"
    skills.mkdir()

    pw = skills / "parallel-web" / "scripts"
    pw.mkdir(parents=True)
    (pw / "parallel_web.py").write_text("# parallel_web")

    slides = skills / "scientific-slides" / "scripts"
    slides.mkdir(parents=True)
    (slides / "pdf_to_images.py").write_text("# pdf_to_images")

    schematics = skills / "scientific-schematics" / "scripts"
    schematics.mkdir(parents=True)
    (schematics / "generate_schematic.py").write_text("# generate_schematic")

    gen_img = skills / "generate-image" / "scripts"
    gen_img.mkdir(parents=True)
    (gen_img / "generate_image.py").write_text("# generate_image")

    rl = skills / "research-lookup" / "scripts"
    rl.mkdir(parents=True)
    (rl / "research_lookup.py").write_text("# research_lookup")

    # SKILL.md files (should NOT be copied)
    for skill_dir in skills.iterdir():
        if skill_dir.is_dir():
            (skill_dir / "SKILL.md").write_text("# Skill definition")

    return pkg


@pytest.fixture
def work_dir(tmp_path):
    """Create a mock working directory."""
    wd = tmp_path / "user_project"
    wd.mkdir()
    return wd


class TestSetupClaudeSkills:
    def test_workspace_in_tmp_dir(self, package_dir, work_dir):
        """Workspace must be in system temp dir, NOT under work_dir."""
        workspace = setup_claude_skills(package_dir, work_dir)
        assert str(workspace).startswith(tempfile.gettempdir())
        assert not str(workspace).startswith(str(work_dir))

    def test_creates_workspace_directory(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        assert workspace.is_dir()

    def test_copies_writer_md_to_root(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        writer = workspace / "WRITER.md"
        assert writer.exists()
        assert writer.read_text() == "# Test WRITER instructions"

    def test_no_claude_skills_directory(self, package_dir, work_dir):
        """Critical: workspace must NOT contain .claude/skills/."""
        workspace = setup_claude_skills(package_dir, work_dir)
        assert not (workspace / ".claude" / "skills").exists()
        # Also no .claude/ directory at all
        assert not (workspace / ".claude").exists()

    def test_flattens_parallel_web_script(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        assert (workspace / "scripts" / "parallel_web.py").exists()

    def test_flattens_pdf_to_images_script(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        assert (workspace / "scripts" / "pdf_to_images.py").exists()

    def test_flattens_generate_schematic_script(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        assert (workspace / "scripts" / "generate_schematic.py").exists()

    def test_flattens_generate_image_script(self, package_dir, work_dir):
        workspace = setup_claude_skills(package_dir, work_dir)
        assert (workspace / "scripts" / "generate_image.py").exists()

    def test_copies_research_lookup_to_root(self, package_dir, work_dir):
        """research_lookup.py should be at workspace root (not in scripts/)."""
        workspace = setup_claude_skills(package_dir, work_dir)
        assert (workspace / "research_lookup.py").exists()

    def test_no_skill_md_files_copied(self, package_dir, work_dir):
        """SKILL.md files should not end up in the workspace."""
        workspace = setup_claude_skills(package_dir, work_dir)
        skill_files = list(workspace.rglob("SKILL.md"))
        assert len(skill_files) == 0

    def test_stable_path_for_same_work_dir(self, package_dir, work_dir):
        """Same work_dir should produce the same workspace path."""
        ws1 = setup_claude_skills(package_dir, work_dir)
        ws2 = setup_claude_skills(package_dir, work_dir)
        assert ws1 == ws2

    def test_idempotent(self, package_dir, work_dir):
        """Running setup twice should not fail or corrupt files."""
        ws1 = setup_claude_skills(package_dir, work_dir)
        ws2 = setup_claude_skills(package_dir, work_dir)
        assert ws1 == ws2
        assert (ws2 / "WRITER.md").read_text() == "# Test WRITER instructions"

    def test_works_when_claude_skills_exists_in_work_dir(self, package_dir, work_dir):
        """Even if work_dir has .claude/skills/, workspace should be clean."""
        existing = work_dir / ".claude" / "skills" / "some-skill"
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("existing skill")

        workspace = setup_claude_skills(package_dir, work_dir)
        # Workspace should NOT have .claude/ at all
        assert not (workspace / ".claude").exists()
        # Original .claude/skills/ should be untouched
        assert (work_dir / ".claude" / "skills" / "some-skill" / "SKILL.md").exists()

    def test_different_work_dirs_get_different_workspaces(self, package_dir, tmp_path):
        """Different work_dirs should produce different workspace paths."""
        wd1 = tmp_path / "project_a"
        wd1.mkdir()
        wd2 = tmp_path / "project_b"
        wd2.mkdir()

        ws1 = setup_claude_skills(package_dir, wd1)
        ws2 = setup_claude_skills(package_dir, wd2)
        assert ws1 != ws2
