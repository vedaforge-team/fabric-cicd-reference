"""
Work out which Fabric solutions a commit actually touched.

The pipeline runs this once, up front. Everything downstream is conditioned on
its output variables, so a change under Ved/ never causes Fin or HR to deploy.

Diff baseline
-------------
There is no single "previous commit" that is correct in every situation, so the
baseline is chosen from the shape of HEAD:

  merge commit    HEAD^1..HEAD   first parent is the target branch before the
                                 merge, so this is exactly what the merge added.
                                 Covers Azure DevOps PR builds, which check out
                                 a merge of the source into the target.
  normal commit   HEAD~1..HEAD   direct commits (Fabric commits to develop) and
                                 squash merges, where the parent is the previous
                                 state of the branch.
  root commit     everything     nothing to compare against.

Known limitation: a push of several commits at once to a branch is evaluated
from HEAD~1, so only the last commit is inspected. Promotion to release and main
happens through pull requests, where HEAD is a merge or squash commit and the
full change set is seen, so this only affects direct pushes to develop, which
are validate-only. Use --base, or the solutionsOverride pipeline parameter, when
a wider range needs to be evaluated.

Usage
-----
    python scripts/detect_changes.py                      # human readable
    python scripts/detect_changes.py --format azdo        # + pipeline variables
    python scripts/detect_changes.py --base main --head HEAD
    python scripts/detect_changes.py --solutions ved,hr   # bypass detection
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solution_config import REPO_ROOT, ConfigError, Registry, load_registry  # noqa: E402

IGNORED = "ignored"
SOLUTION = "solution"
FRAMEWORK = "framework"
UNCLASSIFIED = "unclassified"

BANNER = "=" * 56


class GitError(RuntimeError):
    pass


def run_git(args: List[str], repo_root: Path) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=str(repo_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if result.returncode != 0:
        raise GitError(
            "git {} failed ({}): {}".format(
                " ".join(args), result.returncode, result.stderr.strip()
            )
        )
    return result.stdout.strip()


def assert_full_history(repo_root: Path) -> None:
    """Refuse to run against a shallow clone.

    A shallow clone has no parent commit to diff against. Git reports an empty
    or failing diff rather than an error, which would look like "nothing
    changed" and silently skip every deployment. Failing loudly here is the
    difference between a visible problem and a false negative.
    """
    if run_git(["rev-parse", "--is-shallow-repository"], repo_root) == "true":
        raise GitError(
            "This is a shallow clone, so there is no history to diff against.\n"
            "Set 'fetchDepth: 0' on the checkout step, or disable shallow fetch "
            "in the pipeline settings."
        )


def resolve_range(repo_root: Path, base: Optional[str], head: str) -> Tuple[Optional[str], str, str]:
    """Return (base, head, reason). A base of None means 'treat everything as changed'."""
    if base:
        return base, head, "explicit --base"

    assert_full_history(repo_root)

    # rev-list --parents prints: <commit> <parent1> [<parent2> ...]
    parts = run_git(["rev-list", "--parents", "-n", "1", head], repo_root).split()
    parent_count = len(parts) - 1

    if parent_count >= 2:
        return head + "^1", head, "merge commit (first parent)"
    if parent_count == 1:
        return head + "~1", head, "single parent"
    return None, head, "root commit (no parent)"


def changed_files(repo_root: Path, base: Optional[str], head: str) -> List[str]:
    if base is None:
        output = run_git(["ls-tree", "-r", "--name-only", head], repo_root)
    else:
        output = run_git(["diff", "--name-only", base, head], repo_root)
    return [line.strip() for line in output.splitlines() if line.strip()]


def _matches(path: str, rules: Dict[str, List[str]]) -> bool:
    if path in rules["exact"]:
        return True
    if any(path.startswith(prefix) for prefix in rules["prefixes"]):
        return True
    if any(path.endswith(suffix) for suffix in rules["suffixes"]):
        return True
    return False


def classify(path: str, registry: Registry) -> Tuple[str, Optional[str]]:
    """Classify one repository-relative path.

    Order matters. Documentation is checked first so that a solution's own
    Readme.md does not trigger a deployment of that solution.
    """
    if _matches(path, registry.ignore_paths):
        return IGNORED, None
    for solution in registry.solutions:
        if solution.owns(path):
            return SOLUTION, solution.key
    if _matches(path, registry.framework_paths):
        return FRAMEWORK, None
    return UNCLASSIFIED, None


def analyse(paths: List[str], registry: Registry) -> Dict:
    """Pure function: changed paths in, decision out. This is what the tests drive."""
    solutions = {solution.key: False for solution in registry.solutions}
    buckets = {IGNORED: [], FRAMEWORK: [], UNCLASSIFIED: []}
    owned = {}

    for path in paths:
        kind, key = classify(path, registry)
        if kind == SOLUTION:
            solutions[key] = True
            owned.setdefault(key, []).append(path)
        else:
            buckets[kind].append(path)

    # Registry order, not dict order, so logs and screenshots are stable.
    affected = [s.key for s in registry.solutions if solutions[s.key]]

    return {
        "solutions": solutions,
        "affected": affected,
        "files_by_solution": owned,
        "ignored_files": buckets[IGNORED],
        "framework_files": buckets[FRAMEWORK],
        "unclassified_files": buckets[UNCLASSIFIED],
        "framework_changed": bool(buckets[FRAMEWORK]),
    }


def parse_override(raw: str, registry: Registry) -> List[str]:
    keys = [item.strip().lower() for item in raw.split(",") if item.strip()]
    unknown = [key for key in keys if key not in registry.keys]
    if unknown:
        raise ConfigError(
            "Unknown solution(s) in override: {}. Known solutions: {}".format(
                ", ".join(unknown), ", ".join(registry.keys)
            )
        )
    return [s.key for s in registry.solutions if s.key in keys]


def render_report(result: Dict, registry: Registry, context: Dict) -> str:
    lines = [BANNER, "FABRIC CHANGE DETECTION", BANNER, ""]

    if context.get("override"):
        lines.append("Mode        : MANUAL OVERRIDE (change detection bypassed)")
        lines.append("Override    : {}".format(context["override"]))
    else:
        lines.append("Mode        : automatic")
        lines.append("Baseline    : {}".format(context.get("range_label", "n/a")))

    lines.append("Branch      : {}".format(context.get("branch") or "unknown"))
    lines.append("")

    changed = context.get("changed_files", [])
    lines.append("Changed files: {}".format(len(changed)))
    for path in changed:
        kind, key = classify(path, registry)
        if kind == SOLUTION:
            note = "-> {}".format(key)
        elif kind == IGNORED:
            note = "[ignored: docs]"
        elif kind == FRAMEWORK:
            note = "[framework: validation only]"
        else:
            note = "[UNCLASSIFIED]"
        lines.append("  {:<58} {}".format(path, note))
    lines.append("")

    width = max(len(s.display_name) for s in registry.solutions)
    for solution in registry.solutions:
        state = "CHANGED" if result["solutions"][solution.key] else "NOT CHANGED"
        lines.append("{:<{w}} : {}".format(solution.display_name, state, w=width))
    lines.append("")

    lines.append("Framework changed : {}".format("YES" if result["framework_changed"] else "NO"))

    if result["unclassified_files"]:
        lines.append("")
        lines.append("WARNING: paths that match no rule (no deployment triggered):")
        for path in result["unclassified_files"]:
            lines.append("  {}".format(path))

    lines.append("")
    if result["affected"]:
        lines.append("Affected solutions:")
        for key in result["affected"]:
            lines.append("- {}".format(key))
    else:
        lines.append("Affected solutions: none")
    lines.append("")
    lines.append("Deployment candidates: {}".format(len(result["affected"])))

    if not result["affected"]:
        lines.append("")
        lines.append("No Fabric solution changes detected. Deployment skipped.")

    lines.append(BANNER)
    return "\n".join(lines)


def emit_azdo_variables(result: Dict, registry: Registry) -> None:
    """Publish results as Azure DevOps output variables.

    Consumed downstream as:
      dependencies.DetectChanges.outputs['Detect.detect.<key>']
    Values are strings, so stage conditions must compare against 'true'.
    """
    for solution in registry.solutions:
        value = "true" if result["solutions"][solution.key] else "false"
        print("##vso[task.setvariable variable={};isOutput=true]{}".format(solution.key, value))

    print(
        "##vso[task.setvariable variable=anySolution;isOutput=true]{}".format(
            "true" if result["affected"] else "false"
        )
    )
    print(
        "##vso[task.setvariable variable=frameworkChanged;isOutput=true]{}".format(
            "true" if result["framework_changed"] else "false"
        )
    )
    print(
        "##vso[task.setvariable variable=affected;isOutput=true]{}".format(
            ",".join(result["affected"])
        )
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Detect changed Fabric solutions.")
    parser.add_argument("--base", help="Baseline ref. Defaults to the parent of --head.")
    parser.add_argument("--head", default="HEAD", help="Ref to inspect. Defaults to HEAD.")
    parser.add_argument(
        "--format",
        choices=["text", "azdo"],
        default="text",
        help="'azdo' also emits Azure DevOps output variables.",
    )
    parser.add_argument(
        "--solutions",
        default="",
        help="Comma separated keys. Bypasses detection entirely.",
    )
    parser.add_argument("--json-out", help="Write the machine readable result here.")
    parser.add_argument("--config", help="Path to solutions.yml. Defaults to config/solutions.yml.")
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--fail-on-unclassified",
        action="store_true",
        help="Exit non-zero if any changed path matches no rule.",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()

    try:
        registry = load_registry(Path(args.config) if args.config else None)
    except ConfigError as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 2

    context = {"branch": os.environ.get("BUILD_SOURCEBRANCH", "")}
    override = args.solutions.strip()

    try:
        if override:
            keys = parse_override(override, registry)
            result = {
                "solutions": {s.key: (s.key in keys) for s in registry.solutions},
                "affected": keys,
                "files_by_solution": {},
                "ignored_files": [],
                "framework_files": [],
                "unclassified_files": [],
                "framework_changed": False,
            }
            context["override"] = override
            context["changed_files"] = []
            base, head = None, args.head
        else:
            base, head, reason = resolve_range(repo_root, args.base, args.head)
            files = changed_files(repo_root, base, head)
            result = analyse(files, registry)
            context["changed_files"] = files
            context["range_label"] = (
                "{}..{} ({})".format(base, head, reason) if base else "{} ({})".format(head, reason)
            )
    except (GitError, ConfigError) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 2

    print(render_report(result, registry, context))

    if args.format == "azdo":
        emit_azdo_variables(result, registry)

    if args.json_out:
        payload = dict(result)
        payload.update(
            {
                "schema_version": 1,
                "base": base,
                "head": head,
                "branch": context.get("branch"),
                "override": context.get("override", ""),
                "changed_files": context.get("changed_files", []),
            }
        )
        out_path = Path(args.json_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(out_path), "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
        print("\nWrote {}".format(out_path))

    if args.fail_on_unclassified and result["unclassified_files"]:
        print(
            "ERROR: {} changed path(s) matched no rule.".format(
                len(result["unclassified_files"])
            ),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
