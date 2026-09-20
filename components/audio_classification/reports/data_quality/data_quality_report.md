# Dataset Quality and Original Recording Verification

Generated 2026-10-17T17:37:48.927061+00:00 (UTC).

## Scope and evidence

Reviewed all 945 metadata rows, the existing dataset audit, filenames and source path strings. Recomputed SHA-256 for original inputs; current bird hashes match the audit. Original bird/noise files and metadata retained identical contents, sizes and modification times. No audio was processed, excluded, or listened to by this automated review. No external catalog was assumed or queried.

## Near-silent recordings

20 recordings, all Sri Lanka Frogmouth, have whole-file RMS below -60 dBFS but are not digitally silent. Levels span -75.20 to -60.24 dBFS. Quiet calls can remain useful; low RMS alone does not justify removal.

| Filename | Species | RMS dBFS | Duration seconds |
|---|---|---:|---:|
| Sri_Lanka_Frogmouth_44.wav | Sri_Lanka_Frogmouth | -60.69 | 59.040 |
| Sri_Lanka_Frogmouth_45.wav | Sri_Lanka_Frogmouth | -75.20 | 113.040 |
| Sri_Lanka_Frogmouth_102.wav | Sri_Lanka_Frogmouth | -60.24 | 18.715 |
| Sri_Lanka_Frogmouth_108.wav | Sri_Lanka_Frogmouth | -61.12 | 18.456 |
| Sri_Lanka_Frogmouth_114.wav | Sri_Lanka_Frogmouth | -63.38 | 36.310 |
| Sri_Lanka_Frogmouth_137.wav | Sri_Lanka_Frogmouth | -64.95 | 3.883 |
| Sri_Lanka_Frogmouth_142.wav | Sri_Lanka_Frogmouth | -68.11 | 10.855 |
| Sri_Lanka_Frogmouth_143.wav | Sri_Lanka_Frogmouth | -60.38 | 13.339 |
| Sri_Lanka_Frogmouth_144.wav | Sri_Lanka_Frogmouth | -61.31 | 52.200 |
| Sri_Lanka_Frogmouth_151.wav | Sri_Lanka_Frogmouth | -63.80 | 41.726 |
| Sri_Lanka_Frogmouth_156.wav | Sri_Lanka_Frogmouth | -60.70 | 4.006 |
| Sri_Lanka_Frogmouth_170.wav | Sri_Lanka_Frogmouth | -63.54 | 28.108 |
| Sri_Lanka_Frogmouth_184.wav | Sri_Lanka_Frogmouth | -61.26 | 22.802 |
| Sri_Lanka_Frogmouth_190.wav | Sri_Lanka_Frogmouth | -65.14 | 15.253 |
| Sri_Lanka_Frogmouth_250.wav | Sri_Lanka_Frogmouth | -62.30 | 19.660 |
| Sri_Lanka_Frogmouth_252.wav | Sri_Lanka_Frogmouth | -62.29 | 24.789 |
| Sri_Lanka_Frogmouth_267.wav | Sri_Lanka_Frogmouth | -65.26 | 17.290 |
| Sri_Lanka_Frogmouth_268.wav | Sri_Lanka_Frogmouth | -62.94 | 5.660 |
| Sri_Lanka_Frogmouth_274.wav | Sri_Lanka_Frogmouth | -60.62 | 4.523 |
| Sri_Lanka_Frogmouth_279.wav | Sri_Lanka_Frogmouth | -61.41 | 21.008 |

## Confirmed duplicate links

11 exact duplicate groups contain 22 files. Every group has different declared recording IDs, but none has different species labels. 10 groups link a numeric ID with a local ID; the remaining group links two local IDs. Content identity is confirmed, not the correctness of either original ID. All files remain retained.

| Species | File names | Declared IDs |
|---|---|---|
| Chestnut-backed_Owlet | Chestnut-backed_Owlet_7.wav; Chestnut-backed_Owlet_53.wav | 346212; Chestnut-backed Owlet 23 |
| Green-billed_Coucal | Green-billed_Coucal_16.wav; Green-billed_Coucal_42.wav | 311174; Green-billed Coucal 18 |
| Spot-winged_Thrush | Spot-winged_Thrush_16.wav; Spot-winged_Thrush_64.wav | 190807; Spot-winged Thrush 18 |
| Sri_Lanka_Blue_Magpie | Sri_Lanka_Blue_Magpie_7.wav; Sri_Lanka_Blue_Magpie_34.wav | 629391; Sri Lanka Blue-Magpie 13 |
| Sri_Lanka_Blue_Magpie | Sri_Lanka_Blue_Magpie_8.wav; Sri_Lanka_Blue_Magpie_35.wav | 629390; Sri Lanka Blue-Magpie 14 |
| Sri_Lanka_Frogmouth | Sri_Lanka_Frogmouth_8.wav; Sri_Lanka_Frogmouth_185.wav | 1160424; Sri Lanka Frogmouth 150 |
| Sri_Lanka_Frogmouth | Sri_Lanka_Frogmouth_18.wav; Sri_Lanka_Frogmouth_109.wav | 201366; Sri Lanka Frogmouth 74 |
| Sri_Lanka_Frogmouth | Sri_Lanka_Frogmouth_19.wav; Sri_Lanka_Frogmouth_36.wav | 196561; Sri Lanka Frogmouth 1 |
| Sri_Lanka_Frogmouth | Sri_Lanka_Frogmouth_63.wav; Sri_Lanka_Frogmouth_64.wav | Sri Lanka Frogmouth 28; Sri Lanka Frogmouth 29 |
| Sri_Lanka_Junglefowl | Sri_Lanka_Junglefowl_15.wav; Sri_Lanka_Junglefowl_61.wav | 453366; Sri Lanka Junglefowl 24 |
| Sri_Lanka_Spurfowl | Sri_Lanka_Spurfowl_12.wav; Sri_Lanka_Spurfowl_57.wav | 190817; Sri Lanka Spurfowl 26 |

