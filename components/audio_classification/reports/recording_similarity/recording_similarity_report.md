# Recording similarity and provenance investigation

Generated 2026-10-17T17:54:14.273554+00:00 (UTC).

## Results

945 bird recordings; 934 byte-unique representatives acoustically analyzed. All exact aliases remain in the output groups.
Fingerprint-selected pairs: 122. Reported pair classifications: {'confirmed_exact_duplicate': 11, 'probable_acoustic_match': 51, 'uncertain_similarity': 71}.
Possible components: 883; multi-file components: 60. These are review hypotheses, not confirmed independent recording events.
Cross-species reported pairs: 44. Original bird/noise files and metadata hashes, sizes and modification times unchanged: True.

## Method and thresholds

Read all prior audit and data-quality report files and parsed their CSV/Markdown contents. Revalidated bird hashes against the audit. Analyze byte-identical audio once and explicitly include all exact duplicate edges. No species restriction is used for candidate matching.
Audio is decoded, averaged to mono and downsampled to 8 kHz in memory solely for analysis. No transformed audio is saved. STFT: 512 samples, hop 128; local spectral maxima over 9 frequency bins by 9 time frames, bins below 125 Hz ignored, peaks within 55 dB of recording maximum; retain up to three peaks per frame. Pair each peak with up to five subsequent peaks 4–60 frames away. Hash frequency bins in pairs and time differences in pairs of frames.
An inverted landmark index retrieves matches without all-pairs waveform scans. Suppress tokens with more than 80 postings or more than 20 distinct recordings (52585 suppressed tokens). For each candidate pair test at most three leading offset buckets (64 ms), requiring 8 votes, 4 distinct anchor times, and 0.5 seconds anchor span.
Refine each candidate offset by normalized FFT cross-correlation over up to five two-second anchors, searching ±150 ms. At the strongest alignment, inspect up to ten non-overlapping two-second waveform windows spread across the overlap. Correlation is mean-centered, normalized and absolute, so gain changes and polarity inversion are tolerated. Offsets mean time in B = time in A + offset.
Confirmed exact duplicates require full-file SHA-256 equality. Probable acoustic matches require median absolute waveform correlation ≥0.90, at least 80% of sampled windows ≥0.90, and ≥3 seconds tested. Other fingerprint-selected pairs are uncertain similarities, including failed waveform confirmation. They are not accepted identity links. Thresholds are heuristic, not calibrated probabilities.
aligned_extent_seconds describes the extent available at the estimated lag, NOT a claim that the entire extent matches. tested_seconds and tested_intervals_a describe actual sampled evidence. Gain estimates are least-squares B/A slopes on analysis waveforms, not measured original recording gain settings.

## Possible groups and review

Connected components use confirmed exact and probable acoustic edges only. Uncertain edges remain in the pair/manual tables and do not merge groups. All 945 files appear once in the membership CSV. Transitive grouping is conservative and requires manual review; an edge does not establish the correctness of either original ID. No splits or exclusions were performed.
For each listed pair, listen at the reported A intervals and corresponding B intervals using the offset. Compare call sequences AND background events, assess gain/re-encoding/trimming explanations, and record source URLs, catalog namespace, recorder, date/location and edit history. Cross-species matches require label review. Complete reviewer/date/findings/decision fields in manual_similarity_review.csv; all decisions start pending.
## Limitations

A non-match never proves independence. Same field sessions with different excerpts can evade acoustic detection. Fingerprint pruning, frequency quantization, very quiet or short clips, overlaps shorter than three seconds, phase distortion, heavy compression, pitch/time changes and content above 4 kHz can cause missed matches. Repeated stereotyped bird calls and stationary background can produce false candidates or high correlation. Testing sampled windows does not verify every sample or local edits. No human listening or external provenance verification is claimed.
The 11 known exact duplicate groups are included explicitly rather than counted as independently recovered positives. No synthetic transformation benchmark was performed; recall for re-encoded, gain-adjusted or trimmed copies is not quantified. Prior near-silent flags remain relevant to manual review.
A small in-memory waveform sanity check recovered a two-second trim with 0.35 gain at the expected lag and did not accept unrelated random noise. This checks alignment logic only, not fingerprint retrieval recall or real-world classification accuracy.
Analysis resampling/fingerprints are investigative measurements only: no preprocessing dataset, noise augmentation, model training, train/validation/test split, original-file modification or Git operation occurred. Stop here pending user approval.

