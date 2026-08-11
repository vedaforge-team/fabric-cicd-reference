# Article 02

## Title

One CI/CD Framework for Multiple Microsoft Fabric Solutions

## Purpose

This article shows how a single-solution Fabric pipeline grows into one that
serves several independent solutions, without duplicating the pipeline per
solution and without letting one team's change redeploy another team's
workspaces.

## Working Pattern

- Three solutions share one repository, one folder each
- Each Development workspace is Git-connected to its own folder
- One pipeline detects which solutions a commit changed
- Only the affected solutions deploy; the rest are reported as skipped
- Branch promotion is unchanged: `develop` validates, `release` deploys UAT,
  `main` deploys PROD

## Core Idea

Two questions are answered separately and then combined:

- Which solutions changed? Determined at run time from the git diff.
- Where may they deploy? Determined by the branch.

Both must agree before a stage runs. Detection never widens the branch rule, and
the branch rule never widens detection.

## What the Reader Gets

- A change detector that maps a git diff onto solution folders
- A configuration model that keeps workspace IDs out of source control
- One deployment engine parameterised by solution and environment
- Reusable Azure DevOps stage and step templates
- Safety guards for empty source folders and root-scoped deployments
- An offline test suite covering the scenario matrix

## Engineering Notes Worth Keeping

- Azure DevOps builds its stage graph at compile time while detection answers at
  run time, so every stage is generated and conditioned rather than created
  dynamically. Skipped stages become useful evidence.
- A shallow clone produces an empty diff rather than an error, which would skip
  every deployment while the run stayed green. Detection fails loudly instead.
- Orphan removal treats "absent from source" as "delete from target", so an
  empty solution folder must abort before any Fabric call.
- A shared framework change runs validation but deploys nothing. Republishing
  unchanged artifacts to prove a pipeline edit works is still a production write.

## Assets

- `examples/02-multi-solution/`
- `diagrams/article-02/`
- `images/article-02/`

## Public Safety

This note avoids private planning language, local paths, customer names, tenant
IDs, workspace IDs, and secrets.
