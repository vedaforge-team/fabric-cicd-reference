# fabric-cicd-reference

## Project Overview

This repository is a public reference implementation for Microsoft Fabric CI/CD with Azure DevOps.
It shows one practical promotion path from source-controlled Fabric changes to repeatable deployment through DEV, UAT, and PROD.

## Why This Exists

The goal is to show a practical way to promote Microsoft Fabric items through development, validation, release, and production stages using repository-backed automation.

This is a working example, not a product demo.

## What Readers Will Build

Readers will see how to:

- deploy a Fabric workspace from source control
- pass environment-specific settings through Azure DevOps
- separate validation from deployment
- promote the same solution through multiple environments
- organize reusable example assets for future articles

## Architecture Diagram

Placeholder for the Article 01 architecture diagram.

See the detailed diagram assets in `diagrams/article-01/`.

## Quick Start

1. Read [Article 01 example package](examples/01-solution-promotion/README.md)
2. Review the [quick start guide](examples/01-solution-promotion/QUICKSTART.md)
3. Inspect the deployment script in `examples/01-solution-promotion/deploy_workspace_fabric.py`
4. Review the pipeline definition in `examples/01-solution-promotion/azure-pipelines.yml`

If you are validating the public release assets, also read:

- [Article 01 source notes](docs/articles/article-01-source-notes.md)
- [Release notes v1.0.0](docs/releases/v1.0.0.md)
- [Release checklist](RELEASE_CHECKLIST.md)

## Repository Structure

- `examples/01-solution-promotion/` - public example package for Article 01
- `release-assets/article-01/gist/` - Gist-ready source bundle
- `docs/articles/` - article drafts and source notes
- `docs/releases/` - release notes
- `diagrams/article-01/` - architecture and flow diagrams
- `images/article-01/` - screenshots and image checklist
- `pipelines/` - reusable Azure DevOps pipeline assets
- `templates/` - reusable pipeline templates
- `src/` - reusable Python modules
- `tests/` - test guidance and future test assets

## Article Series

This repository is organized around a short article series on Microsoft Fabric CI/CD.

Current public entry point:

- [Article 01 - Building Enterprise CI/CD for Microsoft Fabric using Azure DevOps](docs/articles/article-01-source-notes.md)

Supporting assets:

- example implementation package
- release notes
- diagrams
- screenshots
- Gist package

## Screenshots

Article 01 screenshots are stored under `images/article-01/`.

Approved screenshot reference:

- [Screenshot checklist](images/article-01/README.md)

## Related Projects

- Private engineering repository used for internal implementation work
- Public reference repository for Article 01
- Azure DevOps pipeline configuration for environment promotion

## Roadmap

The repository roadmap is tracked in [ROADMAP.md](ROADMAP.md).

The current public sequence covers:

1. Enterprise CI/CD for Microsoft Fabric Solution Promotion
2. Multiple Solution Promotion
3. Warehouse Deployment
4. Database Deployment
5. OneLake Shortcuts
6. Activators
7. Deployment Validation
8. Quality Gates
9. Rollback
10. Reusable Azure DevOps Templates

## Contributing

Contributions should keep the repository public-safe, reproducible, and specific to the documented Fabric CI/CD flow.

Before proposing changes:

- avoid private names, tenant data, IDs, secrets, and local paths
- keep implementation changes aligned with the working example
- update the relevant docs or release notes when behavior changes

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
>>>>>>> 775e111 (docs: rewrite public landing page)
