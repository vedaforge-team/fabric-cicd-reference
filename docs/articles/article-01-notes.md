# Article 01

## Title

Building Enterprise CI/CD for Microsoft Fabric using Azure DevOps

## Published

https://www.linkedin.com/pulse/building-enterprise-microsoft-fabric-cicd-practical-guide-mintu-ghosh-f3dbf/

## Purpose

This article shows how one Fabric solution can move through `develop`, `release`, and `main` with a single deployment script and one Azure DevOps pipeline.

## Working Pattern

- `develop` validates the repository against DEV
- `release` deploys to UAT
- `main` deploys to PROD

## What the Reader Gets

- A service-principal driven Fabric deployment script
- A pipeline that is driven by variable groups
- A reusable pattern for one-solution promotion
- Screenshots that show the branch flow and workspace access

## Assets

- `examples/01-solution-promotion/`
- `diagrams/article-01/`
- `images/article-01/`

## Public Safety

This note avoids private planning language, local paths, customer names, tenant IDs, workspace IDs, and secrets.
