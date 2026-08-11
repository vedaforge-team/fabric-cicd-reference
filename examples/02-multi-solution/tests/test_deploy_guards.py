"""
Deployment safety guards.

These run without fabric-cicd or azure-identity installed, because the guards
they cover all execute before the Fabric SDK is loaded. That is deliberate: the
empty-source check is the one piece of logic whose failure mode is destructive,
so it needs to be provable on a laptop rather than discovered against a real
workspace.

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import deploy_fabric_workspace as deploy  # noqa: E402
from solution_config import load_registry  # noqa: E402


@contextmanager
def environment(**values):
    """Temporarily set (or clear, with None) environment variables."""
    previous = {}
    for key, value in values.items():
        previous[key] = os.environ.get(key)
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


class GuardTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        cls.ved = cls.registry.get("ved")
        cls.fin = cls.registry.get("fin")


class TestEmptySourceGuard(GuardTestCase):
    """An empty solution folder must never reach orphan removal."""

    def test_populated_solution_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "Ved"
            for name in ("A.Notebook", "B.DataPipeline"):
                (directory / name).mkdir(parents=True)
                (directory / name / ".platform").write_text("{}")
            with environment(ALLOW_EMPTY_SOURCE=None):
                count = deploy.assert_source_not_empty(directory, self.ved, "UAT")
        self.assertEqual(count, 2)

    def test_empty_solution_folder_aborts(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "Fin"
            empty.mkdir()
            (empty / "Readme.md").write_text("auto-created placeholder\n")
            with environment(ALLOW_EMPTY_SOURCE=None):
                with self.assertRaises(SystemExit) as caught:
                    deploy.assert_source_not_empty(empty, self.fin, "UAT")
        self.assertEqual(caught.exception.code, 1)

    def test_readme_alone_is_not_a_fabric_item(self):
        """This is the exact current state of Fin/ and HR/ in this repository."""
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "HR"
            folder.mkdir()
            (folder / "Readme.md").write_text("x")
            self.assertEqual(deploy.count_fabric_items(folder), 0)

    def test_allow_empty_source_is_an_explicit_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "Fin"
            empty.mkdir()
            with environment(ALLOW_EMPTY_SOURCE="true"):
                count = deploy.assert_source_not_empty(empty, self.fin, "UAT")
        self.assertEqual(count, 0)

    def test_counts_items_exactly_in_a_controlled_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp) / "Ved"
            for name in ("A.Notebook", "B.DataPipeline", "C.Lakehouse"):
                (directory / name).mkdir(parents=True)
                (directory / name / ".platform").write_text("{}")
            with environment(ALLOW_EMPTY_SOURCE=None):
                self.assertEqual(
                    deploy.assert_source_not_empty(directory, self.ved, "UAT"), 3
                )

    def test_guard_verdict_follows_folder_contents(self):
        """The guard's verdict tracks what is actually in each solution folder.

        The folders ship empty in this example, so the guard blocks them, which
        is the intended state until a Development workspace is connected and its
        items committed. The assertion still holds once they are populated.
        """
        for solution in self.registry.solutions:
            directory = REPO_ROOT / solution.source_path
            populated = deploy.count_fabric_items(directory) > 0
            with environment(ALLOW_EMPTY_SOURCE=None):
                if populated:
                    self.assertGreater(
                        deploy.assert_source_not_empty(directory, solution, "UAT"), 0
                    )
                else:
                    with self.assertRaises(SystemExit):
                        deploy.assert_source_not_empty(directory, solution, "UAT")

    def test_item_is_recognised_by_platform_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Fin"
            (folder / "Thing.Notebook").mkdir(parents=True)
            (folder / "Thing.Notebook" / ".platform").write_text("{}")
            with environment(ALLOW_EMPTY_SOURCE=None):
                self.assertEqual(deploy.assert_source_not_empty(folder, self.fin, "UAT"), 1)


class TestRepositoryDirectoryScoping(GuardTestCase):
    """A deployment must never be scoped to the repository root."""

    def test_repository_root_is_rejected(self):
        with environment(REPOSITORY_DIRECTORY=str(REPO_ROOT)):
            with self.assertRaises(SystemExit) as caught:
                deploy.resolve_repository_directory(self.ved)
        self.assertEqual(caught.exception.code, 1)

    def test_dot_path_resolving_to_root_is_rejected(self):
        """The Article 01 default of './.' must not survive as a fallback."""
        with environment(REPOSITORY_DIRECTORY=str(REPO_ROOT / "fabric-workspaces" / "Ved" / ".." / "..")):
            with self.assertRaises(SystemExit) as caught:
                deploy.resolve_repository_directory(self.ved)
        self.assertEqual(caught.exception.code, 1)

    def test_missing_directory_is_rejected(self):
        with environment(REPOSITORY_DIRECTORY=str(REPO_ROOT / "NotARealSolution")):
            with self.assertRaises(SystemExit) as caught:
                deploy.resolve_repository_directory(self.ved)
        self.assertEqual(caught.exception.code, 1)

    def test_defaults_to_registry_source_path(self):
        with environment(REPOSITORY_DIRECTORY=None):
            resolved = deploy.resolve_repository_directory(self.ved)
        self.assertEqual(resolved, (REPO_ROOT / self.ved.source_path).resolve())

    def test_explicit_override_is_honoured(self):
        with environment(REPOSITORY_DIRECTORY=str(REPO_ROOT / self.ved.source_path)):
            resolved = deploy.resolve_repository_directory(self.ved)
        self.assertEqual(resolved, (REPO_ROOT / self.ved.source_path).resolve())

    def test_each_solution_resolves_to_its_own_folder(self):
        resolved = set()
        for solution in self.registry.solutions:
            with environment(REPOSITORY_DIRECTORY=None):
                resolved.add(deploy.resolve_repository_directory(solution))
        self.assertEqual(len(resolved), len(self.registry.solutions))


class TestEnvironmentReaders(GuardTestCase):
    def test_read_bool_variants(self):
        for raw, expected in [
            ("true", True), ("True", True), ("1", True), ("yes", True),
            ("false", False), ("0", False), ("", False), ("no", False),
        ]:
            with environment(SOME_FLAG=raw):
                self.assertEqual(deploy.read_bool("SOME_FLAG"), expected, raw)

    def test_read_bool_default_applies_when_unset(self):
        with environment(SOME_FLAG=None):
            self.assertTrue(deploy.read_bool("SOME_FLAG", True))
            self.assertFalse(deploy.read_bool("SOME_FLAG", False))

    def test_remove_orphans_defaults_to_true(self):
        """Article 01 behaviour: orphan removal is on unless switched off."""
        with environment(REMOVE_ORPHANS=None):
            self.assertTrue(deploy.read_bool("REMOVE_ORPHANS", True))

    def test_read_csv_falls_back_to_defaults(self):
        with environment(ITEM_TYPES_IN_SCOPE=""):
            self.assertEqual(
                deploy.read_csv("ITEM_TYPES_IN_SCOPE", deploy.DEFAULT_ITEM_TYPES),
                deploy.DEFAULT_ITEM_TYPES,
            )

    def test_read_csv_trims_entries(self):
        with environment(EXCLUDE_FOLDERS=" a , b ,, c "):
            self.assertEqual(deploy.read_csv("EXCLUDE_FOLDERS"), ["a", "b", "c"])


class TestItemTypePolicy(GuardTestCase):
    def test_warehouse_stays_excluded(self):
        """Warehouse publish can reset schema, so it is handled separately."""
        self.assertNotIn("Warehouse", deploy.DEFAULT_ITEM_TYPES)

    def test_article_01_item_types_preserved(self):
        for item_type in ("DataPipeline", "Lakehouse", "Notebook", "SemanticModel", "Report"):
            self.assertIn(item_type, deploy.DEFAULT_ITEM_TYPES)

    def test_item_types_match_article_01_set(self):
        self.assertEqual(len(deploy.DEFAULT_ITEM_TYPES), 17)


if __name__ == "__main__":
    unittest.main()
