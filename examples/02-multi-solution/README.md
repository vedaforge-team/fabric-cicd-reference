# Multi-Solution Promotion

This example shows the Article 02 implementation: one Azure DevOps pipeline that
promotes several independent Fabric solutions, deploying only the ones a commit
actually changed.

Article 01 (`examples/01-solution-promotion/`) handles one solution. This example
is what that grows into when a second and third team share the repository,
without ending up with three copies of the same pipeline.

## Contents

- `azure-pipelines.yml` - the single entry point
- `config/solutions.yml` - solution registry; workspace IDs by variable name, no GUIDs
- `scripts/detect_changes.py` - decides which solutions changed
- `scripts/deploy_fabric_workspace.py` - the one deployment engine
- `scripts/solution_config.py` - registry loading and validation
- `templates/solution-stages.yml` - Validate / UAT / PROD stages for one solution
- `templates/steps-deploy-solution.yml` - the deployment steps, written once
- `tests/` - the scenario matrix and safety guards, runnable offline
- `fabric-workspaces/` - solution folders, populated by Fabric Git integration
- `env.example` - local environment template
- `QUICKSTART.md` - the shortest path to a working run
- `TROUBLESHOOTING.md` - failure modes worth knowing about in advance

## The problem it solves

Three solutions, nine workspaces, one repository. A notebook edit in one
solution must not republish another team's production workspace.

Two questions are answered separately:

- **Which solutions changed?** `scripts/detect_changes.py`, at run time, from the git diff.
- **Where may they deploy?** The branch the build is running on.

Both must agree before a stage runs. Detection never widens the branch rule, and
the branch rule never widens detection.

## Folder and workspace model

| Solution | Folder | Development workspace | UAT | PROD |
| -------- | ------ | --------------------- | --- | ---- |
| VED | `fabric-workspaces/Ved` | Ved-Development | Ved-UAT | Ved-Prod |
| FIN | `fabric-workspaces/Fin` | Fin-Development | Fin-UAT | Fin-Prod |
| HR  | `fabric-workspaces/HR`  | HR-Development  | HR-UAT  | HR-Prod |

Solution sources sit under `fabric-workspaces/` so the repository root separates
into content and framework. Everything outside that folder - `config/`,
`scripts/`, `templates/`, `tests/`, `azure-pipelines.yml` - is the shared CI/CD
implementation.

Fabric allows several workspaces to share one repository and branch provided each
uses a distinct, non-overlapping Git folder. Development workspaces are
Git-connected; UAT and PROD are deployment targets only, so each environment has
one source of truth rather than two competing ones.

Because a Fabric commit only ever writes inside its own folder, commits arrive
pre-scoped. That is what makes change detection reliable rather than heuristic.

## Branch promotion

| Branch | Result | Target |
| ------ | ------ | ------ |
| pull request | validate only | DEV |
| `develop` | validate only | DEV |
| `release` | deploy | `*-UAT` |
| `main` | deploy | `*-Prod` |

No automatic DEV to UAT to PROD chain. Promotion is a merge someone performs.

## Why every stage always exists

Azure DevOps builds its stage graph at compile time, but change detection only
answers at run time, so stages cannot be created dynamically. Every stage for
every solution is generated, and detection decides which ones execute.

Unaffected solutions therefore show as **Skipped** rather than being absent.
That is worth having: a skipped stage is visible evidence that the pipeline
considered a solution and chose not to deploy it.

## Configuration and secrets

`config/solutions.yml` holds solution keys, folders, workspace names, and the
**name** of the Azure DevOps variable holding each workspace ID. It contains no
GUIDs and no credentials. A test fails if a GUID ever appears in it.

| Value | Lives in |
| ----- | -------- |
| solution keys, folders, workspace names | `config/solutions.yml` |
| item types, exclusions, flags | `azure-pipelines.yml` variables |
| `TENANT_ID`, `CLIENT_ID` | Azure DevOps variable group |
| `CLIENT_SECRET` | Azure DevOps secret variable |
| the nine workspace GUIDs | Azure DevOps variable groups |

The template turns a solution and an environment into a variable name at compile
time, so `ved` + `UAT` becomes `$(VED_UAT_WORKSPACE_ID)`, resolved from the
stage's variable group at run time.

## Safety behaviour

**Deployments are scoped to one solution folder.** The script rejects a
`REPOSITORY_DIRECTORY` resolving to the repository root. A root-scoped run would
sweep every solution's artifacts into one workspace, and the orphan cleanup that
follows would be evaluated against the wrong item set.

**An empty solution folder aborts the run.** If the selected folder holds no
`.platform` descriptors, the deployment fails before any Fabric call. Orphan
removal treats "present in target, absent from source" as "delete", so deploying
an empty `fabric-workspaces/Fin` to a populated `Fin-UAT` would empty it. A folder created but not
yet populated from its Development workspace is a normal intermediate state, so
it has to fail safely rather than proceed.

**Full history is required.** The detection job checks out with `fetchDepth: 0`.
A shallow clone has no parent to diff against, and git reports an empty diff
rather than an error, which would look like "nothing changed" and skip every
deployment. `detect_changes.py` refuses to run in a shallow clone rather than
return that false negative.

**A framework change deploys nothing.** Editing `scripts/`, `templates/`,
`config/` or the pipeline runs validation only. Republishing unchanged artifacts
to UAT or PROD to exercise a pipeline edit would be a real workspace write, orphan
cleanup included, taken for a validation reason. Use the `solutionsOverride`
pipeline parameter when a framework change genuinely needs rolling out.

## Tests

No Azure or Fabric access, and no pytest:

```bash
python3 -m unittest discover -s tests -v
```

Covers the six scenarios the pipeline must get right (VED only, FIN only, HR
only, VED + HR, all three, documentation only), the deployment safety guards,
registry validation, and drift between `config/solutions.yml` and
`azure-pipelines.yml`.

The Fabric SDK is imported lazily by the deployment script so that the guards can
be tested on a machine with neither `fabric-cicd` nor `azure-identity` installed.

## Intended use

Copy the contents of this folder to the **root** of an Azure DevOps-backed
repository. The pipeline invokes `scripts/...` relative to the repository root,
so the layout is meant to sit at the top level rather than in a subfolder.

Then work through `QUICKSTART.md`.

## Adding another solution

1. Create the workspaces, for example `Ops-Development`, `Ops-UAT`, `Ops-Prod`.
2. Add `OPS_DEV_WORKSPACE_ID`, `OPS_UAT_WORKSPACE_ID`, `OPS_PROD_WORKSPACE_ID` to
   the three variable groups.
3. Add an entry to `config/solutions.yml`.
4. Add one `templates/solution-stages.yml` call to `azure-pipelines.yml`, and add
   its three stage names to the `Summary` stage's `dependsOn`.
5. Run the tests. The drift test fails if steps 3 and 4 disagree.
6. Connect `Ops-Development` to the repository with Git folder
   `/fabric-workspaces/Ops` and commit its items from Fabric.

Step 6 comes last on purpose. Until the folder holds real items the empty-source
guard will refuse to deploy it, which is the intended behaviour.
