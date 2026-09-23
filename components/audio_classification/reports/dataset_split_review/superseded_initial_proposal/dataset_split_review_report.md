# Dataset split preparation and leakage safety review

Generated 2026-10-17T18:19:08.716054+00:00 (UTC).

**Not safe to finalize as a verified leakage-free split.** This is a proposal only. Accepted source links remain together, but uncertain similarities and unknown provenance require review. No files were moved or excluded.

## Verification and quality

All 9,233 clips were decoded, checked for 80,000 samples / 16 kHz / mono / PCM-16 WAV, compared with stored hashes and their original source samples, and checked for exact right-padding. Metadata labels, IDs, group IDs, filenames, times and full non-overlapping source coverage were verified. All 945 parents are covered. Original, noise, prepared audio, metadata and prior reports remained unchanged.
Padding percent = declared padding samples / 80,000 × 100, verified against source boundaries and zero samples. Natural trailing silence is not counted as padding. Heavy padding is defined here as ≥50%. Digital silence means every sample is zero. Near-silence means nonzero RMS below -60 dBFS; source-content RMS excludes padding to avoid conflating padding with quiet calls. Full-clip RMS is also recorded.
Padded clips: 942; heavily padded: 447; silent: 4; near-silent nonpadding content: 213.
Per-clip measurements and inherited flags are in proposed_split_assignments.csv; species totals are in clip_quality_summary.csv. All clips, including duplicates and low-quality clips, remain in the proposal.

## Group construction and allocation

Connected components join shared original IDs, historical source paths, prior similarity group IDs, exact-content IDs, and all confirmed-exact/probable-acoustic edges. Uncertain edges are flagged but do not merge groups. No cross-species accepted component was present. Singleton groups do not prove recording independence.
Seed 42 (NumPy default_rng). Within each species, allocate integer group quotas by largest remainder for 80/10/10, then evaluate 2,000 reproducible random whole-group allocations. Select the lowest summed squared relative deviation from per-species clip and parent-recording targets. No outcome/model data is used. This heuristic aims for balance, not a mathematical optimum; no group is broken.
Rounding whole-group quotas and unequal recording lengths make exact 80/10/10 clip and parent counts generally impossible. Allocation preserves existing class imbalance; it does not equalize species by removing or duplicating clips.

| Split | Groups | Parent recordings | Clips | Clip percent |
|---|---:|---:|---:|---:|
| train | 706 | 755 | 7371 | 79.83% |
| validation | 90 | 95 | 936 | 10.14% |
| test | 87 | 95 | 926 | 10.03% |

| Species | Split | Groups | Parent recordings | Clips | Species clip percent |
|---|---|---:|---:|---:|---:|
| Chestnut-backed_Owlet | train | 59 | 62 | 564 | 79.77% |
| Chestnut-backed_Owlet | validation | 8 | 8 | 72 | 10.18% |
| Chestnut-backed_Owlet | test | 7 | 8 | 71 | 10.04% |
| Crimson-fronted_Barbet | train | 36 | 40 | 269 | 80.30% |
| Crimson-fronted_Barbet | validation | 5 | 5 | 32 | 9.55% |
| Crimson-fronted_Barbet | test | 4 | 5 | 34 | 10.15% |
| Green-billed_Coucal | train | 45 | 51 | 673 | 79.83% |
| Green-billed_Coucal | validation | 6 | 6 | 86 | 10.20% |
| Green-billed_Coucal | test | 6 | 7 | 84 | 9.96% |
| Spot-winged_Thrush | train | 82 | 87 | 1337 | 79.54% |
| Spot-winged_Thrush | validation | 10 | 11 | 177 | 10.53% |
| Spot-winged_Thrush | test | 10 | 11 | 167 | 9.93% |
| Sri_Lanka_Blue_Magpie | train | 45 | 46 | 391 | 80.45% |
| Sri_Lanka_Blue_Magpie | validation | 6 | 6 | 48 | 9.88% |
| Sri_Lanka_Blue_Magpie | test | 5 | 6 | 47 | 9.67% |
| Sri_Lanka_Frogmouth | train | 218 | 228 | 1769 | 79.94% |
| Sri_Lanka_Frogmouth | validation | 27 | 28 | 219 | 9.90% |
| Sri_Lanka_Frogmouth | test | 27 | 28 | 225 | 10.17% |
| Sri_Lanka_Grey_Hornbill | train | 31 | 36 | 212 | 80.00% |
| Sri_Lanka_Grey_Hornbill | validation | 4 | 5 | 26 | 9.81% |
| Sri_Lanka_Grey_Hornbill | test | 4 | 4 | 27 | 10.19% |
| Sri_Lanka_Junglefowl | train | 65 | 69 | 837 | 79.49% |
| Sri_Lanka_Junglefowl | validation | 8 | 9 | 110 | 10.45% |
| Sri_Lanka_Junglefowl | test | 8 | 9 | 106 | 10.07% |
| Sri_Lanka_Spurfowl | train | 48 | 55 | 652 | 79.80% |
| Sri_Lanka_Spurfowl | validation | 6 | 7 | 82 | 10.04% |
| Sri_Lanka_Spurfowl | test | 6 | 7 | 83 | 10.16% |
| Yellow-fronted_Barbet | train | 77 | 81 | 667 | 80.07% |
| Yellow-fronted_Barbet | validation | 10 | 10 | 84 | 10.08% |
| Yellow-fronted_Barbet | test | 10 | 10 | 82 | 9.84% |

