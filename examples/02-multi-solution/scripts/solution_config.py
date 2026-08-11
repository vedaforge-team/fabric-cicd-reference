"""
Load and validate the Fabric solution registry (config/solutions.yml).

Shared by detect_changes.py and deploy_fabric_workspace.py so that both agree
on which solutions exist and where their artifacts live. Validation runs on
load: a malformed registry should fail in a unit test or at the top of a
pipeline step, not halfway through a deployment.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "solutions.yml"

ENVIRONMENTS = ("dev", "uat", "prod")


class ConfigError(ValueError):
    """Raised when config/solutions.yml is missing, malformed or inconsistent."""


class Solution:
    """One Fabric solution: a source folder plus its per-environment targets."""

    def __init__(self, key, display_name, source_path, workspaces):
        self.key = key
        self.display_name = display_name
        self.source_path = source_path
        self.workspaces = workspaces

    def workspace_name(self, environment: str) -> str:
        return self.workspaces[environment.lower()]["name"]

    def workspace_id_variable(self, environment: str) -> str:
        return self.workspaces[environment.lower()]["id_variable"]

    def owns(self, path: str) -> bool:
        """True if a repository-relative path belongs to this solution."""
        return path == self.source_path or path.startswith(self.source_path + "/")

    def __repr__(self):
        return "Solution(key={!r}, source_path={!r})".format(self.key, self.source_path)


class Registry:
    """The parsed contents of config/solutions.yml."""

    def __init__(self, solutions, ignore_paths, framework_paths):
        self.solutions = solutions
        self.ignore_paths = ignore_paths
        self.framework_paths = framework_paths

    @property
    def keys(self) -> List[str]:
        return [solution.key for solution in self.solutions]

    def get(self, key: str) -> Solution:
        for solution in self.solutions:
            if solution.key == key.lower():
                return solution
        raise ConfigError(
            "Unknown solution {!r}. Known solutions: {}".format(key, ", ".join(self.keys))
        )


def _require_mapping(value, label):
    if not isinstance(value, dict):
        raise ConfigError("{} must be a mapping, got {}".format(label, type(value).__name__))
    return value


def _parse_path_rules(raw, label) -> Dict[str, List[str]]:
    raw = raw or {}
    _require_mapping(raw, label)
    rules = {
        "prefixes": list(raw.get("prefixes") or []),
        "suffixes": list(raw.get("suffixes") or []),
        "exact": list(raw.get("exact") or []),
    }
    for prefix in rules["prefixes"]:
        if not prefix.endswith("/"):
            raise ConfigError(
                "{}.prefixes entry {!r} must end with '/' so it cannot match a "
                "similarly named file".format(label, prefix)
            )
    return rules


def _parse_solution(raw, index) -> Solution:
    label = "solutions[{}]".format(index)
    _require_mapping(raw, label)

    key = raw.get("key")
    if not key or not isinstance(key, str):
        raise ConfigError("{}.key is required".format(label))
    if key != key.lower():
        raise ConfigError(
            "{}.key {!r} must be lowercase. The key is used for Azure DevOps "
            "output variables and stage names, which are easier to reason about "
            "when case is fixed.".format(label, key)
        )

    source_path = raw.get("source_path")
    if not source_path or not isinstance(source_path, str):
        raise ConfigError("{}.source_path is required".format(label))
    if source_path.startswith("/") or source_path.endswith("/"):
        raise ConfigError(
            "{}.source_path {!r} must not start or end with '/'".format(label, source_path)
        )
    if source_path in (".", "./", ".."):
        raise ConfigError(
            "{}.source_path {!r} would scope a deployment to the repository "
            "root. Each solution must resolve to its own folder.".format(label, source_path)
        )

    workspaces = _require_mapping(raw.get("workspaces"), "{}.workspaces".format(label))
    parsed_workspaces = {}
    for environment in ENVIRONMENTS:
        entry = workspaces.get(environment)
        if entry is None:
            raise ConfigError(
                "{}.workspaces.{} is required".format(label, environment)
            )
        _require_mapping(entry, "{}.workspaces.{}".format(label, environment))
        for field in ("name", "id_variable"):
            if not entry.get(field):
                raise ConfigError(
                    "{}.workspaces.{}.{} is required".format(label, environment, field)
                )
        parsed_workspaces[environment] = {
            "name": entry["name"],
            "id_variable": entry["id_variable"],
        }

    return Solution(
        key=key,
        display_name=raw.get("display_name") or key.upper(),
        source_path=source_path,
        workspaces=parsed_workspaces,
    )


def load_registry(config_path: Optional[Path] = None) -> Registry:
    """Parse and validate the solution registry."""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.is_file():
        raise ConfigError("Solution registry not found at {}".format(path))

    with open(str(path), "r") as handle:
        raw = yaml.safe_load(handle)

    _require_mapping(raw, "config/solutions.yml")

    raw_solutions = raw.get("solutions")
    if not isinstance(raw_solutions, list) or not raw_solutions:
        raise ConfigError("config/solutions.yml must define a non-empty 'solutions' list")

    solutions = [_parse_solution(entry, index) for index, entry in enumerate(raw_solutions)]

    seen_keys = set()
    for solution in solutions:
        if solution.key in seen_keys:
            raise ConfigError("Duplicate solution key {!r}".format(solution.key))
        seen_keys.add(solution.key)

    # Overlapping source paths would make change detection ambiguous and could
    # let one solution's deployment sweep in another solution's artifacts.
    for outer in solutions:
        for inner in solutions:
            if outer is inner:
                continue
            if outer.source_path == inner.source_path:
                raise ConfigError(
                    "Solutions {!r} and {!r} share source_path {!r}".format(
                        outer.key, inner.key, outer.source_path
                    )
                )
            if inner.source_path.startswith(outer.source_path + "/"):
                raise ConfigError(
                    "source_path {!r} ({}) is nested inside {!r} ({}). Solution "
                    "folders must not overlap.".format(
                        inner.source_path, inner.key, outer.source_path, outer.key
                    )
                )

    return Registry(
        solutions=solutions,
        ignore_paths=_parse_path_rules(raw.get("ignore_paths"), "ignore_paths"),
        framework_paths=_parse_path_rules(raw.get("framework_paths"), "framework_paths"),
    )


def count_fabric_items(directory: Path) -> int:
    """Count Fabric items under a directory.

    A Fabric item is a folder containing a .platform descriptor, which is what
    fabric-cicd looks for when it walks the repository directory.
    """
    directory = Path(directory)
    if not directory.is_dir():
        return 0
    return sum(1 for _ in directory.rglob(".platform"))


def resolve_source_directory(solution: Solution, repo_root: Optional[Path] = None) -> Path:
    root = Path(repo_root) if repo_root else REPO_ROOT
    return (root / solution.source_path).resolve()


def is_repository_root(candidate: Path, repo_root: Optional[Path] = None) -> bool:
    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    return Path(candidate).resolve() == root


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}