## Reproduction

`python components/audio_classification/src/check_recording_similarity.py`
Requires a nonexistent output directory; refuses overwrites. Dependencies: numpy 2.4.6, scipy 1.17.1, soundfile 0.14.0.

## Prior reports read

```json
[
  {
    "path": "reports\\dataset_audit\\audio_quality_report.csv",
    "sha256": "051043acfbae871155b262ade943dbab039c0da1f42f5126454551dde9bbd11c",
    "rows": 951
  },
  {
    "path": "reports\\dataset_audit\\dataset_summary.csv",
    "sha256": "f8185a7fb4041527d94a8705f0b0a63d6ef33d588ed0db519a00c1baef124b69",
    "rows": 10
  },
  {
    "path": "reports\\dataset_audit\\duplicate_report.csv",
    "sha256": "49128986349ab337dccc763d985a7de26a3c7c8ef58ba91bb6fa5738e0c37add",
    "rows": 22
  },
  {
    "path": "reports\\dataset_audit\\metadata_validation.csv",
    "sha256": "c1e99d0c82b2d26064b71cc5f5bcd01bc5260a6d9b63a4d11d26eb1583aae29a",
    "rows": 1593
  },
  {
    "path": "reports\\dataset_audit\\noise_summary.csv",
    "sha256": "2fc8462567ac0c4414a61a924f5895e27d96b2763ac16397b388716016b7b47a",
    "rows": 6
  },
  {
    "path": "reports\\dataset_audit\\phase_01_report.md",
    "sha256": "6cb58420715f11dbf5b53eef1826f32968f01a577a86aec13e922dfcbf52cb5c",
    "characters": 5389
  },
  {
    "path": "reports\\dataset_audit\\species_distribution.png",
    "sha256": "f66728b49e66dd9dbad9ffac54518c9643a2ea91f2cc63bc29c782bf8f97af12",
    "bytes": 140731
  },
  {
    "path": "reports\\data_quality\\data_quality_report.md",
    "sha256": "1b336a0b0ee37a948ab8b2896333cac82661fc8e3367971841df2215ea210ea9",
    "characters": 9444
  },
  {
    "path": "reports\\data_quality\\duplicate_identity_review.csv",
    "sha256": "204c8d412982b6d991004eb7212a2b45b1a7b062f4afef647d53800c6d086407",
    "rows": 22
  },
  {
    "path": "reports\\data_quality\\input_integrity.csv",
    "sha256": "acde567ec491e218a546d25799257af6dbb6d924a702729579f10067f74c5393",
    "rows": 953
  },
  {
    "path": "reports\\data_quality\\manual_listening_checklist.csv",
    "sha256": "d7127527d95d4d7359648da6041506e7353be056824fa749e6a186cecc9712f6",
    "rows": 945
  },
  {
    "path": "reports\\data_quality\\near_silent_review.csv",
    "sha256": "3b6ab915f057f1eccd159027a1df84aff34bfac9961c0a6aeffe6362d06ecace",
    "rows": 20
  },
  {
    "path": "reports\\data_quality\\recording_identity_review.csv",
    "sha256": "28baf6e440a39a97d745d71bd70c20267052697e7558af1625d568a6ff9923aa",
    "rows": 945
  },
  {
    "path": "reports\\data_quality\\recording_links.csv",
    "sha256": "b1ffec77b8af99a0476aee99f94a80dac945ebbab8278f7b03e921dcfbeabfad",
    "rows": 11
  },
  {
    "path": "reports\\data_quality\\species_identity_summary.csv",
    "sha256": "1254b5c7d821558303886a0905a72449ca2fcfdcbbcf5c77f9261282d6e27f46",
    "rows": 10
  },
  {
    "path": "reports\\data_quality\\unverified_local_ids.csv",
    "sha256": "62a968a71218c7a40919a99fda363befac6ec4f85d4f86e1de7d8227e35d12f5",
    "rows": 648
  }
]
```