## Leakage findings and required review

Hard constraint failures: 0. All 11 exact duplicate pairs and 51 probable acoustic pairs stay together. All parent recordings, prior similarity components, exact-content groups and declared IDs stay in one proposed split.
Uncertain similarity pairs crossing splits: 15 of 71. All 44 cross-species uncertain candidates remain unresolved regardless of assignment. Unknown source provenance applies to all 945 recordings, so acoustic separation cannot certify independent field sessions.
Additional identical decoded-clip cross-split risk rows: 26. These are flagged separately; identical silent waveforms do not imply common source provenance.
split_leakage_audit.csv lists each uncertain pair with endpoints, proposed splits, correlation and offset; RISK rows identify cross-split cases. Review them before approval. Recover source URLs/recording events for unresolved parents. If an uncertain link is accepted, regroup and generate a new proposal before finalizing. Review heavy padding and silence for evaluation suitability without automatically excluding anything.

| Uncertain pair A | Pair B | Split A | Split B |
|---|---|---|---|
| birds_audio/Spot-winged_Thrush/Spot-winged_Thrush_48.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | train | test |
| birds_audio/Sri_Lanka_Spurfowl/Sri_Lanka_Spurfowl_7.wav | birds_audio/Sri_Lanka_Spurfowl/Sri_Lanka_Spurfowl_38.wav | train | validation |
| birds_audio/Sri_Lanka_Spurfowl/Sri_Lanka_Spurfowl_34.wav | birds_audio/Sri_Lanka_Spurfowl/Sri_Lanka_Spurfowl_35.wav | train | validation |
| birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_161.wav | birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_169.wav | train | test |
| birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_162.wav | birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_169.wav | train | test |
| birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_167.wav | birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_169.wav | train | test |
| birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_168.wav | birds_audio/Sri_Lanka_Frogmouth/Sri_Lanka_Frogmouth_169.wav | train | test |
| birds_audio/Sri_Lanka_Junglefowl/Sri_Lanka_Junglefowl_18.wav | birds_audio/Sri_Lanka_Junglefowl/Sri_Lanka_Junglefowl_19.wav | validation | train |
| birds_audio/Spot-winged_Thrush/Spot-winged_Thrush_17.wav | birds_audio/Spot-winged_Thrush/Spot-winged_Thrush_55.wav | train | test |
| birds_audio/Sri_Lanka_Junglefowl/Sri_Lanka_Junglefowl_39.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | train | test |
| birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_51.wav | test | train |
| birds_audio/Sri_Lanka_Junglefowl/Sri_Lanka_Junglefowl_50.wav | birds_audio/Sri_Lanka_Junglefowl/Sri_Lanka_Junglefowl_51.wav | validation | train |
| birds_audio/Chestnut-backed_Owlet/Chestnut-backed_Owlet_32.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | train | test |
| birds_audio/Green-billed_Coucal/Green-billed_Coucal_27.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | train | test |
| birds_audio/Chestnut-backed_Owlet/Chestnut-backed_Owlet_33.wav | birds_audio/Yellow-fronted_Barbet/Yellow-fronted_Barbet_50.wav | train | test |

## Reproduce and next step

`python components/audio_classification/src/review_dataset_split.py`
Refuses to overwrite the review directory. No final train/validation/test folders, augmentation, training or Git operations were performed. Wait for approval and resolution of flagged risks before finalizing.
