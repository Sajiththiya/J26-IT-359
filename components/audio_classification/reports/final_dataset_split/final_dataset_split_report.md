# Final dataset splitting and similarity risk resolution

Generated 2026-10-18T01:45:36.277554+00:00 (UTC).

**Automated grouping and copy checks passed. This is not proof of leakage-free independent field recordings.** Species labels and original IDs remain unchanged; no human identity verification is claimed.

## Evidence and grouping decisions

Read prior prepared metadata, proposed assignments, leakage audit and all top-level similarity/data-quality reports. All 21 previously crossing uncertain pairs are identified in recording_group_decisions.csv (was_cross_split_uncertain=True), including seven cross-species pairs. Their prior waveform correlations, fingerprint votes, offsets and tested A intervals are preserved, with corresponding B intervals computed from the offset. These existing measurements were reviewed; no new acoustic identity claim or human listening is made.
Keep the 11 exact-content pairs and 51 probable acoustic pairs at their original evidence levels. Coallocate ALL 71 uncertain pairs precautionarily, not just the previous 21 crossings, so the rebuilt split cannot introduce crossings among previously within-split candidates. The 44 cross-species uncertain candidates are all listed in cross_species_review.csv as possible label conflicts; none is relabeled or classified as a confirmed duplicate.
Prior review groups (including additional exact decoded non-silent clip links) and declared recording IDs remain indivisible. Transitive precautionary components may contain several species: files keep their own species folders and labels. An entire component shares one split. Uncertain similarities can reflect common calls/backgrounds, so conservative grouping sacrifices allocation flexibility without resolving identity.
Final components: 846; multi-species components: 3. Evidence decisions are pair-level; final_split_assignments.csv carries every parent’s final component.

## Allocation method

Seed 42; NumPy default_rng. Thirty deterministic randomized greedy allocations followed by up to five whole-group local-move passes. Joint objective is squared relative deviation from 80/10/10 per-species clip counts, per-species parent counts, and global group counts (group term weight 2). Select the lowest objective. This supports multi-species groups and does not use model outcomes. Unequal group sizes and cross-species components prevent exact proportions; no clip or parent is removed to improve balance.
Group counts per species count components represented in that species and therefore cannot be summed across species for multi-species groups. ALL_SPECIES rows count unique groups.

| Species | Split | Parent recordings | Groups represented | Clips | Clip percent |
|---|---|---:|---:|---:|---:|
| Chestnut-backed_Owlet | train | 62 | 58 | 568 | 80.34% |
| Chestnut-backed_Owlet | val | 8 | 8 | 62 | 8.77% |
| Chestnut-backed_Owlet | test | 8 | 7 | 77 | 10.89% |
| Crimson-fronted_Barbet | train | 40 | 36 | 255 | 76.12% |
| Crimson-fronted_Barbet | val | 5 | 5 | 42 | 12.54% |
| Crimson-fronted_Barbet | test | 5 | 4 | 38 | 11.34% |
| Green-billed_Coucal | train | 52 | 44 | 677 | 80.31% |
| Green-billed_Coucal | val | 6 | 4 | 84 | 9.96% |
| Green-billed_Coucal | test | 6 | 6 | 82 | 9.73% |
| Spot-winged_Thrush | train | 87 | 80 | 1351 | 80.37% |
| Spot-winged_Thrush | val | 11 | 11 | 154 | 9.16% |
| Spot-winged_Thrush | test | 11 | 8 | 176 | 10.47% |
| Sri_Lanka_Blue_Magpie | train | 46 | 43 | 377 | 77.57% |
| Sri_Lanka_Blue_Magpie | val | 6 | 6 | 55 | 11.32% |
| Sri_Lanka_Blue_Magpie | test | 6 | 6 | 54 | 11.11% |
| Sri_Lanka_Frogmouth | train | 227 | 209 | 1775 | 80.21% |
| Sri_Lanka_Frogmouth | val | 28 | 26 | 221 | 9.99% |
| Sri_Lanka_Frogmouth | test | 29 | 26 | 217 | 9.81% |
| Sri_Lanka_Grey_Hornbill | train | 36 | 31 | 211 | 79.62% |
| Sri_Lanka_Grey_Hornbill | val | 4 | 3 | 28 | 10.57% |
| Sri_Lanka_Grey_Hornbill | test | 5 | 4 | 26 | 9.81% |
| Sri_Lanka_Junglefowl | train | 69 | 67 | 841 | 79.87% |
| Sri_Lanka_Junglefowl | val | 9 | 8 | 116 | 11.02% |
| Sri_Lanka_Junglefowl | test | 9 | 5 | 96 | 9.12% |
| Sri_Lanka_Spurfowl | train | 55 | 45 | 657 | 80.42% |
| Sri_Lanka_Spurfowl | val | 7 | 6 | 81 | 9.91% |
| Sri_Lanka_Spurfowl | test | 7 | 6 | 79 | 9.67% |
| Yellow-fronted_Barbet | train | 81 | 76 | 672 | 80.67% |
| Yellow-fronted_Barbet | val | 10 | 9 | 82 | 9.84% |
| Yellow-fronted_Barbet | test | 10 | 9 | 79 | 9.48% |
| ALL_SPECIES | train | 755 | 680 | 7384 | 79.97% |
| ALL_SPECIES | val | 94 | 85 | 925 | 10.02% |
| ALL_SPECIES | test | 96 | 81 | 924 | 10.01% |

## Validation and retained limitations

All 945 original parents and 9,233 clips retained. Every parent, prior group, exact-content group, probable pair and precautionary pair occurs in one split. Each clip was decoded before allocation, checked against its parent and padding, and its copied bytes verified by SHA-256. All copies were staged and validated before publishing birds_audio_split/. Original/prepared files and prior metadata/reports remained unchanged.
No known exact/probable/precautionary pair crosses boundaries. Unknown source provenance remains for all originals; unobserved overlap or common field sessions can still cause leakage. Conservative grouping resolves allocation risks, not source identity. All four silent clips, near-silent and heavily padded clips and duplicate material remain. Padding and quality flags are carried forward. Silent content is not evidence of common origin.
Copies are organized under birds_audio_split/train, val and test with the same ten species names and clip filenames. No augmentation, relabeling, training or Git operations occurred.

## Reproduce

`python components/audio_classification/src/finalize_dataset_split.py`
Requires absent output, report and staging directories; refuses overwrites. Any preflight failure prevents copying; copy/check failure prevents publication of a final folder. Wait for user approval before noise augmentation.
