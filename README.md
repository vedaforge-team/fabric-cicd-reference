# fabric-cicd-reference

Public reference implementation for Microsoft Fabric CI/CD with Azure DevOps.

Two working examples: promoting a single Fabric solution through DEV, UAT, and
PROD, and promoting several independent solutions from one repository without
letting a change in one deploy the others.

These are working examples, not a product demo.

## Examples

| Example | Covers | Release |
| ------- | ------ | ------- |
| [`01-solution-promotion`](examples/01-solution-promotion/README.md) | One solution through `develop`, `release`, `main` | `v1.0.0` |
| [`02-multi-solution`](examples/02-multi-solution/README.md) | Several solutions, one pipeline, change-aware deployment | `v2.0.0` |

Start with 01 if you are setting up Fabric CI/CD for the first time. Go to 02
when a second team needs to share the repository.

## What the examples show

**Example 01** — deploying a Fabric workspace from source control, passing
environment-specific settings through Azure DevOps variable groups, separating
validation from deployment, and promoting one solution through three
environments.

**Example 02** — three solutions across nine workspaces served by one pipeline.
The additions that make that safe:

- Change detection mapping a git diff onto solution folders, so a commit deploys
  only the solutions it touched
- A single deployment engine parameterised by solution and environment, rather
  than one script per solution
- A registry holding workspace IDs by variable name, keeping GUIDs out of Git
- Deployment scoping that rejects the repository root as a source path
- An empty-source guard that aborts before any Fabric call when a solution
  folder holds no items
- Shallow-clone detection, so a missing diff baseline fails loudly instead of
  silently skipping every deployment

The organising idea in 02 is that two questions stay separate: *which solutions
changed* is answered by detection at run time, and *where they may deploy* is
answered by the branch. Both must agree before a stage runs.

## Quick start

**Single solution**

1. [Example package](examples/01-solution-promotion/README.md)
2. [Quick start guide](examples/01-solution-promotion/QUICKSTART.md)
3. `examples/01-solution-promotion/deploy_workspace_fabric.py`
4. `examples/01-solution-promotion/azure-pipelines.yml`

**Multiple solutions**

1. [Example package](examples/02-multi-solution/README.md)
2. [Quick start guide](examples/02-multi-solution/QUICKSTART.md)
3. [Troubleshooting](examples/02-multi-solution/TROUBLESHOOTING.md)
4. Run the offline test suite — no Azure or Fabric access required:

```bash
cd examples/02-multi-solution
python3 -m unittest discover -s tests -v
```

## Diagrams

Mermaid sources, rendered by GitHub:

- [`diagrams/article-01/`](diagrams/article-01/) — architecture, pipeline, and promotion flow
- [`diagrams/article-02/`](diagrams/article-02/) — architecture, repository layout,
  branch strategy, change-detection logic, pipeline execution, commit-to-deploy
  sequence, multi-workspace deployment, and the deployment lifecycle

## Repository structure

- `examples/` — one package per published article
- `diagrams/` — Mermaid diagram sources
- `images/` — screenshots per article
- `docs/articles/` — article notes
- `docs/releases/` — release notes
- `release-assets/` — Gist-ready bundles

## Article series

| # | Article | Notes |
| - | ------- | ----- |
| 01 | Building Enterprise CI/CD for Microsoft Fabric using Azure DevOps | [notes](docs/articles/article-01-notes.md) |
| 02 | One CI/CD framework for multiple Microsoft Fabric solutions | [notes](docs/articles/article-02-notes.md) |

## Releases

| Version | Notes | Scope |
| ------- | ----- | ----- |
| `v2.0.0` | [release notes](docs/releases/v2.0.0.md) | Multi-solution promotion with change-aware deployment |
| `v1.0.0` | [release notes](docs/releases/v1.0.0.md) | Single-solution promotion |

`v2.0.0` contains breaking changes for anyone upgrading from `v1.0.0`. The
release notes list the required migration steps.

## Known limitations

Stated plainly so they are not discovered late:

- No `parameter.yml`. Items referencing a workspace-specific resource by GUID
  still point at the source environment after deployment.
- No approval gates. A merge to `main` deploys PROD unattended.
- Warehouse schema deployment is deliberately excluded, because a `fabric-cicd`
  publish can reset schema.
- A push of several commits at once is evaluated from `HEAD~1`, so only the last
  commit is inspected. Promotion goes through pull requests, where the whole
  change set is visible, so this affects direct pushes to `develop` only.

## Contributing

Keep the repository public-safe, reproducible, and specific to the documented
Fabric CI/CD flow. Before proposing changes:

- avoid private names, tenant data, IDs, secrets, and local paths
- keep implementation changes aligned with the working example
- update the relevant docs or release notes when behaviour changes

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT. See [LICENSE](LICENSE).