## Investigation of original IDs

All 648 unverified IDs are sequential species-name labels and exactly equal their historical source filename stems. They all reference audio/... paths. The other 297 numeric IDs reference dataset/... paths. Source extensions across all rows: {'.mp3': 421, '.wav': 462, '.m4a': 62}.
None of the 945 historical source files is present at its recorded path. There are no repeated declared IDs or identical source-path strings. Neither numbered filenames nor matching species names establish independent recording events. Numeric IDs lack a verified catalog namespace, source URL, recorder, location and date in this CSV.
12 local-ID files are linked by exact content to other files. The other 636 local-ID files have no confirmed counterpart from this evidence. The 648-row unverified_local_ids.csv records every case. Duplicate pairs crossing the audio/ and dataset/ collections demonstrate overlapping source collections.
Distinct file hashes cannot rule out re-encoding, gain changes, trims, overlapping excerpts or different files from the same field session. Duration similarity is not proof of identity. No similarity fingerprinting, waveform alignment, embedded-tag extraction or external provenance verification was performed; these remain possible follow-up checks.

## Species identity summary

The three file-status columns below are mutually exclusive and sum to each species file count. Confirmed means confirmed duplicate-content linkage only. Provisional means an unlinked numeric ID. Unresolved means an unlinked local ID. All original recording identities remain unverified, including those with confirmed content links. Zero confirmed independent originals means zero verified by available evidence, not zero real originals.

| Species | Files with confirmed content links | Provisional files | Unresolved files | Byte-unique groups | Numeric candidates |
|---|---:|---:|---:|---:|---:|
| Chestnut-backed_Owlet | 2 | 29 | 47 | 77 | 30 |
| Crimson-fronted_Barbet | 0 | 13 | 37 | 50 | 13 |
| Green-billed_Coucal | 2 | 23 | 39 | 63 | 24 |
| Spot-winged_Thrush | 2 | 45 | 62 | 108 | 46 |
| Sri_Lanka_Blue_Magpie | 4 | 19 | 35 | 56 | 21 |
| Sri_Lanka_Frogmouth | 8 | 32 | 244 | 280 | 35 |
| Sri_Lanka_Grey_Hornbill | 0 | 14 | 31 | 45 | 14 |
| Sri_Lanka_Junglefowl | 2 | 36 | 49 | 86 | 37 |
| Sri_Lanka_Spurfowl | 2 | 30 | 37 | 68 | 31 |
| Yellow-fronted_Barbet | 0 | 46 | 55 | 101 | 46 |

## Leakage and collection priorities

The 22 exact duplicate files would cause definite content leakage if separated between future splits. Keep each confirmed group together when splitting is eventually authorized. All 945 records have unresolved provenance and therefore possible additional identity leakage; recording_identity_review.csv lists every record and required evidence. The 934 byte-unique groups are NOT 934 confirmed independent recordings.
Crimson-fronted Barbet (13 numeric candidates) and Sri Lanka Grey Hornbill (14) are highest priority for provenance recovery or additional documented independent recordings. Relative to the earlier 20-recording screening target, conditional gaps are 7 and 6 only if every numeric candidate is independent and no local candidate can be verified. Actual shortfalls cannot yet be established for any species. The other eight species also need verification before sufficiency can be claimed. Frogmouth has the largest local-ID backlog (249) and all 20 quiet files.
The audit also found one noise recording per category. Independent training/test noise sources are not established; future evaluation would need additional independent recordings or an explicitly limited evaluation design. No noise splitting or augmentation was performed.

## Manual listening and provenance checklist

manual_listening_checklist.csv includes all 945 records: urgent duplicate/quiet cases first, other local IDs next, numeric candidates last. Every decision is pending and every recording retained.

1. Listen to the complete recording at a comfortable level; for quiet files note any playback-only gain used. Do not normalize or overwrite the source.
2. Record target-bird audibility, identification confidence, call time ranges, other species, background sound and artifacts. Silence between calls is not the same as an unusable recording.
3. Compare listed duplicate partners and other suspected relatives for matching call sequences, background events and overlapping sections. Listening similarity suggests a link but does not establish provenance.
4. Recover original URLs/files and record catalog namespace, original ID, recorder, date, location, parent recording and edit/export history. Resolve conflicting IDs without editing the original metadata; document proposed corrections separately.
5. Record reviewer, date, evidence and a proposed keep/review/exclude decision. No exclusion becomes automatic. Approve identities before any future split.

## Deliverables and limits

CSV files: near_silent_review, duplicate_identity_review, recording_links, recording_identity_review, unverified_local_ids, manual_listening_checklist, species_identity_summary, input_integrity.
Reproducible script: src/review_data_quality.py. It refuses to overwrite an existing data_quality folder. The earlier audit reports were not regenerated or changed.
No original recording or metadata was modified; no preprocessing, splitting, augmentation, training or Git operation was performed. Further work requires user approval.
