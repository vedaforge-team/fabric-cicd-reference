"""
Deploy one Microsoft Fabric solution to one workspace.

The pipeline owns orchestration. This script owns authentication, workspace
configuration, validation mode, orphan cleanup, and fabric-cicd publish
behaviour. All environment-specific values are injected at runtime.

One solution, one environment, one invocation. There is no per-solution copy of
this file: the solution is a parameter, and the source folder and target
workspace are resolved from config/solutions.yml plus Azure DevOps variables.

    SOLUTION_KEY=ved  TARGET_ENVIRONMENT_NAME=UAT   -> Ved/  -> Ved-UAT
    SOLUTION_KEY=hr   TARGET_ENVIRONMENT_NAME=PROD  -> HR/   -> HR-Prod
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))

from solution_config import (  # noqa: E402
    REPO_ROOT,
    ConfigError,
    count_fabric_items,
    is_repository_root,
    load_registry,
    resolve_source_directory,
)

# The Fabric SDK is imported lazily rather than at module load. Everything up
# to and including the empty-source guard is plain path and config handling, so
# keeping the import out of the way lets those checks run - and be unit tested -
# on a machine that has no fabric-cicd installed. The pipeline installs it
# before this script runs.
def _load_fabric_sdk():
    from azure.identity import ClientSecretCredential
    from fabric_cicd import (
        FabricWorkspace,
        append_feature_flag,
        change_log_level,
        publish_all_items,
        unpublish_all_orphan_items,
    )

    return {
        "ClientSecretCredential": ClientSecretCredential,
        "FabricWorkspace": FabricWorkspace,
        "append_feature_flag": append_feature_flag,
        "change_log_level": change_log_level,
        "publish_all_items": publish_all_items,
        "unpublish_all_orphan_items": unpublish_all_orphan_items,
    }


DEFAULT_ITEM_TYPES = [
    "DataPipeline",
    "Lakehouse",
    "Notebook",
    "SemanticModel",
    # "Warehouse" is intentionally excluded. Warehouse schema deployment must
    # be handled separately to avoid schema reset risk during fabric-cicd publish.
    "Environment",
    "Eventhouse",
    "Eventstream",
    "KQLDatabase",
    "KQLQueryset",
    "Dataflow",
    "MirroredDatabase",
    "MLExperiment",
    "SparkJobDefinition",
    "SQLDatabase",
    "VariableLibrary",
    "Reflex",
    "Report",
]


def read_env(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name, default)
    if isinstance(value, str):
        value = value.strip()
    return value


def read_bool(name: str, default: bool = False) -> bool:
    raw_value = read_env(name)
    if raw_value is None or raw_value == "":
        return default
    return raw_value.lower() in {"1", "true", "yes", "y"}


def read_csv(name: str, default: Iterable[str] | None = None) -> list[str]:
    raw_value = read_env(name)
    if not raw_value:
        return list(default or [])
    return [value.strip() for value in raw_value.split(",") if value.strip()]


def require_env(names: Iterable[str]) -> None:
    missing = [name for name in names if not read_env(name)]
    if missing:
        print(
            "ERROR: Missing required environment variables: " + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)


def fail(message: str) -> None:
    print("ERROR: {}".format(message), file=sys.stderr)
    sys.exit(1)


def resolve_repository_directory(solution) -> Path:
    """Work out which folder to deploy, and refuse anything unsafe.

    REPOSITORY_DIRECTORY may be set explicitly by the pipeline; otherwise it is
    derived from the solution's source_path. There is deliberately no fallback
    to the repository root: a root-scoped deployment would sweep every
    solution's artifacts into a single workspace, and the orphan cleanup that
    follows would then be evaluated against the wrong item set.
    """
    override = read_env("REPOSITORY_DIRECTORY")
    if override:
        directory = Path(override).resolve()
    else:
        directory = resolve_source_directory(solution)

    if is_repository_root(directory):
        fail(
            "REPOSITORY_DIRECTORY resolved to the repository root ({}). "
            "Deployments must be scoped to a single solution folder such as "
            "'{}'.".format(directory, solution.source_path)
        )

    if not directory.is_dir():
        fail(
            "Source directory {} does not exist. Expected solution '{}' at "
            "'{}'.".format(directory, solution.key, solution.source_path)
        )

    return directory


def assert_source_not_empty(directory: Path, solution, environment: str) -> int:
    """Stop before any Fabric call if the solution folder holds no items.

    This runs ahead of unpublish_all_orphan_items on purpose. An empty source
    folder combined with orphan removal means "every item in the target is an
    orphan", which would empty the workspace. A solution folder that has been
    created but not yet populated from its Development workspace is a normal
    intermediate state, so this has to fail safely rather than proceed.
    """
    item_count = count_fabric_items(directory)
    if item_count > 0:
        return item_count

    if read_bool("ALLOW_EMPTY_SOURCE"):
        print(
            "WARNING: {} contains no Fabric items, but ALLOW_EMPTY_SOURCE is set. "
            "Continuing.".format(directory)
        )
        return 0

    fail(
        "Solution '{}' has no Fabric items under {}.\n"
        "Refusing to deploy to {} because orphan removal would treat every item "
        "in the target workspace as an orphan and delete it.\n"
        "Connect the Development workspace to this folder and commit its items "
        "first. Set ALLOW_EMPTY_SOURCE=true only if emptying the target is "
        "genuinely intended.".format(solution.key, directory, environment)
    )
    return 0


def build_workspace(repository_directory: Path, sdk):
    credential = sdk["ClientSecretCredential"](
        tenant_id=read_env("TENANT_ID"),
        client_id=read_env("CLIENT_ID"),
        client_secret=read_env("CLIENT_SECRET"),
    )

    return sdk["FabricWorkspace"](
        workspace_id=read_env("TARGET_WORKSPACE_ID"),
        environment=read_env("TARGET_ENVIRONMENT_NAME"),
        repository_directory=str(repository_directory),
        item_type_in_scope=read_csv("ITEM_TYPES_IN_SCOPE", DEFAULT_ITEM_TYPES),
        token_credential=credential,
        exclude_paths=read_csv("EXCLUDE_FOLDERS"),
    )


def print_run_context(solution, environment, directory, item_count) -> None:
    print("=" * 56)
    print("FABRIC DEPLOYMENT")
    print("=" * 56)
    print("Solution:             {} ({})".format(solution.display_name, solution.key))
    print("Target environment:   {}".format(environment))
    print("Target workspace:     {}".format(solution.workspace_name(environment)))
    print("Workspace ID source:  {}".format(solution.workspace_id_variable(environment)))
    print("Repository directory: {}".format(directory))
    print("Fabric items found:   {}".format(item_count))
    print("Validation only:      {}".format(read_bool("VALIDATE_ONLY")))
    print("Remove orphans:       {}".format(read_bool("REMOVE_ORPHANS", True)))
    print("Shortcut publishing:  {}".format(read_bool("ENABLE_SHORTCUT_PUBLISH", True)))
    print("Item types in scope:  {}".format(read_csv("ITEM_TYPES_IN_SCOPE", DEFAULT_ITEM_TYPES)))
    print("Excluded folders:     {}".format(read_csv("EXCLUDE_FOLDERS") or "none"))
    print("=" * 56)


def main() -> None:
    require_env(
        [
            "SOLUTION_KEY",
            "TENANT_ID",
            "CLIENT_ID",
            "CLIENT_SECRET",
            "TARGET_WORKSPACE_ID",
            "TARGET_ENVIRONMENT_NAME",
        ]
    )

    solution_key = read_env("SOLUTION_KEY")
    environment = read_env("TARGET_ENVIRONMENT_NAME")

    try:
        registry = load_registry()
        solution = registry.get(solution_key)
        solution.workspace_name(environment)
    except ConfigError as error:
        fail(str(error))
    except KeyError:
        fail(
            "Unknown environment {!r} for solution {!r}. Expected one of: dev, "
            "uat, prod.".format(environment, solution_key)
        )

    repository_directory = resolve_repository_directory(solution)
    item_count = assert_source_not_empty(repository_directory, solution, environment)

    # Everything above this line is local validation. Nothing has touched Fabric
    # yet, and nothing will if the guards above rejected the run.
    sdk = _load_fabric_sdk()

    sdk["change_log_level"](read_env("LOG_LEVEL", "INFO") or "INFO")

    if read_bool("ENABLE_SHORTCUT_PUBLISH", True):
        sdk["append_feature_flag"]("enable_shortcut_publish")

    # Built before the validate-only check on purpose. Constructing the
    # FabricWorkspace authenticates the service principal, resolves the target
    # workspace and parses every item in the source folder, so it is the part
    # that actually validates. Returning before this would make develop builds
    # green without checking anything.
    workspace = build_workspace(repository_directory, sdk)

    print_run_context(solution, environment, repository_directory, item_count)

    if read_bool("VALIDATE_ONLY"):
        print("Validation-only mode. No workspace changes applied.")
        return

    if read_bool("REMOVE_ORPHANS", True):
        sdk["unpublish_all_orphan_items"](workspace)
    else:
        print("Orphan cleanup skipped because REMOVE_ORPHANS=false.")

    sdk["publish_all_items"](workspace)
    print(
        "Deployment completed successfully: {} -> {} ({}).".format(
            solution.display_name, solution.workspace_name(environment), environment
        )
    )


if __name__ == "__main__":
    main()
