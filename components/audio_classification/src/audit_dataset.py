"""Read-only Phase 1 audit. Requires numpy, soundfile and matplotlib.

Run: python components/audio_classification/src/audit_dataset.py
Input recordings are only opened for reading. Decoding is for inspection only;
no audio, splits, features, or training outputs are produced.
"""
from pathlib import Path
from collections import Counter, defaultdict
import csv
import hashlib
import math
import re
import struct
import os
import io
from datetime import datetime, timezone

import numpy as np
import soundfile as sf
BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'reports' / 'dataset_audit'
# Keep Matplotlib's generated font/config cache inside the authorized component.
os.environ['MPLCONFIGDIR'] = str(BASE / '.cache' / 'matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

EXTENSIONS = {'.wav', '.wave', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.aif', '.aiff', '.opus', '.wma', '.au'}
MARKERS = re.compile(r'(?:^|[ _-])(segment|seg|chunk|clip|augment|aug|pitch|stretch|shift|mix|noise|speed)(?:[ _-]|\d|$)', re.I)


def write_csv(name, rows, fields):
    with (OUT / name).open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def rel(path):
    return path.relative_to(BASE).as_posix()


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def open_audio(path):
    try:
        return sf.SoundFile(path), 'direct'
    except sf.LibsndfileError:
        # Ogg Skeleton multiplexing is unsupported by some libsndfile builds.
        # Select the existing Vorbis pages in memory for read-only decoding.
        if path.suffix.lower() != '.ogg':
            raise
        data = path.read_bytes()
        pages, serial, offset = [], None, 0
        while offset < len(data):
            if data[offset:offset + 4] != b'OggS' or offset + 27 > len(data):
                raise ValueError('Invalid or truncated Ogg page')
            segments = data[offset + 26]
            payload = offset + 27 + segments
            if payload > len(data):
                raise ValueError('Truncated Ogg segment table')
            end = payload + sum(data[offset + 27:payload])
            if end > len(data):
                raise ValueError('Truncated Ogg payload')
            page_serial = data[offset + 14:offset + 18]
            if data[payload:payload + 7] == b'\x01vorbis':
                if serial is not None and serial != page_serial:
                    raise ValueError('Multiple Vorbis streams require separate review')
                serial = page_serial
            pages.append((page_serial, data[offset:end]))
            offset = end
        if serial is None:
            raise ValueError('No Vorbis stream found')
        return sf.SoundFile(io.BytesIO(b''.join(page for sid, page in pages if sid == serial))), 'in_memory_ogg_vorbis_stream_selection'


def inspect(path, kind):
    stat = path.stat()
    result = dict(file_path=rel(path), dataset=kind, category=path.relative_to(BASE / kind).parts[0],
                  size_bytes=stat.st_size, sha256=digest(path), format='', subtype='',
                  sample_rate_hz='', channels='', bit_depth='', duration_seconds='',
                  frames='', decoded_frames=0, peak_amplitude='', rms_dbfs='',
                  digital_silence=False, near_silent=False, nonfinite_samples=0,
                  wav_declared_data_bytes='', wav_data_truncated=False,
                  filename_derivative_marker=bool(MARKERS.search(path.stem)),
                  decoder_method='', status='ok', issues='', error='')
    issues = []
    if stat.st_size == 0:
        issues.append('zero_byte_file')
    # libsndfile can silently accept truncated WAV payloads; inspect RIFF sizes too.
    with path.open('rb') as f:
        header = f.read(12)
        if header[:4] == b'RIFF' and header[8:12] == b'WAVE':
            if struct.unpack('<I', header[4:8])[0] + 8 > stat.st_size:
                issues.append('truncated_riff_container')
            while f.tell() + 8 <= stat.st_size:
                chunk, size = struct.unpack('<4sI', f.read(8))
                if chunk == b'data':
                    result['wav_declared_data_bytes'] = size
                    result['wav_data_truncated'] = f.tell() + size > stat.st_size
                    if result['wav_data_truncated']:
                        issues.append('truncated_wav_data')
                    break
                f.seek(size + size % 2, 1)
    try:
        opened, method = open_audio(path)
        result['decoder_method'] = method
        with opened as audio:
            result.update(format=audio.format, subtype=audio.subtype, sample_rate_hz=audio.samplerate,
                          channels=audio.channels, frames=audio.frames,
                          duration_seconds=audio.frames / audio.samplerate)
            depths = {'PCM_U8': 8, 'PCM_S8': 8, 'PCM_16': 16, 'PCM_24': 24, 'PCM_32': 32,
                      'FLOAT': 32, 'DOUBLE': 64}
            result['bit_depth'] = depths.get(audio.subtype, 'not applicable (compressed codec)')
            peak, squares, samples, frames, invalid = 0.0, 0.0, 0, 0, 0
            for block in audio.blocks(blocksize=131072, dtype='float64', always_2d=True):
                frames += len(block)
                finite = np.isfinite(block)
                invalid += int(block.size - finite.sum())
                values = block[finite]
                if values.size:
                    peak = max(peak, float(np.max(np.abs(values))))
                    squares += float(np.sum(values * values))
                    samples += values.size
            db = 10 * math.log10(squares / samples) if squares and samples else -math.inf
            result.update(decoded_frames=frames, peak_amplitude=peak, rms_dbfs=db,
                          digital_silence=bool(samples and peak == 0),
                          near_silent=bool(samples and peak > 0 and db < -60), nonfinite_samples=invalid)
            if frames == 0:
                issues.append('empty_audio')
            if frames != audio.frames:
                issues.append('decoded_frame_count_mismatch')
            if invalid:
                issues.append('nonfinite_samples')
            if result['digital_silence']:
                issues.append('digital_silence')
            if result['near_silent']:
                issues.append('near_silent_review')
            expected = {'.wav': {'WAV', 'WAVEX', 'RF64'}, '.ogg': {'OGG'}, '.mp3': {'MP3', 'MPEG-1/2 Audio'}}
            if path.suffix.lower() in expected and audio.format not in expected[path.suffix.lower()]:
                issues.append('extension_format_mismatch')
    except Exception as exc:
        issues.append('unreadable_or_decode_error')
        result['error'] = str(exc)
    result['issues'] = ';'.join(issues)
    result['status'] = 'review' if issues else 'ok'
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = sorted(p for kind in ('birds_audio', 'Noisy') for p in (BASE / kind).rglob('*') if p.is_file())
    before = {rel(p): (p.stat().st_size, p.stat().st_mtime_ns, digest(p)) for p in inputs}
    files = [p for p in inputs if p.suffix.lower() in EXTENSIONS]
    quality = []
    for i, path in enumerate(files, 1):
        quality.append(inspect(path, path.relative_to(BASE).parts[0]))
        if i % 100 == 0 or i == len(files):
            print(f'Inspected {i}/{len(files)} audio files', flush=True)
    lookup = {r['file_path'].casefold(): r for r in quality}
    with (BASE / 'birds_audio' / 'metadata.csv').open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        metadata = list(reader)
    validations = []

    def issue(row, path, check, detail, severity='error'):
        validations.append(dict(row_number=row, file_path=path, severity=severity, check=check, detail=detail))

    required = ['file_path', 'species', 'original_recording_id', 'source', 'duration_seconds']
    for name in required:
        if name not in columns:
            issue('', '', 'missing_column', name)
    by_path, ids, sources, exact_rows = defaultdict(list), defaultdict(list), defaultdict(list), defaultdict(list)
    valid_meta = defaultdict(list)
    for line, row in enumerate(metadata, 2):
        path = (row.get('file_path') or '').strip().replace('\\', '/')
        for key in columns:
            if not (row.get(key) or '').strip():
                issue(line, path, 'missing_value', key)
        if None in row:
            issue(line, path, 'extra_csv_fields', str(row[None]))
        by_path[path.casefold()].append(line)
        exact_rows[tuple(row.get(k) for k in columns)].append(line)
        rid = (row.get('original_recording_id') or '').strip()
        source = (row.get('source') or '').strip()
        if rid:
            ids[rid].append((line, row.get('species'), path))
        if source:
            sources[source.casefold()].append(line)
        audio = lookup.get(path.casefold())
        if not audio or audio['dataset'] != 'birds_audio':
            issue(line, path, 'incorrect_or_missing_audio_path', 'Not a bird audio file in this inventory')
        else:
            if row.get('species') != audio['category']:
                issue(line, path, 'species_label_mismatch', f"Folder label: {audio['category']}")
            else:
                valid_meta[path.casefold()].append(row)
            try:
                duration = float(row.get('duration_seconds', ''))
                if not math.isfinite(duration) or duration <= 0:
                    raise ValueError('Duration must be positive and finite')
                if audio['duration_seconds'] != '' and abs(duration - audio['duration_seconds']) > 0.01:
                    issue(line, path, 'duration_mismatch', f"metadata={duration}; decoded={audio['duration_seconds']}")
            except (TypeError, ValueError) as exc:
                issue(line, path, 'invalid_duration', str(exc))
        if rid and not re.fullmatch(r'(?:XC)?\d+', rid, re.I):
            issue(line, path, 'unverified_original_id', 'Descriptive/local ID; independence cannot be established from this name.', 'warning')
        if source and not (BASE / source).is_file():
            issue(line, path, 'unavailable_provenance_source', 'Historical source is not present; this is distinct from the active audio path.', 'warning')
    for label, groups in [('duplicate_metadata_row', exact_rows), ('duplicate_audio_path', by_path), ('repeated_source', sources)]:
        for key, lines in groups.items():
            if len(lines) > 1:
                issue(';'.join(map(str, lines)), str(key), label, f'{len(lines)} entries')
    for rid, entries in ids.items():
        if len(entries) > 1:
            issue(';'.join(str(e[0]) for e in entries), '', 'repeated_original_id', rid, 'warning')
            if len({e[1] for e in entries}) > 1:
                issue('', '', 'original_id_species_conflict', rid)
    for audio in quality:
        if audio['dataset'] == 'birds_audio' and audio['file_path'].casefold() not in by_path:
            issue('', audio['file_path'], 'audio_missing_metadata', 'No metadata entry')
    hashes = defaultdict(list)
    for row in quality:
        hashes[row['sha256']].append(row)
    duplicates = []
    for sha, group in hashes.items():
        if len(group) > 1:
            for row in group:
                duplicates.append(dict(sha256=sha, group_size=len(group), file_path=row['file_path'],
                                       dataset=row['dataset'], category=row['category'], size_bytes=row['size_bytes'],
                                       cross_category=len({r['category'] for r in group}) > 1))
    summary = []
    for folder in sorted((BASE / 'birds_audio').iterdir()):
        if not folder.is_dir():
            continue
        group = [r for r in quality if r['dataset'] == 'birds_audio' and r['category'] == folder.name]
        records = [valid_meta[r['file_path'].casefold()][0] for r in group if len(valid_meta[r['file_path'].casefold()]) == 1]
        numeric = {re.sub('^XC', '', r['original_recording_id'], flags=re.I) for r in records if re.fullmatch(r'(?:XC)?\d+', r['original_recording_id'], re.I)}
        local = {r['original_recording_id'] for r in records if not re.fullmatch(r'(?:XC)?\d+', r['original_recording_id'], re.I)}
        durations = [r['duration_seconds'] for r in group if r['duration_seconds'] != '']
        summary.append(dict(species=folder.name, audio_files=len(group), unique_file_hashes=len({r['sha256'] for r in group}),
                            metadata_distinct_original_ids=len(numeric | local),
                            numeric_catalog_style_original_ids=len(numeric), unverified_local_original_ids=len(local),
                            independently_verified_original_count='unknown (source evidence unavailable)',
                            below_20_catalog_style_ids=len(numeric) < 20,
                            total_duration_seconds=sum(durations), min_duration_seconds=min(durations, default=0),
                            max_duration_seconds=max(durations, default=0),
                            sample_rates_hz=';'.join(map(str, sorted({r['sample_rate_hz'] for r in group if r['sample_rate_hz'] != ''}))),
                            channels=';'.join(map(str, sorted({r['channels'] for r in group if r['channels'] != ''}))),
                            quality_flagged_files=sum(r['status'] != 'ok' for r in group)))
    noise = []
    for folder in sorted((BASE / 'Noisy').iterdir()):
        if folder.is_dir():
            group = [r for r in quality if r['dataset'] == 'Noisy' and r['category'] == folder.name]
            noise.append(dict(category=folder.name, audio_files=len(group), formats=';'.join(sorted({r['format'] for r in group})),
                              subtypes=';'.join(sorted({r['subtype'] for r in group})),
                              sample_rates_hz=';'.join(sorted({str(r['sample_rate_hz']) for r in group})),
                              channels=';'.join(sorted({str(r['channels']) for r in group})),
                              bit_depths=';'.join(sorted({str(r['bit_depth']) for r in group})),
                              total_duration_seconds=sum(r['duration_seconds'] for r in group if r['duration_seconds'] != ''),
                              quality_flagged_files=sum(r['status'] != 'ok' for r in group)))
    write_csv('audio_quality_report.csv', quality, list(quality[0]))
    write_csv('dataset_summary.csv', summary, list(summary[0]))
    write_csv('noise_summary.csv', noise, list(noise[0]))
    write_csv('duplicate_report.csv', duplicates, ['sha256', 'group_size', 'file_path', 'dataset', 'category', 'size_bytes', 'cross_category'])
    write_csv('metadata_validation.csv', validations or [dict(check='all_checks_passed', severity='info')], ['row_number', 'file_path', 'severity', 'check', 'detail'])
    x = np.arange(len(summary))
    fig, ax = plt.subplots(figsize=(14, 8))
    for offset, key, label, color in [(-.2, 'audio_files', 'Audio files', '#2878a0'), (.2, 'numeric_catalog_style_original_ids', 'Catalog-style IDs (not independently verified)', '#e3a33b')]:
        bars = ax.bar(x + offset, [r[key] for r in summary], .4, label=label, color=color)
        ax.bar_label(bars, fontsize=8, padding=3)
    ax.axhline(20, color='red', linestyle='--', linewidth=1, label='20-recording threshold')
    ax.set_xticks(x, [r['species'].replace('_', ' ') for r in summary], rotation=40, ha='right')
    ax.set_ylabel('Count')
    ax.set_title('Phase 1 bird dataset: file counts and original-recording ID evidence')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / 'species_distribution.png', dpi=180)
    plt.close(fig)
    after = {rel(p): (p.stat().st_size, p.stat().st_mtime_ns, digest(p)) for p in inputs}
    unchanged = before == after
    counts = Counter(r['check'] for r in validations)
    flagged = [r for r in quality if r['status'] != 'ok']
    birds = [r for r in quality if r['dataset'] == 'birds_audio']
    lines = ['# Phase 1 dataset audit', '', f'Generated: {datetime.now(timezone.utc).isoformat()} (UTC).', '',
             f'Found **{len(birds)} bird audio files in {len(summary)} species folders**, plus **{len(quality)-len(birds)} noise files in {len(noise)} categories**.',
             f'Full-file decoding attempted for all files; decode errors: {sum(bool(r["error"]) for r in quality)}. Input SHA-256 hashes, sizes and modification times unchanged: **{unchanged}**.', '',
             '## Bird inventory', '', '| Species | Files | Distinct metadata IDs | Catalog-style IDs | Unverified local IDs |', '|---|---:|---:|---:|---:|']
    lines += [f"| {r['species'].replace('_', ' ')} | {r['audio_files']} | {r['metadata_distinct_original_ids']} | {r['numeric_catalog_style_original_ids']} | {r['unverified_local_original_ids']} |" for r in summary]
    lines += ['', '## Original recordings and the 20-recording threshold', '',
              'Numeric / XC-prefixed IDs are treated as catalog-style original-recording identifiers supplied by metadata. They are stronger evidence than sequential output filenames, but the catalog, original sources and embedded provenance have not been independently verified. Descriptive IDs are counted separately as unverified local IDs. Unique IDs or hashes do not by themselves prove biological independence; edited or re-encoded copies can differ.',
              'The exact independently verified original-recording count is therefore unknown. The catalog-style count is provisional, not a proven lower bound.',
              'Species with fewer than 20 catalog-style IDs: ' + (', '.join(r['species'] + ' (' + str(r['numeric_catalog_style_original_ids']) + ')' for r in summary if r['below_20_catalog_style_ids']) or 'none') + '.', '',
              '## Audio quality and formats', '',
              f'Bird duration: {sum(r["duration_seconds"] for r in birds if r["duration_seconds"] != "") / 3600:.2f} hours.',
              f'Files flagged for quality review: {len(flagged)}. Findings: {dict(Counter(i for r in flagged for i in r["issues"].split(";")))}.',
              f'Bird formats/subtypes/rates/channels: {dict(Counter((r["format"], r["subtype"], r["sample_rate_hz"], r["channels"]) for r in birds))}.',
              f'Decoder methods: {dict(Counter(r["decoder_method"] for r in quality))}. Ogg Skeleton containers, when rejected by libsndfile, are inspected by selecting their existing Vorbis pages in memory and decoding that stream. No converted or extracted audio is saved.',
              'Every audio file is decoded in blocks; sample rate, channels, duration, subtype and bit depth are recorded per file. Digital silence means every decoded sample is zero. Near-silence means nonzero audio below -60 dBFS RMS and requires listening review. Compressed MP3/Vorbis audio has no meaningful fixed PCM bit depth. Successful decoding does not establish species identity or absence of audible defects.', '',
              '## Metadata validation', '', f'Metadata rows: {len(metadata)}. Findings by check: {dict(counts)}.',
              'Active file_path values are checked against the audio inventory and species folders; durations use a 0.01-second tolerance. Missing values, duplicate rows/paths/sources/IDs and missing inventory coverage are checked. Folder consistency cannot establish whether the bird heard is actually the labeled species.',
              'Unavailable source paths are historical provenance references, not broken active audio paths. They prevent independent source verification.', '',
              'No findings for a check means it passed; warnings about historical sources and unverified IDs are recorded separately from errors.', '',
              '## Exact duplicates', '',
              f'{len({r["sha256"] for r in duplicates})} SHA-256 duplicate groups; {len(duplicates)} files participate. The CSV contains one row per file in a group (header only when none). Hashing covers both bird and noise files. Similar audio, alternate encodings and overlapping segments are not detected by byte hashes.', '',
              'Compare duplicate_report.csv with metadata: exact duplicate files carrying different original IDs are evidence that distinct metadata IDs overcount independent recordings.', '',
              '## Existing segmentation or augmentation', '',
              f'Filename derivative-marker matches: {sum(r["filename_derivative_marker"] for r in quality)}. Repeated metadata ID groups: {sum(len(v)>1 for v in ids.values())}.',
              'Numbered output filenames alone are not evidence of segmentation. Metadata references source files with other formats, indicating prior conversion for those entries. Naming, duration distribution and repeated source/ID checks cannot prove that no segmentation or augmentation occurred. Source originals or preparation logs are needed to settle this; no new preprocessing or augmentation was performed.', '',
              '## Noise inventory', '', '| Category | Files | Format / subtype | Rate (Hz) | Channels | Duration (s) |', '|---|---:|---|---|---|---:|']
    lines += [f"| {r['category']} | {r['audio_files']} | {r['formats']} / {r['subtypes']} | {r['sample_rates_hz']} | {r['channels']} | {r['total_duration_seconds']:.2f} |" for r in noise]
    lines += ['', 'Noisy/SOURCES.txt uses historical Rain/... prefixes that do not match the current category layout; the recordings themselves are inventoried at their actual paths. Non-audio inputs are not counted as recordings.', '',
              '## Reproduce and next action', '', '`python components/audio_classification/src/audit_dataset.py`', '',
              f'Libraries: numpy {np.__version__}; soundfile {sf.__version__}; libsndfile {sf.__libsndfile_version__}; matplotlib {matplotlib.__version__}.',
              'Review flagged audio, resolve provenance for local IDs and verify source identities before treating every file as an independent recording. All requested outputs are in this report directory. Original recordings and metadata were not modified. Phase 2 has not started and requires user approval.']
    (OUT / 'phase_01_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if not unchanged:
        raise RuntimeError('Input changed during audit; inspect before trusting report')
    print(f'Done. Bird files: {len(birds)}; species: {len(summary)}; noise: {len(noise)} categories; flagged: {len(flagged)}. Inputs unchanged.', flush=True)


if __name__ == '__main__':
    main()
