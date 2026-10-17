# Work Package 3 — Literature-review workflow

The authoritative working file is [`literature_review_matrix.xlsx`](../../literature_review_matrix.xlsx). It contains five sheets: instructions, the source matrix, indicator evidence, decision links and topic coverage. The initial release contains 31 selected sources. It is a critical evidence register, not a claim that every paper has been reproduced or that literature alone validates an index.

## How to complete and maintain it

1. Read the title and abstract to screen relevance, then read the methods, results and limitations in the full paper before relying on a claim. Record what the study actually measured, its spatial/temporal support, its validation and its limitations. Do not copy an abstract into every column.
2. Use the exact DOI or stable official URL. Verify citation, year and study area from the publisher or authoritative repository. Store quotes separately with page numbers; the matrix should normally paraphrase.
3. Prefer Sri Lankan bird evidence for ecological relevance. Use global studies for measurement methods, validation and general mechanisms, while stating the limits of transferring their thresholds or weights.
4. For each proposed indicator, complete all six design fields: relevance, risk direction, temporal meaning, transformation, weighting and limitations. If any field is unsupported, keep the indicator as a candidate or context variable.
5. Record conflicting findings and scope differences. Evidence that canopy matters locally does not prove a universal canopy threshold; evidence that elevation structures communities does not make elevation a degradation pressure.
6. Link each adopted decision to at least one direct ecological source and, where needed, a measurement/method source. Revisit the matrix whenever an indicator, outcome, weight or validation scheme changes.

## Current evidence conclusion

Forest condition and recent loss are supported core candidates. Fragmentation/connectivity is supported but must be derived and scale-tested. Human pressure and vegetation anomaly are supported conceptually but require accepted, temporally aligned data. Weather and elevation remain context or species-specific modifiers because their direction is nonlinear and species dependent. Sampling coverage is an uncertainty layer, not environmental risk. Species vulnerability remains separate and cannot be scored until the trait evidence is complete.

No final HRI weights or classes are approved. Use an explicit baseline plus prespecified alternative weights, thresholds, transformations and resolutions. Report rank correlations, class transitions, selected-area overlap and coverage changes. Validate a future degradation model with random, spatial and forward-temporal splits, but evaluate the HRI and conservation priority against separate ecological evidence.

## Adding a source

Add a row only when the source supplies a decision-relevant ecological result, a validated measurement method, or a necessary validation/decision framework. Assign it to a topic, complete every matrix field, and update the indicator or decision sheet if the conclusion changes. Keep weaker contextual sources clearly labelled rather than increasing the source count without improving evidence.

Rebuild the workbook with `python3 scripts/build_literature_review_matrix.py`. The script makes the contents reviewable and reproducible; edit the script's source and indicator registers rather than manually creating an undocumented workbook fork.
