# Fabric workspace sources

One folder per Fabric solution. Each folder is the source of truth for a
solution's artifacts and is connected to that solution's **Development**
workspace through Fabric Git integration.

| Folder | Development workspace | Git folder to connect |
| ------ | --------------------- | --------------------- |
| `Ved/` | Ved-Development | `/fabric-workspaces/Ved` |
| `Fin/` | Fin-Development | `/fabric-workspaces/Fin` |
| `HR/`  | HR-Development  | `/fabric-workspaces/HR`  |

These folders are written by Fabric, not by hand. UAT and PROD workspaces are
deployment targets and are deliberately not Git-connected, so each environment
has one source of truth rather than two competing ones.

Everything outside this folder is the shared CI/CD framework: `config/`,
`scripts/`, `templates/`, `tests/` and `azure-pipelines.yml`.

Change detection uses these folder boundaries. A commit touching only
`fabric-workspaces/Ved` deploys VED and leaves FIN and HR untouched. See the
repository README for the full model.
