# Species traits: evidence and limitations

Reviewed 1 October 2026. This is a source-supported working table, not an expert-approved vulnerability index. No scores or weights have been assigned.

## What was populated

- All 25 input scientific names were checked against the [Avibase Sri Lanka checklist](https://avibase.bsc-eoc.org/checklist.jsp?lang=EN&region=LK), which displays Clements 2025 nomenclature. Twenty-four are marked endemic there. Names and common names from the observation dataset remain unchanged for joining.
- Sri Lanka Frogmouth is non-endemic to Sri Lanka. Its range also includes India, supported by the [Journal of Threatened Taxa distribution review](https://www.threatenedtaxa.org/index.php/JoTT/article/view/2775). It remains in the data; any restriction to endemic birds requires an explicit scope decision.
- Global categories for 24 taxa come from the **2025 category column of HBW/BirdLife checklist v10**, downloaded from the [official taxonomy page](https://datazone.birdlife.org/about-our-science/taxonomy). This is a reproducible 2025 snapshot, not a claim that every species received a 2025 assessment or that each entry was checked against the latest 2026 assessment. Totals: 14 LC, 3 NT, 6 VU and 1 EN; one unresolved taxon.
- For Argya cinereifrons, the populated [BirdLife factsheet](https://datazone.birdlife.org/species/factsheet/ashy-fronted-babbler-argya-cinereifrons) supports High forest dependency, elevation 0–1200 m, and assessment year 2020. These describe source-reported ecology; they do not establish numerical risk weights or universal habitat thresholds.

## Taxonomy differences

`accepted_scientific_name` refers to the explicitly recorded observation-taxonomy standard, not a universally preferred name. `assessment_scientific_name` records the name matched in BirdLife.

| Input name | Assessment treatment | Handling |
| --- | --- | --- |
| Pachyglossa vincens | Dicaeum vincens | Genus crosswalk supported by [Avibase's taxonomy history](https://avibase.bsc-eoc.org/species.jsp?avibaseid=6D7110408CCB6BAF&lang=EN) |
| Psittacula calthrapae | Nicopsitta calthrapae | Input name explicitly appears in the checklist synonym column |
| Treron pompadora | Current species SISRecID 22725560 | Older same-name NR concept excluded from matching |
| Zoothera imbricata | Not independently recognized by BirdLife v10; imbricata appears under Zoothera aurea | Global species category left blank; no transfer from the broader species |

The Sri Lanka Thrush discrepancy is also documented in [Avibase's taxonomic treatments](https://avibase.bsc-eoc.org/species.jsp?avibaseid=BEEAC3EE4D10AB3D&lang=EN). `NR` is retained only in `birdlife_checklist_code`, never as an IUCN threat category and never converted to LC, NE, DD or zero vulnerability.

## Field meanings

| Field | Interpretation |
| --- | --- |
| `scientific_name` | Original immutable join key |
| `taxonomy_standard` | Named authority/version for observation-name acceptance |
| `endemic_status` | `yes` or `no` for Sri Lanka under the stated observation taxonomy |
| `iucn_category` | Global category at the documented snapshot; blank means unresolved |
| `iucn_snapshot_year` | Checklist category snapshot year, not assessment year |
| `iucn_assessment_date` | Exact assessment date, currently blank for all taxa |
| `iucn_assessment_year` | Assessment year when directly supported; currently only Argya |
| `iucn_assessment_date_precision` | `year` or `unknown`; never infer a month/day |
| `iucn_assessment_date_source` | Source of an assessment year/date, separately from category source |
| `birdlife_checklist_row` | Excel row for checking the match in the archived workbook |
| `forest_dependence` | Source's categorical dependence level, not an invented numerical score |
| `elevation_min_m`, `elevation_max_m` | Source-reported species limits; not fitted from observation elevations |
| `verification_status` | `partially_verified` for all rows: additional fields and expert review remain |
| `reviewed_by` | Automated source review is explicitly identified; no human/expert review is claimed |

National categories were not populated or substituted for global categories. Missing trait values are not biological zeros. All inclusion decisions remain pending; no records were dropped.

## Supporting artifacts

- `species_trait_evidence.csv`: field-level links, locators and access date for populated conservation/ecological fields.
- `../../reports/audits/species_checklist_matches.csv`: original-name/assessment-name crosswalk with workbook rows and IDs.
- `../raw/species_sources/HBW_BirdLife_checklist_v10.xlsx`: original provider workbook, unchanged.
- `../raw/species_sources/checklist_manifest.json`: direct download URL, provider/version, checksum and retrieval timestamp.
- `../../reports/audits/species_traits_before_verification.csv`: the original template preserved before editing.

Source searches encountered empty dynamic BirdLife factsheet fields and a direct Avibase download restriction. Accessible web-rendered checklist evidence and the official downloadable workbook were used instead. Missing fields were not inferred from page placeholders or secondary claims.

## Before priority scoring

Recover exact assessment dates and verify the chosen release for the final analysis; obtain forest-dependence and elevation evidence for the remaining taxa; resolve the thrush taxon concept and endemic-only scope; then justify aggregation and weights with sensitivity analysis. High forest dependency is not automatically equivalent to forest-interior specialization.

This table is a present-day evidence review. Do not insert its current categories into historical predictor sets as if they were known at earlier dates. Retrospective sensitivity analyses and operational forecasting need different, explicitly documented time rules. Historical versions must be selected by the prediction cutoff where traits are predictors.
