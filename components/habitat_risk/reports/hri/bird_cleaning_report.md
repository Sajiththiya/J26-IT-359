# Bird Observation Cleaning Report
## Work Package 2 — Complete Bird-Data Cleaning
### 1. Dataset
Input dataset:
`bird_observations_cleaning_draft.csv`
Total observations: **102,929**
Unique scientific names: **25**
Year range: **2010–2023**
---
## 2. Duplicate Review
Potential duplicate copies flagged: **18,411**
Complete dataset size: **102,929**
Deduplicated sensitivity dataset size: **84,518**
Potential duplicates were NOT automatically deleted from the primary
dataset because the supplied data do not contain a checklist/event
identifier that can establish whether identical rows represent repeated
ingestion or separate valid observations.
The complete dataset is therefore retained for the primary workflow,
while the deduplicated dataset is retained for sensitivity analysis.
---
## 3. Survey Effort Review
Missing duration records: **11,401**
Missing distance records: **37,057**
Impossible effort records: **20**
Missing effort values were NOT replaced with zero.
Missing effort means that effort information is unavailable.
Occurrences with impossible effort values are retained as occurrence
evidence but should not contribute those invalid effort measurements to
effort-dependent analyses.
---
## 4. Spatial Review
Missing coordinate records: **0**
Globally invalid coordinate records:
**0**
Broad Sri Lanka screening candidates:
**0**
The broad coordinate envelope was used only to identify records requiring
review. It is not treated as an official Sri Lanka national boundary.
Manual spatial decisions use four statuses:
- keep
- correct
- exclude
- unresolved
No coordinate correction is invented automatically.
---
## 5. Species Scope
Species included after verification: **0**
Species excluded: **0**
Species still unresolved: **25**
Taxonomy and endemic status are not guessed automatically.
Unresolved species remain explicitly flagged until verified using an
authoritative source.
---
## 6. Final Observation Status
Analysis-ready records: **102,929**
Excluded or unresolved records:
**0**
Rows with unresolved species scope:
**102,929**
If species verification is incomplete, the analysis-ready dataset should
be considered provisional until `final_species_scope.csv` is frozen.
---
## 7. Sampling Bias
Records were summarized by year, species, observation date and location.
Grid-cell/year sampling analysis is pending because a grid-cell identifier has not yet been assigned.
Highly sampled cell-years are identified using the 95th percentile of
record counts when grid data are available.
Spatial thinning is used only as a sensitivity experiment and does not
create absence information.
---
## 8. Important Ecological Interpretation
A missing bird observation means:
**the species was not recorded in the available observation data.**
It must NOT automatically be interpreted as:
**the species was absent from that location.**
This distinction is important because citizen-science observation data
are affected by uneven sampling effort and observer accessibility.
---
## 9. Reproducibility
Every original observation has a `source_row_id`.
Duplicate, effort, spatial, temporal, count and species-scope decisions
are recorded explicitly.
The workflow preserves the original values while creating derived
analysis fields and documented decisions.
