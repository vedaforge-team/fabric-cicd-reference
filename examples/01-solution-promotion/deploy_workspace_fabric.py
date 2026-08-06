"""
Deploy Microsoft Fabric workspace items using Azure DevOps variables.

The pipeline owns orchestration. This script owns authentication, workspace
configuration, validation mode, orphan cleanup, and fabric-cicd publish behavior.
All environment-specific values are injected at runtime.
"""

import os
import sys
from typing import Iterable

from azure.identity import ClientSecretCredential
from fabric_cicd import (
    FabricWorkspace,
    append_feature_flag,
    change_log_level,
    publish_all_items,
    unpublish_all_orphan_items,
)


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
            "ERROR: Missing required environment variables: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)


def build_workspace() -> FabricWorkspace:
    credential = ClientSecretCredential(
        tenant_id=read_env("TENANT_ID"),
        client_id=read_env("CLIENT_ID"),
        client_secret=read_env("CLIENT_SECRET"),
    )

    repository_directory = os.path.abspath(
        read_env("REPOSITORY_DIRECTORY", "./.") or "./."
    )

    return FabricWorkspace(
        workspace_id=read_env("TARGET_WORKSPACE_ID"),
        environment=read_env("TARGET_ENVIRONMENT_NAME"),
        repository_directory=repository_directory,
        item_type_in_scope=read_csv("ITEM_TYPES_IN_SCOPE", DEFAULT_ITEM_TYPES),
        token_credential=credential,
        exclude_paths=read_csv("EXCLUDE_FOLDERS"),
    )


def print_run_context() -> None:
    print(f"Repository directory: {os.path.abspath(read_env('REPOSITORY_DIRECTORY', './.') or './.')}")
    print(f"Target environment:   {read_env('TARGET_ENVIRONMENT_NAME')}")
    print(f"Validation only:      {read_bool('VALIDATE_ONLY')}")
    print(f"Remove orphans:       {read_bool('REMOVE_ORPHANS', True)}")
    print(f"Shortcut publishing:  {read_bool('ENABLE_SHORTCUT_PUBLISH', True)}")
    print(f"Item types in scope:  {read_csv('ITEM_TYPES_IN_SCOPE', DEFAULT_ITEM_TYPES)}")
    print(f"Excluded folders:     {read_csv('EXCLUDE_FOLDERS') or 'none'}")


def main() -> None:
    require_env(
        [
            "TENANT_ID",
            "CLIENT_ID",
            "CLIENT_SECRET",
            "TARGET_WORKSPACE_ID",
            "TARGET_ENVIRONMENT_NAME",
        ]
    )

    change_log_level(read_env("LOG_LEVEL", "INFO") or "INFO")

    if read_bool("ENABLE_SHORTCUT_PUBLISH", True):
        append_feature_flag("enable_shortcut_publish")

    workspace = build_workspace()
    print_run_context()

    if read_bool("VALIDATE_ONLY"):
        print("Validation-only mode. No workspace changes applied.")
        return

    if read_bool("REMOVE_ORPHANS", True):
        unpublish_all_orphan_items(workspace)
    else:
        print("Orphan cleanup skipped because REMOVE_ORPHANS=false.")

    publish_all_items(workspace)
    print(f"Deployment completed successfully for {read_env('TARGET_ENVIRONMENT_NAME')}.")


if __name__ == "__main__":
    main()

