# Audio preprocessing report

Generated 2026-10-17T18:06:59.246112+00:00 (UTC).

Original recordings: 945. Verified clips: 9233. Errors: 0. Original bird/noise files and metadata unchanged: True.

## Policy and verification

All sources must decode correctly and be 16 kHz mono PCM-16 WAV. No resampling, normalization or other signal transformation was needed. Non-overlapping source intervals are copied exactly; short sources and incomplete final tails are right-padded with zeros to 80,000 samples. No valid source samples are dropped. Short/tail clips may contain little audio: source content duration and padding are explicit metadata fields, not evidence of a complete five-second call.
start_time_seconds and end_time_seconds refer to actual source audio (exclusive end); duration_seconds is the saved five-second duration including padding. Every generated WAV is reopened and compared sample-for-sample to its parent interval and zeros, and verified for sample rate, channels, frame count and encoding. Parent metadata/folder labels are checked; bird identity itself remains inherited, not verified by listening.
Low-volume and silent intervals are retained and flagged. All unresolved provenance is carried forward. Exact content group IDs and possible similarity component IDs are preserved. Uncertain cross-species candidates are separately flagged from accepted cross-species conflicts. Possible groups are not proof of independence. Exact duplicate sources remain separate outputs with shared group evidence.
Output metadata: birds_audio_prepared/metadata.csv. Source integrity and short recordings: source_verification.csv. Error table has headers only when no errors occur. No train/validation/test split, augmentation, pitch/speed changes or training was performed. No original recording or metadata was modified.

| Species | Sources | Clips | Padded clips | Short sources | Errors |
|---|---:|---:|---:|---:|---:|
| Chestnut-backed_Owlet | 78 | 707 | 78 | 0 | 0 |
| Crimson-fronted_Barbet | 50 | 335 | 50 | 2 | 0 |
| Green-billed_Coucal | 64 | 843 | 64 | 8 | 0 |
| Spot-winged_Thrush | 109 | 1681 | 108 | 3 | 0 |
| Sri_Lanka_Blue_Magpie | 58 | 486 | 56 | 2 | 0 |
| Sri_Lanka_Frogmouth | 284 | 2213 | 284 | 40 | 0 |
| Sri_Lanka_Grey_Hornbill | 45 | 265 | 45 | 2 | 0 |
| Sri_Lanka_Junglefowl | 87 | 1053 | 87 | 8 | 0 |
| Sri_Lanka_Spurfowl | 69 | 817 | 69 | 0 | 0 |
| Yellow-fronted_Barbet | 101 | 833 | 101 | 4 | 0 |

## Reproduction

`python components/audio_classification/src/prepare_audio.py --prepare`
Refuses existing prepared outputs or report directories. Running without --prepare does not process audio. Further splitting requires user approval.
