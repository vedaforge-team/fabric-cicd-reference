# Article 02 Diagrams

Mermaid sources for the multi-solution Fabric CI/CD article.

| File | Shows |
| ---- | ----- |
| `01-high-level-architecture.mmd` | Three solutions, one framework, nine workspaces |
| `02-repository-layout.mmd` | Root split into content and framework |
| `03-branch-strategy.mmd` | Branch decides which environment may be written |
| `04-change-detection-logic.mmd` | Baseline selection and path classification |
| `05-pipeline-execution.mmd` | Compile-time stage graph, run-time conditions |
| `06-commit-to-deploy-sequence.mmd` | Fabric commit through to a UAT deployment |
| `07-multi-workspace-deployment.mmd` | Two solutions deploying, one skipped |
| `08-deployment-lifecycle.mmd` | Guard sequence inside the deployment engine |

## A note on terminology

`04-change-detection-logic.mmd` is often described as "path filters", but these
are **not** Azure DevOps trigger path filters. The pipeline trigger has no
`paths:` block. Classification runs at run time in Python because a trigger
filter can only decide whether the whole pipeline runs; it cannot set the
per-solution variables that later stages condition on.
