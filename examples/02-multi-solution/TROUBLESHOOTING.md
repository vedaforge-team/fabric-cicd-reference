# Troubleshooting

## Everything skips, and the run is green

The most likely cause is a shallow clone. Change detection diffs against the
parent commit, and a shallow clone has none, so git returns an empty diff rather
than an error. That reads as "nothing changed".

`detect_changes.py` checks for this and fails rather than returning the false
negative, so the run should be red instead. If it is green and everything
skipped, confirm:

- the `DetectChanges` job has `checkout: self` with `fetchDepth: 0`
- the changed paths are not all in the ignore list (`*.md`, `docs/`, `diagrams/`, `images/`)
- the change was not framework-only, which validates but deploys nothing by design

The `DetectChanges` log lists every changed file with the rule that matched it.

## A stage condition never matches

Output variables are strings. `eq(..., true)` never matches; it has to be
`eq(..., 'true')`.

The full reference is
`dependencies.DetectChanges.outputs['Detect.detect.<key>']`, and all three parts
matter: the job name `Detect`, the step name `detect`, and the solution key. A
consuming stage must also `dependsOn: DetectChanges`, or the variable cannot be
resolved at all.

## A solution has stages but never runs

Check that its key in `config/solutions.yml` matches the `solution` parameter in
`azure-pipelines.yml`. The drift test catches this:

```bash
python3 -m unittest tests.test_solution_config -v
```

## "Refusing to deploy ... orphan removal would treat every item as an orphan"

The solution folder holds no `.platform` descriptors. This is the empty-source
guard, and it is doing its job.

Connect that solution's Development workspace to the folder and commit its items
from Fabric. Only set `ALLOW_EMPTY_SOURCE=true` if emptying the target workspace
is genuinely what you want.

## "REPOSITORY_DIRECTORY resolved to the repository root"

Something set the source path to the repository root instead of a solution
folder. A root-scoped deployment publishes every solution into one workspace, and
the orphan cleanup that follows is evaluated against the wrong item set.

Set `REPOSITORY_DIRECTORY` to a single solution folder, or leave it unset and let
the script resolve `source_path` from `config/solutions.yml`.

## Items are recreated instead of updated

`fabric-cicd` matches repository items to workspace items by `displayName` and
`type`, not by folder path or `logicalId`. Moving a solution into a subfolder is
therefore transparent, but renaming an item is not: a rename looks like a delete
plus an add, and orphan removal will remove the old name from the target.

## Case-sensitivity differences between laptop and agent

Hosted agents run Linux and are case-sensitive; macOS git is case-insensitive by
default. A folder named `Ved` referenced as `ved` works locally and fails on the
agent.

`test_source_paths_exist_on_disk` compares each `source_path` against the real
directory name and catches this before it reaches CI.

## Duplicate items after reorganising folders

If artifacts are copied into a new folder without deleting the originals, the
repository holds two items with identical `displayName` and `type`.
`FabricWorkspace` scans its directory recursively and will see both.

Validate-only builds hide this, because they never publish. Confirm the old
copies are actually deleted, and check the remote branch rather than a local
clone that may be behind.

## The pipeline deploys nothing after a framework change

Working as intended. Changes to `scripts/`, `templates/`, `config/`, `tests/` and
`azure-pipelines.yml` run validation but mark no solution as changed.

To roll a framework change out deliberately, run the pipeline manually with the
`solutionsOverride` parameter set to the solutions you mean, for example
`ved,hr`.

## Only the last commit of a push is inspected

A multi-commit push is evaluated from `HEAD~1`. Promotion to `release` and `main`
happens through pull requests, where `HEAD` is a merge or squash commit and the
whole change set is visible, so this affects direct pushes to `develop` only,
which are validate-only.

Use `--base` locally, or `solutionsOverride` in the pipeline, to cover a wider
range.

## Cross-environment references break after deployment

Items referencing a workspace-specific resource by GUID still point at the source
environment. `fabric-cicd` handles this with a `parameter.yml` file, which it
looks for inside the repository directory it was given.

Because each solution deploys from its own folder, each gets its own
`fabric-workspaces/Ved/parameter.yml` and so on. There is no shared file to
coordinate.
