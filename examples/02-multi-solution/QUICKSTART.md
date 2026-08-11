# Quickstart

## Goal

Run three Fabric solutions through validation, UAT and PROD from one Azure
DevOps pipeline, deploying only the solutions a commit actually changed.

## Prerequisites

- An Azure DevOps repository with branches `develop`, `release` and `main`
- Three Fabric workspaces per solution: Development, UAT and PROD
- A service principal with access to every workspace it will deploy to
- Python 3.9 or later for local validation

## Steps

### 1. Copy the example to the repository root

The pipeline calls `scripts/...` relative to the repository root, so this layout
belongs at the top level, not in a subfolder.

### 2. Create the variable groups

Three groups, one per environment:

```
VG-Fabric-Dev    TENANT_ID, CLIENT_ID, CLIENT_SECRET,
                 VED_DEV_WORKSPACE_ID,  FIN_DEV_WORKSPACE_ID,  HR_DEV_WORKSPACE_ID
VG-Fabric-UAT    TENANT_ID, CLIENT_ID, CLIENT_SECRET,
                 VED_UAT_WORKSPACE_ID,  FIN_UAT_WORKSPACE_ID,  HR_UAT_WORKSPACE_ID
VG-Fabric-Prod   TENANT_ID, CLIENT_ID, CLIENT_SECRET,
                 VED_PROD_WORKSPACE_ID, FIN_PROD_WORKSPACE_ID, HR_PROD_WORKSPACE_ID
```

Mark `CLIENT_SECRET` as secret. Leave the workspace IDs non-secret so they are
readable as environment variables.

Workspace GUIDs come from the workspace URL:
`app.fabric.microsoft.com/groups/<GUID>/...`

### 3. Adjust the registry to your solutions

Edit `config/solutions.yml` so the keys, folders and workspace names match yours,
then mirror the same solutions in `azure-pipelines.yml`. Run the tests; the drift
test fails if the two disagree.

### 4. Verify locally before pushing

```bash
python3 -m unittest discover -s tests -v
```

### 5. Create the pipeline

Point Azure DevOps at `azure-pipelines.yml`. Grant it access to the three
variable groups.

The first run is a framework-only change, so detection marks nothing as changed
and every deployment stage skips. That is the expected result and a good first
signal that detection works.

### 6. Connect the Development workspaces

For each solution, in Fabric: Workspace settings, Git integration, connect to the
repository on branch `develop` with the **Git folder** set to that solution's
folder (`/fabric-workspaces/Ved`, `/fabric-workspaces/Fin`,
`/fabric-workspaces/HR`). Then commit the workspace items from Fabric.

Do this after step 5. Until a folder holds real items, the empty-source guard
refuses to deploy it.

### 7. Promote

- Commit to `develop` to validate the changed solutions against DEV.
- Merge `develop` into `release` to deploy the changed solutions to UAT.
- Merge `release` into `main` to deploy them to PROD.

## Checking it works

Make a change under one solution folder only, then look at the run:

- The `DetectChanges` job log names that solution as `CHANGED` and the others as
  `NOT CHANGED`.
- Every stage belonging to the other solutions shows as **Skipped**.
- The `Summary` stage prints a solution-by-environment table.

A commit touching only `README.md` should produce a green run with every
deployment stage skipped and the message
`No Fabric solution changes detected. Deployment skipped.`

## Running one deployment by hand

```bash
cp env.example .env
# fill in the values, then export them
python3 scripts/deploy_fabric_workspace.py
```

Keep `VALIDATE_ONLY=true` until you are sure the target is right. Validation
still authenticates, resolves the workspace and parses every item, so it catches
most mistakes without writing anything.
