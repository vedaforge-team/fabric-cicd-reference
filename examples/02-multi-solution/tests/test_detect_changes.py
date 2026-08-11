"""
Change detection tests.

These cover the scenarios the pipeline is meant to guarantee, and they run
against the real config/solutions.yml so that editing the registry without
thinking about detection breaks a test rather than a deployment.

    python3 -m unittest discover -s tests -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from detect_changes import analyse, classify, parse_override  # noqa: E402
from solution_config import ConfigError, load_registry  # noqa: E402


class DetectionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = load_registry()

    def detect(self, paths):
        return analyse(paths, self.registry)

    def assertAffected(self, paths, expected):
        result = self.detect(paths)
        self.assertEqual(result["affected"], expected)
        for key in self.registry.keys:
            self.assertEqual(
                result["solutions"][key],
                key in expected,
                "solution {!r} state wrong for {}".format(key, paths),
            )


class TestScenarioMatrix(DetectionTestCase):
    """The six scenarios the pipeline has to get right."""

    def test_a_ved_only(self):
        self.assertAffected(
            [
                "fabric-workspaces/Ved/Test_Notebook_02.Notebook/notebook-content.py",
                "fabric-workspaces/Ved/Test_Data_Pipeline_01.DataPipeline/pipeline-content.json",
            ],
            ["ved"],
        )

    def test_b_fin_only(self):
        self.assertAffected(["fabric-workspaces/Fin/Fin_Notebook_01.Notebook/.platform"], ["fin"])

    def test_c_hr_only(self):
        self.assertAffected(["fabric-workspaces/HR/HR_Notebook_01.Notebook/notebook-content.py"], ["hr"])

    def test_d_ved_and_hr(self):
        self.assertAffected(
            [
                "fabric-workspaces/Ved/Test_Notebook_02.Notebook/notebook-content.py",
                "fabric-workspaces/HR/HR_Notebook_01.Notebook/notebook-content.py",
            ],
            ["ved", "hr"],
        )

    def test_e_all_three(self):
        self.assertAffected(
            [
                "fabric-workspaces/Ved/Test_Notebook_02.Notebook/notebook-content.py",
                "fabric-workspaces/Fin/Fin_Notebook_01.Notebook/notebook-content.py",
                "fabric-workspaces/HR/HR_Notebook_01.Notebook/notebook-content.py",
            ],
            ["ved", "fin", "hr"],
        )

    def test_f_docs_only(self):
        result = self.detect(["README.md", "docs/article-02/SCREENSHOT_PLAN.md"])
        self.assertEqual(result["affected"], [])
        self.assertFalse(result["framework_changed"])
        self.assertEqual(len(result["ignored_files"]), 2)


class TestOrdering(DetectionTestCase):
    def test_affected_follows_registry_order(self):
        """Order is registry order, not the order files happened to change."""
        result = self.detect(
            [
                "fabric-workspaces/HR/a.Notebook/notebook-content.py",
                "fabric-workspaces/Fin/b.Notebook/notebook-content.py",
                "fabric-workspaces/Ved/c.Notebook/notebook-content.py",
            ]
        )
        self.assertEqual(result["affected"], ["ved", "fin", "hr"])


class TestDocumentationHandling(DetectionTestCase):
    def test_solution_readme_does_not_trigger_deployment(self):
        """fabric-workspaces/Ved/Readme.md is an Azure DevOps folder placeholder, not an artifact."""
        result = self.detect(["fabric-workspaces/Ved/Readme.md"])
        self.assertEqual(result["affected"], [])
        self.assertIn("fabric-workspaces/Ved/Readme.md", result["ignored_files"])

    def test_markdown_beside_real_change_does_not_mask_it(self):
        result = self.detect(
            ["README.md", "fabric-workspaces/Ved/Test_Notebook_02.Notebook/notebook-content.py"]
        )
        self.assertEqual(result["affected"], ["ved"])

    def test_docs_folder_ignored(self):
        result = self.detect(["docs/article-02/notes.md", "images/article-02/x.png"])
        self.assertEqual(result["affected"], [])
        self.assertEqual(result["unclassified_files"], [])


class TestFrameworkChanges(DetectionTestCase):
    """A framework edit must not deploy anything on its own."""

    def test_scripts_change_is_framework_only(self):
        result = self.detect(["scripts/deploy_fabric_workspace.py"])
        self.assertEqual(result["affected"], [])
        self.assertTrue(result["framework_changed"])

    def test_pipeline_change_is_framework_only(self):
        result = self.detect(["azure-pipelines.yml", "templates/solution-stages.yml"])
        self.assertEqual(result["affected"], [])
        self.assertTrue(result["framework_changed"])

    def test_config_change_is_framework_only(self):
        """Editing the registry changes how a solution would deploy, not what it contains."""
        result = self.detect(["config/solutions.yml"])
        self.assertEqual(result["affected"], [])
        self.assertTrue(result["framework_changed"])

    def test_framework_and_solution_together(self):
        result = self.detect(
            ["scripts/detect_changes.py", "fabric-workspaces/Ved/Test_Notebook_02.Notebook/notebook-content.py"]
        )
        self.assertEqual(result["affected"], ["ved"])
        self.assertTrue(result["framework_changed"])


class TestEdgeCases(DetectionTestCase):
    def test_empty_changeset(self):
        result = self.detect([])
        self.assertEqual(result["affected"], [])
        self.assertFalse(result["framework_changed"])

    def test_unclassified_path_is_reported_not_deployed(self):
        result = self.detect(["some_new_top_level_file.txt"])
        self.assertEqual(result["affected"], [])
        self.assertEqual(result["unclassified_files"], ["some_new_top_level_file.txt"])

    def test_similar_prefix_does_not_match_solution(self):
        """'Vedanta/...' must not be read as a change inside 'Ved/'."""
        result = self.detect(["fabric-workspaces/Vedanta/thing.Notebook/notebook-content.py"])
        self.assertEqual(result["affected"], [])
        self.assertIn("fabric-workspaces/Vedanta/thing.Notebook/notebook-content.py", result["unclassified_files"])

    def test_case_sensitivity(self):
        """Agents run Linux. 'ved/' is not 'Ved/'."""
        result = self.detect(["fabric-workspaces/ved/thing.Notebook/notebook-content.py"])
        self.assertEqual(result["affected"], [])

    def test_deleted_files_still_classify(self):
        """git diff --name-only lists deletions too; they are real changes."""
        result = self.detect(["fabric-workspaces/Ved/Old_Notebook.Notebook/.platform"])
        self.assertEqual(result["affected"], ["ved"])

    def test_classify_returns_owner(self):
        kind, key = classify("fabric-workspaces/Fin/x.Notebook/.platform", self.registry)
        self.assertEqual((kind, key), ("solution", "fin"))


class TestOverride(DetectionTestCase):
    def test_override_selects_named_solutions(self):
        self.assertEqual(parse_override("ved,hr", self.registry), ["ved", "hr"])

    def test_override_is_case_and_space_tolerant(self):
        self.assertEqual(parse_override(" VED , Hr ", self.registry), ["ved", "hr"])

    def test_override_uses_registry_order(self):
        self.assertEqual(parse_override("hr,ved", self.registry), ["ved", "hr"])

    def test_override_rejects_unknown_solution(self):
        with self.assertRaises(ConfigError):
            parse_override("ved,payroll", self.registry)


if __name__ == "__main__":
    unittest.main()
