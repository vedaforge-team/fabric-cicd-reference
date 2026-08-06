# Quickstart

## Goal

Run a single Fabric solution through validation, UAT, and PROD using Azure DevOps variable groups and a service principal.

## Prerequisites

- Azure DevOps repository connected to your Fabric solution
- Variable groups for DEV, UAT, and PROD
- A Fabric workspace for each environment
- A service principal with access to each workspace
- Python installed for local validation

## Steps

1. Create the variable groups expected by the pipeline.
2. Put `deploy_workspace_fabric.py` at the repository root.
3. Put `azure-pipelines.yml` at the repository root.
4. Run the pipeline from `develop` for validation.
5. Merge `develop` to `release` to deploy UAT.
6. Merge `release` to `main` to deploy PROD.

## Result

The pipeline validates on `develop`, deploys to UAT from `release`, and deploys to PROD from `main`.

