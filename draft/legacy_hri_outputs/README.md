# Historical HRI bird-cleaning outputs

These five CSV files were moved here from
`components/habitat_risk/data/processed/hri/` for archival organisation.
Their contents were not changed. They are historical outputs, not the
current accepted bird-cleaning release.

Use `components/habitat_risk/data/processed/hri/wp2_v1/` for the versioned
bird-cleaning release. Its exclusion table is named
`bird_observations_excluded_or_withheld.csv`.

Earlier cleaning-notebook cells still reference the original output paths
and may recreate those files when rerun. Notebook code was not changed by
this move. To restore the historical layout, move these five CSVs back to
their original directory after checking for existing files; do not overwrite
new outputs.

## Non-research files

The `non_research/` subfolder preserves original repository-relative paths
for these additional archived files:

- `components/habitat_risk/.DS_Store`
- `components/habitat_risk/data/.DS_Store`
- `components/habitat_risk/scripts/__pycache__/build_species_vulnerability.cpython-313.pyc`

These are macOS display metadata and a generated Python cache, not research
inputs. They may be regenerated automatically. Research sources, historical
audit evidence and reference notebooks remain in the component intentionally.
