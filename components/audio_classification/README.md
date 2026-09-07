# Component 02: Noise-Robust Bioacoustic Bird Call Recognition

This component is for Sri Lankan endemic bird audio classification.

## Purpose

The purpose of this component is to classify bird species using audio recordings.

## Research Workflow

1. Collect bird audio recordings.
2. Clean and split audio into short clips.
3. Extract audio features such as Mel spectrograms or MFCC.
4. Train a deep learning model.
5. Test the model using unseen audio.
6. Predict the bird species from a new audio file.

## Folder Structure

```text
audio_classification/
├── birds_audio/                 # Original 10 species folders and metadata.csv
├── Noisy/                       # Original six noise categories and SOURCES.txt
├── birds_audio_prepared/        # Five-second WAV clips and metadata.csv
├── src/
│   ├── audit_dataset.py
│   └── prepare_audio.py
├── reports/
│   ├── dataset_audit/           # Existing audit CSVs, chart and report
│   ├── data_quality/
│   ├── recording_similarity/
│   └── audio_preprocessing/     # Clip counts, source checks and errors
└── .cache/
    └── matplotlib/              # Generated cache, outside reports
```

## Current Status

Audit, quality review and similarity investigation are complete. The approved
preprocessing workflow creates five-second clips. No dataset splitting,
augmentation or training is performed. Original provenance requires review before
defining independent groups; catalog-style IDs alone do not prove independence.

The audit report is [phase_01_report.md](reports/dataset_audit/phase_01_report.md).
Its filename and historical results are preserved. The audit script now uses
`reports/dataset_audit/` for outputs and `.cache/matplotlib/` for its cache.

## Running the Audit

Dependencies: `numpy`, `soundfile`, `matplotlib`. From the repository root:

```powershell
python components/audio_classification/src/audit_dataset.py
```

This reads original inputs and regenerates the audit reports. Rerunning replaces
generated reports, but never writes original recordings or metadata.

## Preparation Helpers

Additional dependency: `scipy`. `src/prepare_audio.py` provides reusable functions:

- `read_audio`: read audio supported by the installed libsndfile decoder.
- `validate_audio`: check sample rate, shape, finite values, silence and levels.
- `validate_recording_metadata`: check the path, species and ID presence, retaining
  the supplied ID without asserting recording independence.
- `to_mono`: average channels in memory.
- `resample_audio`: resample in memory using an anti-aliasing polyphase filter.
- `save_audio`: exclusively create mono, 16 kHz, PCM-16 WAV files inside an allowed
  species folder under `birds_audio_prepared/`. The parent must already exist;
  existing files and out-of-range samples are rejected. The clipping workflow
  explicitly permits and flags silent intervals rather than discarding them.

Running without arguments only prints a status message. To create clips in an
empty prepared folder (refuses to overwrite outputs):

```powershell
python components/audio_classification/src/prepare_audio.py --prepare
```

The workflow preserves all valid source samples, with no gain changes. Short
recordings and final partial intervals are right-padded with zeros. Metadata
distinguishes actual source start/end times from the saved five-second duration,
records padding, and preserves parent IDs, original filenames, exact-content and
possible recording groups, and quality/provenance flags. Each saved clip is
reopened and checked sample-for-sample against its source interval plus padding.
See [the preprocessing report](reports/audio_preprocessing/audio_preprocessing_report.md).

The generic reader reports unsupported codecs/containers. Noise recordings are
not used in this workflow; the multiplexed Rain Ogg needs explicit handling
before any future use.

Keep `birds_audio/`, `Noisy/` and original metadata unchanged. Dataset splitting,
noise augmentation and model training require further approval.
