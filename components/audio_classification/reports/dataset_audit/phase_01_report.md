# Phase 1 dataset audit

Generated: 2026-10-17T16:32:47.454794+00:00 (UTC).

Found **945 bird audio files in 10 species folders**, plus **6 noise files in 6 categories**.
Full-file decoding attempted for all files; decode errors: 0. Input SHA-256 hashes, sizes and modification times unchanged: **True**.

## Bird inventory

| Species | Files | Distinct metadata IDs | Catalog-style IDs | Unverified local IDs |
|---|---:|---:|---:|---:|
| Chestnut-backed Owlet | 78 | 78 | 30 | 48 |
| Crimson-fronted Barbet | 50 | 50 | 13 | 37 |
| Green-billed Coucal | 64 | 64 | 24 | 40 |
| Spot-winged Thrush | 109 | 109 | 46 | 63 |
| Sri Lanka Blue Magpie | 58 | 58 | 21 | 37 |
| Sri Lanka Frogmouth | 284 | 284 | 35 | 249 |
| Sri Lanka Grey Hornbill | 45 | 45 | 14 | 31 |
| Sri Lanka Junglefowl | 87 | 87 | 37 | 50 |
| Sri Lanka Spurfowl | 69 | 69 | 31 | 38 |
| Yellow-fronted Barbet | 101 | 101 | 46 | 55 |

## Original recordings and the 20-recording threshold

Numeric / XC-prefixed IDs are treated as catalog-style original-recording identifiers supplied by metadata. They are stronger evidence than sequential output filenames, but the catalog, original sources and embedded provenance have not been independently verified. Descriptive IDs are counted separately as unverified local IDs. Unique IDs or hashes do not by themselves prove biological independence; edited or re-encoded copies can differ.
The exact independently verified original-recording count is therefore unknown. The catalog-style count is provisional, not a proven lower bound.
Species with fewer than 20 catalog-style IDs: Crimson-fronted_Barbet (13), Sri_Lanka_Grey_Hornbill (14).

## Audio quality and formats

Bird duration: 12.18 hours.
Files flagged for quality review: 20. Findings: {'near_silent_review': 20}.
Bird formats/subtypes/rates/channels: {('WAV', 'PCM_16', 16000, 1): 945}.
Decoder methods: {'direct': 950, 'in_memory_ogg_vorbis_stream_selection': 1}. Ogg Skeleton containers, when rejected by libsndfile, are inspected by selecting their existing Vorbis pages in memory and decoding that stream. No converted or extracted audio is saved.
Every audio file is decoded in blocks; sample rate, channels, duration, subtype and bit depth are recorded per file. Digital silence means every decoded sample is zero. Near-silence means nonzero audio below -60 dBFS RMS and requires listening review. Compressed MP3/Vorbis audio has no meaningful fixed PCM bit depth. Successful decoding does not establish species identity or absence of audible defects.

## Metadata validation

Metadata rows: 945. Findings by check: {'unavailable_provenance_source': 945, 'unverified_original_id': 648}.
Active file_path values are checked against the audio inventory and species folders; durations use a 0.01-second tolerance. Missing values, duplicate rows/paths/sources/IDs and missing inventory coverage are checked. Folder consistency cannot establish whether the bird heard is actually the labeled species.
Unavailable source paths are historical provenance references, not broken active audio paths. They prevent independent source verification.

No findings for a check means it passed; warnings about historical sources and unverified IDs are recorded separately from errors.

## Exact duplicates

11 SHA-256 duplicate groups; 22 files participate. The CSV contains one row per file in a group (header only when none). Hashing covers both bird and noise files. Similar audio, alternate encodings and overlapping segments are not detected by byte hashes.

Compare duplicate_report.csv with metadata: exact duplicate files carrying different original IDs are evidence that distinct metadata IDs overcount independent recordings.

## Existing segmentation or augmentation

Filename derivative-marker matches: 0. Repeated metadata ID groups: 0.
Numbered output filenames alone are not evidence of segmentation. Metadata references source files with other formats, indicating prior conversion for those entries. Naming, duration distribution and repeated source/ID checks cannot prove that no segmentation or augmentation occurred. Source originals or preparation logs are needed to settle this; no new preprocessing or augmentation was performed.

## Noise inventory

| Category | Files | Format / subtype | Rate (Hz) | Channels | Duration (s) |
|---|---:|---|---|---|---:|
| Forest ambient sound | 1 | OGG / VORBIS | 48000 | 2 | 180.00 |
| Insects | 1 | MP3 / MPEG_LAYER_III | 48000 | 2 | 416.17 |
| Other bird calls - mixed bird sounds | 1 | OGG / VORBIS | 48000 | 2 | 312.05 |
| Rain | 1 | OGG / VORBIS | 44100 | 1 | 44.96 |
| Streams - flowing water | 1 | OGG / VORBIS | 48000 | 2 | 140.06 |
| Wind | 1 | OGG / VORBIS | 44100 | 2 | 272.76 |

Noisy/SOURCES.txt uses historical Rain/... prefixes that do not match the current category layout; the recordings themselves are inventoried at their actual paths. Non-audio inputs are not counted as recordings.

## Reproduce and next action

`python components/audio_classification/src/audit_dataset.py`

Libraries: numpy 2.4.6; soundfile 0.14.0; libsndfile 1.2.2; matplotlib 3.11.0.
Review flagged audio, resolve provenance for local IDs and verify source identities before treating every file as an independent recording. All requested outputs are in this report directory. Original recordings and metadata were not modified. Phase 2 has not started and requires user approval.
