# Roadmap

Phases are delivered as articles, each with a working example in `examples/`.

| Phase | Scope | Status |
| ----- | ----- | ------ |
| 1 | Enterprise CI/CD for Microsoft Fabric solution promotion | Released in `v1.0.0` |
| 2 | Multiple solution promotion | Released in `v2.0.0` |
| 3 | Warehouse deployment | Planned |
| 4 | Database deployment | Planned |
| 5 | OneLake shortcuts | Planned |
| 6 | Activators | Planned |
| 7 | Deployment validation | Planned |
| 8 | Quality gates | Planned |
| 9 | Rollback | Planned |
| 10 | Reusable Azure DevOps templates | Foundation delivered in `v2.0.0`; a standalone template package is still planned |

## Phase 1 — Enterprise CI/CD for Microsoft Fabric solution promotion

One Fabric solution promoted through `develop`, `release`, and `main` using a
service principal and environment-specific variable groups.

Delivered: `examples/01-solution-promotion/`

## Phase 2 — Multiple solution promotion

Several independent Fabric solutions sharing one repository and one pipeline,
with change detection ensuring a commit deploys only the solutions it touched.

Delivered: `examples/02-multi-solution/`

Carried forward as known limitations: no `parameter.yml` for cross-environment
value replacement, and no approval gates on UAT or PROD.

## Phase 3 — Warehouse deployment

Warehouse schema deployment is deliberately excluded from the current item types
because a `fabric-cicd` publish can reset schema. This phase covers handling it
separately and safely.

## Phase 4 onward

Database deployment, OneLake shortcuts, activators, deployment validation,
quality gates, rollback, and a reusable template package. Scope for each is set
when the preceding phase is published.
