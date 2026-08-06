# Article 01 Source Notes

This document captures verified facts for Article 01. It is not the final LinkedIn article.

## What Was Built

- A variable-driven Fabric deployment script
- An Azure DevOps pipeline for `develop`, `release`, and `main`
- Public article assets, diagrams, and screenshots
- A release-ready Gist package

## What Was Tested

- DEV deployment
- UAT deployment
- PROD deployment
- Python syntax
- YAML syntax
- Screenshot naming and placement

## Key Engineering Decisions

- Use a service principal instead of interactive login
- Keep the deployment script separate from the pipeline
- Use branch-based promotion instead of manual copying
- Exclude Warehouse from the `fabric-cicd` item scope
- Use environment variables for all deployment inputs

## Practical Lessons

- Keep the script small and variable-driven.
- Keep branch behavior explicit in the pipeline.
- Keep screenshots named consistently and grouped by article.
- Keep release assets separate from the main example package.

## Screenshot Map

- `images/article-01/article-01-01-develop-validation.png`
- `images/article-01/article-01-02-release-deployment.png`
- `images/article-01/article-01-03-prod-deployment.png`
- `images/article-01/article-01-04-variable-groups.png`
- `images/article-01/article-01-01-dev-spn-access.png`
- `images/article-01/article-01-02-uat-spn-access.png`
- `images/article-01/article-01-03-prod-spn-access.png`

## GitHub Links to Reference Later

- `README.md`
- `examples/01-solution-promotion/README.md`
- `examples/01-solution-promotion/QUICKSTART.md`
- `examples/01-solution-promotion/TROUBLESHOOTING.md`
- `release-assets/article-01/gist/README.md`
- `docs/releases/v1.0.0.md`

## Points That Still Need Author Confirmation

- Final LinkedIn headline and opening hook
- Whether the release package should be copied into a gist as-is or lightly reformatted
- Whether the article should mention the GitHub repo name directly

