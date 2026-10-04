# Component 02 Colab training package

This package contains actual WAVs, including clean training audio. Resolve every nonempty audio_path in the CSV files relative to this directory. Do not resolve paths relative to the CSV filename or current notebook directory.
train.csv: 29,402 examples (7,380 clean + 22,022 noisy). val.csv: 925 clean clips. test.csv: 924 clean clips. All are 16 kHz mono PCM-16, five seconds.
training_selection.csv records all 29,524 candidate training examples, including 122 exclusions (4 silent clean and 118 noisy SNR warnings). Excluded rows intentionally have an empty audio_path; filter included=True before loading. Their filename, species, variant, parent IDs and hash preserve traceability. No excluded audio is packaged.
Use label_mapping.json for the same integer labels in Wav2Vec2 and AST. Labels are the sorted finalized species names. Use the feature extractor appropriate to the selected checkpoint; this package does not train or install models.
The authoritative split is preserved. Never randomly split CSV rows. No final recording group crosses train/val/test. Low-energy, heavy-padding, audibility-review and provenance flags remain; inclusion is not a claim that target-bird audibility or field-recording independence is verified.
The historical quality_review.md is copied verbatim for evidence and contains original-project paths and pre-selection recommendations. Its statements about unmodified manifests refer to the original review; this package applies the subsequently approved selection policy. Use the package CSVs to load audio.
Only clean validation/test audio is provided. Six single-source noise categories do not establish independent-noise evaluation. Augmented examples are not independent original recordings.

Preflight estimated folder+ZIP requirement including reserve: 9.816 GiB; available: 72.316 GiB.

| Species | Train | Val | Test |
|---|---:|---:|---:|
| Chestnut-backed_Owlet | 2270 | 62 | 77 |
| Crimson-fronted_Barbet | 1019 | 42 | 38 |
| Green-billed_Coucal | 2697 | 84 | 82 |
| Spot-winged_Thrush | 5401 | 154 | 176 |
| Sri_Lanka_Blue_Magpie | 1508 | 55 | 54 |
| Sri_Lanka_Frogmouth | 7004 | 221 | 217 |
| Sri_Lanka_Grey_Hornbill | 840 | 28 | 26 |
| Sri_Lanka_Junglefowl | 3364 | 116 | 96 |
| Sri_Lanka_Spurfowl | 2619 | 81 | 79 |
| Yellow-fronted_Barbet | 2680 | 82 | 79 |
