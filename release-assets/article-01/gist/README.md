# Article 01 Gist Package

This package contains the reusable files that can be published as a single Gist for Article 01.

## What the script does

`deploy_workspace_fabric.py` authenticates with a service principal, builds a `FabricWorkspace`, and either validates or deploys Fabric workspace items based on environment variables supplied by Azure DevOps or a local shell.

## Prerequisites

- Python 3.10 or later
- Access to a Fabric workspace
- A service principal with workspace permissions
- `fabric-cicd` and `azure-identity` installed

## Required Python packages

```text
fabric-cicd
azure-identity
```

## Required environment variables

```text
TENANT_ID
CLIENT_ID
CLIENT_SECRET
TARGET_WORKSPACE_ID
TARGET_ENVIRONMENT_NAME
```

Optional environment variables:

```text
REPOSITORY_DIRECTORY
EXCLUDE_FOLDERS
ITEM_TYPES_IN_SCOPE
LOG_LEVEL
ENABLE_SHORTCUT_PUBLISH
REMOVE_ORPHANS
VALIDATE_ONLY
```

## Minimum Fabric workspace permission

The service principal needs `Contributor` on the target Fabric workspace.

## Local validation command

```bash
python deploy_workspace_fabric.py
```

## Deployment command

```bash
VALIDATE_ONLY=false python deploy_workspace_fabric.py
```

## Expected successful outcome

- Validation mode reports that no workspace changes were applied.
- Deployment mode removes orphaned items when enabled.
- Deployment mode publishes the current repository state to the target workspace.

## Limitations

- Warehouse schema deployment is intentionally excluded from the item scope.
- The script depends on environment variables rather than interactive prompts.
- The script assumes the repository root contains the Fabric item folders to scan.

## Full repository

See the full reference implementation in the main repository:

[fabric-cicd-reference](../../../README.md)
