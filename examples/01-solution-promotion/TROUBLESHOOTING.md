# Troubleshooting

## Package Install Fails

If `fabric-cicd` cannot be installed, check that the pinned version exists on PyPI and matches the version in the pipeline.

## Missing Environment Variables

If the script exits early, verify the Azure DevOps variable group includes the expected tenant, client, secret, workspace, and environment values.

## No Items Deploy

If the run succeeds but nothing changes, confirm the repository path is correct and the item folders are under the directory scanned by the script.

## Wrong Branch Behavior

If validation or deployment happens on the wrong branch, check the trigger and stage conditions in `azure-pipelines.yml`.

