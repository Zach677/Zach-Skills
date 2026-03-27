from __future__ import annotations

import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import new_skill  # type: ignore  # noqa: E402


class NormalizeSkillNameTests(unittest.TestCase):
    def test_normalize_skill_name_slugifies_human_title(self) -> None:
        self.assertEqual(new_skill.normalize_skill_name("My New Skill"), "my-new-skill")

    def test_normalize_skill_name_rejects_empty_slug(self) -> None:
        with self.assertRaises(ValueError):
            new_skill.normalize_skill_name("!!!")


class ScaffoldSkillTests(unittest.TestCase):
    def test_scaffold_skill_creates_expected_files(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            created = new_skill.scaffold_skill(
                repo_root=root,
                raw_name="My New Skill",
                description="Use when creating a new reusable skill.",
                include_extend=True,
                include_agent=True,
            )

            skill_dir = root / "skills" / "my-new-skill"
            self.assertEqual(created, skill_dir)
            self.assertTrue((skill_dir / "SKILL.md").exists())
            self.assertTrue((skill_dir / "README.md").exists())
            self.assertTrue((skill_dir / "EXTEND.example.md").exists())
            self.assertTrue((skill_dir / "agents" / "openai.yaml").exists())
            self.assertTrue((skill_dir / "references" / "README.md").exists())
            self.assertTrue((skill_dir / "scripts" / "README.md").exists())

            skill_md = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("name: my-new-skill", skill_md)
            self.assertIn("Use when creating a new reusable skill.", skill_md)

    def test_scaffold_skill_omits_optional_files_when_not_requested(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)

            skill_dir = new_skill.scaffold_skill(
                repo_root=root,
                raw_name="Lean Skill",
                description="Use when the lean template is enough.",
                include_extend=False,
                include_agent=False,
            )

            self.assertFalse((skill_dir / "EXTEND.example.md").exists())
            self.assertFalse((skill_dir / "agents").exists())

    def test_scaffold_skill_refuses_to_overwrite_existing_directory(self) -> None:
        with TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            existing = root / "skills" / "my-new-skill"
            existing.mkdir(parents=True)

            with self.assertRaises(FileExistsError):
                new_skill.scaffold_skill(
                    repo_root=root,
                    raw_name="My New Skill",
                    description="Use when creating a new reusable skill.",
                    include_extend=True,
                    include_agent=True,
                )


if __name__ == "__main__":
    unittest.main()
