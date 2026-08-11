# Changelog

## v2.0.0

- Added multi-solution promotion: one Azure DevOps pipeline serving several Fabric solutions.
- Added change detection that maps a git diff onto solution folders, so a commit deploys only the solutions it touched.
- Added a central solution registry holding workspace IDs by variable name rather than by value.
- Generalised the deployment script to take a solution and an environment, replacing per-solution copies.
- Added reusable Azure DevOps stage and step templates, instantiated once per solution.
- Added deployment scoping: the repository root is rejected as a source path.
- Added an empty-source guard that aborts before any Fabric call when a solution folder holds no items.
- Added shallow-clone detection so a missing diff baseline fails loudly instead of silently skipping deployments.
- Added a manual `solutionsOverride` pipeline parameter for deliberate framework rollout.
- Added an offline test suite requiring neither Azure, Fabric, nor pytest.
- Added Article 02 diagrams, screenshots, and reference example.
- **Breaking:** solution artifacts move under `fabric-workspaces/<Solution>/`, the deployment script moves to `scripts/`, `REPOSITORY_DIRECTORY` no longer defaults to the repository root, `SOLUTION_KEY` and `config/solutions.yml` are now required, workspace ID variables are solution-qualified, and change detection requires `fetchDepth: 0`. See `docs/releases/v2.0.0.md`.

## v1.0.0

- First public release of the Microsoft Fabric solution promotion reference implementation.
- Added Article 01 public reference materials for Microsoft Fabric solution promotion.
- Added a variable-driven deployment script for Azure DevOps.
- Added Azure DevOps pipeline and supporting documentation for Article 01.
- Added the Article 01 Gist package and release notes.
- Added verified source notes for the public article workflow.
