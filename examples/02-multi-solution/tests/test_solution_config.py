"""
Registry validation, and the checks that stop configuration from drifting away
from the pipeline or from what is actually on disk.

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from solution_config import (  # noqa: E402
    ConfigError,
    count_fabric_items,
    is_repository_root,
    load_registry,
)

PIPELINE_PATH = REPO_ROOT / "azure-pipelines.yml"
SOLUTION_STAGES_TEMPLATE = "templates/solution-stages.yml"


def write_config(body):
    handle = tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False)
    yaml.safe_dump(body, handle)
    handle.close()
    return Path(handle.name)


def minimal_solution(key="ved", source_path="Ved"):
    return {
        "key": key,
        "display_name": key.upper(),
        "source_path": source_path,
        "workspaces": {
            "dev": {"name": key + "-Development", "id_variable": key.upper() + "_DEV_WORKSPACE_ID"},
            "uat": {"name": key + "-UAT", "id_variable": key.upper() + "_UAT_WORKSPACE_ID"},
            "prod": {"name": key + "-Prod", "id_variable": key.upper() + "_PROD_WORKSPACE_ID"},
        },
    }


class TestRealRegistry(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def test_expected_solutions(self):
        self.assertEqual(self.registry.keys, ["ved", "fin", "hr"])

    def test_source_paths_exist_on_disk(self):
        """Catches a case mismatch locally instead of on a Linux agent.

        macOS git is case-insensitive by default, so `is_dir()` alone would
        happily accept `fabric-workspaces/ved` for a folder actually named
        `Ved` - and then fail on the agent. Every path component is compared
        against the real directory listing instead.
        """
        for solution in self.registry.solutions:
            current = REPO_ROOT
            for part in Path(solution.source_path).parts:
                names = [entry.name for entry in current.iterdir() if entry.is_dir()]
                self.assertIn(
                    part,
                    names,
                    "source_path {!r}: {!r} does not match a directory name exactly".format(
                        solution.source_path, part
                    ),
                )
                current = current / part
            self.assertTrue(current.is_dir(), "missing folder {}".format(solution.source_path))

    def test_no_workspace_guids_in_config(self):
        """The registry must stay free of tenant-specific identifiers."""
        text = (REPO_ROOT / "config" / "solutions.yml").read_text()
        import re

        guids = re.findall(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            text,
        )
        self.assertEqual(guids, [], "config/solutions.yml contains GUID(s): {}".format(guids))

    def test_id_variables_are_unique(self):
        seen = []
        for solution in self.registry.solutions:
            for environment in ("dev", "uat", "prod"):
                seen.append(solution.workspace_id_variable(environment))
        self.assertEqual(len(seen), len(set(seen)), "duplicate workspace ID variable names")

    def test_workspace_lookup(self):
        ved = self.registry.get("ved")
        self.assertEqual(ved.workspace_name("uat"), "Ved-UAT")
        self.assertEqual(ved.workspace_id_variable("prod"), "VED_PROD_WORKSPACE_ID")

    def test_get_is_case_insensitive(self):
        self.assertEqual(self.registry.get("VED").key, "ved")

    def test_get_unknown_raises(self):
        with self.assertRaises(ConfigError):
            self.registry.get("payroll")


class TestPipelineDrift(unittest.TestCase):
    """azure-pipelines.yml declares solutions at compile time; the registry
    declares them at run time. If they disagree, a solution silently loses its
    stages or deploys with the wrong source path."""

    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()
        with open(str(PIPELINE_PATH)) as handle:
            cls.pipeline = yaml.safe_load(handle)

    def instantiations(self):
        found = []
        for stage in self.pipeline.get("stages", []):
            if isinstance(stage, dict) and stage.get("template") == SOLUTION_STAGES_TEMPLATE:
                found.append(stage.get("parameters", {}))
        return found

    def test_pipeline_declares_every_registered_solution(self):
        declared = [entry["solution"] for entry in self.instantiations()]
        self.assertEqual(
            declared,
            self.registry.keys,
            "azure-pipelines.yml and config/solutions.yml disagree on solutions",
        )

    def test_source_paths_match_registry(self):
        for entry in self.instantiations():
            solution = self.registry.get(entry["solution"])
            self.assertEqual(
                entry["sourcePath"],
                solution.source_path,
                "sourcePath for {!r} differs between pipeline and registry".format(solution.key),
            )

    def test_summary_stage_depends_on_every_solution_stage(self):
        summary = next(
            stage
            for stage in self.pipeline["stages"]
            if isinstance(stage, dict) and stage.get("stage") == "Summary"
        )
        depends = set(summary["dependsOn"])
        for key in self.registry.keys:
            for prefix in ("Validate_", "Deploy_UAT_", "Deploy_PROD_"):
                self.assertIn(
                    prefix + key,
                    depends,
                    "Summary stage does not depend on {}{}".format(prefix, key),
                )

    def test_detection_stage_checks_out_full_history(self):
        detect = next(
            stage
            for stage in self.pipeline["stages"]
            if isinstance(stage, dict) and stage.get("stage") == "DetectChanges"
        )
        checkout = detect["jobs"][0]["steps"][0]
        self.assertEqual(checkout.get("checkout"), "self")
        self.assertEqual(
            checkout.get("fetchDepth"),
            0,
            "change detection needs full history; fetchDepth must be 0",
        )


class TestRegistryValidation(unittest.TestCase):
    def load(self, solutions):
        path = write_config({"version": 1, "solutions": solutions})
        try:
            return load_registry(path)
        finally:
            path.unlink()

    def test_rejects_duplicate_keys(self):
        with self.assertRaises(ConfigError):
            self.load([minimal_solution("ved", "Ved"), minimal_solution("ved", "Other")])

    def test_rejects_shared_source_path(self):
        with self.assertRaises(ConfigError):
            self.load([minimal_solution("ved", "Shared"), minimal_solution("fin", "Shared")])

    def test_rejects_nested_source_paths(self):
        """Overlapping folders would make ownership of a path ambiguous."""
        with self.assertRaises(ConfigError):
            self.load([minimal_solution("ved", "Ved"), minimal_solution("fin", "Ved/Fin")])

    def test_rejects_repository_root_as_source(self):
        with self.assertRaises(ConfigError):
            self.load([minimal_solution("ved", ".")])

    def test_rejects_uppercase_key(self):
        with self.assertRaises(ConfigError):
            self.load([minimal_solution("VED", "Ved")])

    def test_rejects_missing_environment(self):
        solution = minimal_solution()
        del solution["workspaces"]["prod"]
        with self.assertRaises(ConfigError):
            self.load([solution])

    def test_rejects_missing_id_variable(self):
        solution = minimal_solution()
        del solution["workspaces"]["uat"]["id_variable"]
        with self.assertRaises(ConfigError):
            self.load([solution])

    def test_rejects_empty_solutions(self):
        with self.assertRaises(ConfigError):
            self.load([])

    def test_rejects_missing_file(self):
        with self.assertRaises(ConfigError):
            load_registry(REPO_ROOT / "config" / "does-not-exist.yml")


class TestSafetyHelpers(unittest.TestCase):
    def test_counts_fabric_items(self):
        """An item is a folder containing a .platform descriptor."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Ved"
            for name in ("A.Notebook", "B.DataPipeline", "C.Lakehouse"):
                (root / name).mkdir(parents=True)
                (root / name / ".platform").write_text("{}")
            self.assertEqual(count_fabric_items(root), 3)

    def test_empty_solution_folder_counts_zero(self):
        """A scaffolded but unpopulated folder has no items.

        This is the state a solution is in between creating its folder and
        connecting its Development workspace, and it is exactly what the
        empty-source guard exists to catch.
        """
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "Fin"
            folder.mkdir()
            (folder / "README.md").write_text("populated by Fabric git integration\n")
            self.assertEqual(count_fabric_items(folder), 0)

    def test_item_names_with_spaces_are_counted(self):
        """Fabric allows spaces in item names, e.g. 'Notebook_1 Copy.Notebook'."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "Ved"
            (root / "Notebook_1 Copy.Notebook").mkdir(parents=True)
            (root / "Notebook_1 Copy.Notebook" / ".platform").write_text("{}")
            self.assertEqual(count_fabric_items(root), 1)

    def test_missing_directory_counts_zero(self):
        self.assertEqual(count_fabric_items(REPO_ROOT / "NoSuchFolder"), 0)

    def test_repository_root_detected(self):
        self.assertTrue(is_repository_root(REPO_ROOT))
        self.assertTrue(is_repository_root(REPO_ROOT / "Ved" / ".."))
        self.assertFalse(is_repository_root(REPO_ROOT / "Ved"))


if __name__ == "__main__":
    unittest.main()
