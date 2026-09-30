# Noise-robust training dataset preparation

Generated 2026-10-18T02:09:20.181441+00:00 (UTC).

Authoritative membership: train 7,384; val 925; test 924. Clean training references: 7,384. Generated noisy WAVs: 22140. No-signal clips skipped for augmentation: 4; their clean examples remain. Generation failures: 0.
Dataset storage including reference tables: 3547651492 bytes (3.304 GiB). Preflight free space 78.02 GiB; maximum noisy audio estimate 3.30 GiB plus 0.25 GiB reserve.

## Quality and eligibility

Training digital silence: 4; near-silence below -60 dBFS on non-padded content: 193; padding >=50%: 365.
Fully silent/no-measurable-signal clips are never augmented. Quiet and heavily padded clips remain measurable-signal candidates and receive noisy versions with review flags; recommended eligibility is review rather than automatic exclusion. Peaks at most two PCM LSB are separately flagged as unusually low. All target-bird audibility requires human review: energy detection does not establish bird presence. No recording or clip was removed.

## Mixing and reproducibility

Seed 42, NumPy default_rng; random category and integer sample offset selected in authoritative training row order for light/medium/heavy levels. Category and offset selection is serial and deterministic; parallel writes do not affect random choices. Noise decoded and converted to 16 kHz mono in memory only; multiplexed Rain Ogg uses existing Vorbis pages. Noise sample offsets refer to the decoded/resampled stream, seconds to its timeline.
RMS-based levels: 20/10/0 dB. Signal and noise RMS use only the actual source-content samples, excluding zero padding. Noise is added only to this same region; padding remains zero. Noise gain = signal RMS / (noise RMS * 10^(SNR/20)). If the mixture peak exceeds 0.95, one common gain scales both bird and noise. Source audio is never overwritten.
Every output is reopened and checked for 80,000 samples, 16 kHz mono PCM-16, finite/nonzero content, preserved zero padding and quantization error <= one PCM LSB. Prequantization SNR is verified against target. Achieved SNR after saving treats decoded output minus the gain-scaled bird as effective noise, including quantization error.
Post-PCM SNR deviations >0.5 dB: 118. These remain flagged in the manifest, not hidden or automatically removed. Very low-energy clips are sensitive to 16-bit quantization.

Maximum absolute saved-audio SNR deviation: 31.443752 dB. Flagged examples require review before claiming target-SNR compliance or use in SNR-controlled experiments. Effective noise includes PCM quantization; target SNR is met before quantization, not necessarily after saving.

## Clean references and protection

birds_audio_augmented/train/<species>/clean/references.csv references existing clean training WAVs; no redundant clean audio copies. Paths are relative to the component directory. Clean reference hashes match authoritative assignment hashes. No validation/test waveform was used to estimate mixing parameters; they were only hashed for integrity. Validation and test stay in birds_audio_split/val and test. No noisy test outputs were made.
Original bird, prepared, split, noise files, metadata and prior reports were hashed before/after and remained unchanged. Parent and final group membership checks passed. All generated examples derive only from training membership. Each measurable training clip has exactly three noisy versions.
There is only one original noise recording in each category. Reusing these recordings for future noisy testing would not demonstrate independent-noise evaluation. Augmented example counts are not independent bird recordings: the training sources remain 755 parent files with unresolved original-event provenance.

| Species | Type | Examples |
|---|---|---:|
| Chestnut-backed_Owlet | clean | 568 |
| Chestnut-backed_Owlet | light_noise | 568 |
| Chestnut-backed_Owlet | medium_noise | 568 |
| Chestnut-backed_Owlet | heavy_noise | 568 |
| Crimson-fronted_Barbet | clean | 255 |
| Crimson-fronted_Barbet | light_noise | 255 |
| Crimson-fronted_Barbet | medium_noise | 255 |
| Crimson-fronted_Barbet | heavy_noise | 255 |
| Green-billed_Coucal | clean | 677 |
| Green-billed_Coucal | light_noise | 677 |
| Green-billed_Coucal | medium_noise | 677 |
| Green-billed_Coucal | heavy_noise | 677 |
| Spot-winged_Thrush | clean | 1351 |
| Spot-winged_Thrush | light_noise | 1351 |
| Spot-winged_Thrush | medium_noise | 1351 |
| Spot-winged_Thrush | heavy_noise | 1351 |
| Sri_Lanka_Blue_Magpie | clean | 377 |
| Sri_Lanka_Blue_Magpie | light_noise | 377 |
| Sri_Lanka_Blue_Magpie | medium_noise | 377 |
| Sri_Lanka_Blue_Magpie | heavy_noise | 377 |
| Sri_Lanka_Frogmouth | clean | 1775 |
| Sri_Lanka_Frogmouth | light_noise | 1773 |
| Sri_Lanka_Frogmouth | medium_noise | 1773 |
| Sri_Lanka_Frogmouth | heavy_noise | 1773 |
| Sri_Lanka_Grey_Hornbill | clean | 211 |
| Sri_Lanka_Grey_Hornbill | light_noise | 210 |
| Sri_Lanka_Grey_Hornbill | medium_noise | 210 |
| Sri_Lanka_Grey_Hornbill | heavy_noise | 210 |
| Sri_Lanka_Junglefowl | clean | 841 |
| Sri_Lanka_Junglefowl | light_noise | 841 |
| Sri_Lanka_Junglefowl | medium_noise | 841 |
| Sri_Lanka_Junglefowl | heavy_noise | 841 |
| Sri_Lanka_Spurfowl | clean | 657 |
| Sri_Lanka_Spurfowl | light_noise | 657 |
| Sri_Lanka_Spurfowl | medium_noise | 657 |
| Sri_Lanka_Spurfowl | heavy_noise | 657 |
| Yellow-fronted_Barbet | clean | 672 |
| Yellow-fronted_Barbet | light_noise | 671 |
| Yellow-fronted_Barbet | medium_noise | 671 |
| Yellow-fronted_Barbet | heavy_noise | 671 |

Script: `python components/audio_classification/src/augment_training_audio.py`. Refuses existing output/report/staging directories. Staging is published only after verification. No model training, Git operations, relabeling or previous-file changes. Stop pending approval before model training.
