"""Reusable audio helpers and explicit --prepare five-second clipping pipeline.

Dependencies: numpy, soundfile, scipy. Recording provenance must be reviewed
before any future dataset splitting or augmentation.
"""
from pathlib import Path
from math import gcd
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

BASE = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = BASE / 'birds_audio_prepared'
SPECIES = frozenset({
    'Chestnut-backed_Owlet', 'Crimson-fronted_Barbet', 'Green-billed_Coucal',
    'Spot-winged_Thrush', 'Sri_Lanka_Blue_Magpie', 'Sri_Lanka_Frogmouth',
    'Sri_Lanka_Grey_Hornbill', 'Sri_Lanka_Junglefowl', 'Sri_Lanka_Spurfowl',
    'Yellow-fronted_Barbet',
})


def validate_audio(samples, sample_rate):
    """Reject invalid/empty samples; return silence and level diagnostics.

    Arrays use (frames,) or (frames, channels), with normalized float samples.
    Silence is reported, not silently removed. Near-silence is RMS < -60 dBFS.
    """
    if isinstance(sample_rate, bool) or not isinstance(sample_rate, (int, np.integer)) or sample_rate <= 0:
        raise ValueError('Sample rate must be a positive integer')
    data = np.asarray(samples)
    if data.ndim not in (1, 2) or data.size == 0 or (data.ndim == 2 and data.shape[1] == 0):
        raise ValueError('Expected nonempty frames or frames-by-channels audio')
    if not np.issubdtype(data.dtype, np.floating) or not np.isfinite(data).all():
        raise ValueError('Audio must contain finite floating-point samples')
    peak = float(np.max(np.abs(data)))
    # Scale before squaring to avoid overflow for invalid large amplitudes.
    rms = float(peak * np.sqrt(np.mean((data / peak) ** 2))) if peak else 0.0
    dbfs = float(20 * np.log10(rms)) if rms else float('-inf')
    return dict(frames=len(data), channels=1 if data.ndim == 1 else data.shape[1],
                sample_rate=int(sample_rate), duration_seconds=len(data) / sample_rate,
                peak=peak, rms_dbfs=dbfs, silent=peak == 0,
                near_silent=0 < rms < 0.001, exceeds_pcm_range=peak > 1)


def validate_recording_metadata(row, audio_path):
    """Check local path, species and ID presence, without claiming independence."""
    path = Path(audio_path).resolve(strict=True)
    root = (BASE / 'birds_audio').resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('Input must be an original bird file')
    species = path.relative_to(root).parts[0]
    if species not in SPECIES or row.get('species') != species:
        raise ValueError('Unknown species or metadata/folder label mismatch')
    raw_path = str(row.get('file_path', '')).replace('\\', '/')
    if not raw_path or (BASE / raw_path).resolve() != path:
        raise ValueError('Metadata path does not match the audio file')
    recording_id = str(row.get('original_recording_id') or '').strip()
    if not recording_id:
        raise ValueError('Original recording ID is missing')
    return dict(species=species, original_recording_id=row['original_recording_id'],
                provenance_verified=False)


def read_audio(path):
    """Read a libsndfile-supported file without modifying it.

    Unsupported codecs/containers raise an error; no automatic conversion occurs.
    In particular the audited multiplexed Rain Ogg needs a future explicit reader.
    """
    with sf.SoundFile(Path(path), mode='r') as audio:
        expected_frames = audio.frames
        rate = audio.samplerate
        samples = audio.read(dtype='float64', always_2d=True)
    validate_audio(samples, rate)
    if len(samples) != expected_frames:
        raise ValueError('Decoded frame count differs from the file header')
    return samples, rate


def to_mono(samples, sample_rate):
    """Average channels in memory; never write source audio."""
    validate_audio(samples, sample_rate)
    data = np.asarray(samples, dtype=np.float64)
    return data.copy() if data.ndim == 1 else data.mean(axis=1)


def resample_audio(samples, source_rate, target_rate=16000):
    """Polyphase resampling along the frame axis, in memory only."""
    validate_audio(samples, source_rate)
    validate_audio(samples, target_rate)
    divisor = gcd(int(source_rate), int(target_rate))
    if source_rate == target_rate:
        return np.asarray(samples).copy()
    result = resample_poly(samples, target_rate // divisor, source_rate // divisor, axis=0)
    validate_audio(result, target_rate)
    return result


def save_audio(destination, samples, sample_rate=16000, *, allow_silence=False):
    """Exclusively create mono 16-kHz PCM-16 WAV inside the prepared folder.

    Requires an existing parent directory and refuses overwrites, nonfinite audio
    and out-of-range samples. Silence is allowed only with allow_silence=True.
    """
    info = validate_audio(samples, sample_rate)
    if sample_rate != 16000 or info['channels'] != 1:
        raise ValueError('Prepared WAV must be mono at 16000 Hz')
    if (info['silent'] and not allow_silence) or info['exceeds_pcm_range']:
        raise ValueError('Cannot save silent or out-of-range audio')
    path = Path(destination).resolve()
    if not path.is_relative_to(OUTPUT_ROOT.resolve()) or path.suffix.lower() != '.wav':
        raise ValueError('Destination must be a WAV inside birds_audio_prepared')
    if path.relative_to(OUTPUT_ROOT.resolve()).parts[0] not in SPECIES:
        raise ValueError('Destination must be inside an existing species name')
    # Exclusive creation protects existing outputs, including original hardlinks.
    with path.open('xb') as stream:
        sf.write(stream, samples, sample_rate, format='WAV', subtype='PCM_16')
    return path


def prepare_dataset():
    """Preserve all valid source samples; pad short sources and final tails."""
    import csv
    import hashlib
    import json
    from collections import Counter, defaultdict
    from datetime import datetime, timezone

    reports = BASE / 'reports/audio_preprocessing'
    if reports.exists() or (OUTPUT_ROOT.exists() and any(OUTPUT_ROOT.iterdir())):
        raise FileExistsError('Refusing to overwrite existing prepared audio or reports')

    def read_csv(path):
        with path.open(encoding='utf-8-sig', newline='') as stream:
            return list(csv.DictReader(stream))

    def sha(path):
        h = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1048576), b''):
                h.update(block)
        return h.hexdigest()

    def snapshot():
        return {str(p.relative_to(BASE)): (p.stat().st_size, p.stat().st_mtime_ns, sha(p))
                for root in ('birds_audio', 'Noisy') for p in sorted((BASE/root).rglob('*')) if p.is_file()}

    before = snapshot()
    originals = read_csv(BASE/'birds_audio/metadata.csv')
    audit = {r['file_path']: r for r in read_csv(BASE/'reports/dataset_audit/audio_quality_report.csv')}
    group_rows = read_csv(BASE/'reports/recording_similarity/possible_recording_groups.csv')
    groups = {r['file_path']: r for r in group_rows}
    identities = {r['file_path']: r for r in read_csv(BASE/'reports/data_quality/recording_identity_review.csv')}
    pairs = read_csv(BASE/'reports/recording_similarity/similarity_pairs.csv')
    edges = defaultdict(list)
    for pair in pairs:
        edges[pair['file_a']].append(pair)
        edges[pair['file_b']].append(pair)
    expected = {r['file_path'] for r in originals}
    actual = {str(p.relative_to(BASE)).replace('\\', '/') for p in (BASE/'birds_audio').rglob('*.wav')}
    if len(originals)!=945 or len(expected)!=945 or expected!=actual or set(groups)!=expected or len(group_rows)!=945:
        raise ValueError('Inventory/group coverage mismatch; review inputs before preparation')
    if {p.name for p in (BASE/'birds_audio').iterdir() if p.is_dir()} != SPECIES:
        raise ValueError('Unexpected species folder inventory')
    for row in originals:
        path=BASE/row['file_path']; validate_recording_metadata(row,path)
        if sha(path)!=audit[row['file_path']]['sha256']:
            raise ValueError(f'Stale audit: {path}')
        group=groups[row['file_path']]
        if group['species']!=row['species'] or group['original_recording_id']!=row['original_recording_id']:
            raise ValueError('Group metadata mismatch')
    reports.mkdir(); OUTPUT_ROOT.mkdir(exist_ok=True)
    for species in sorted(SPECIES): (OUTPUT_ROOT/species).mkdir()
    clips=[]; sources=[]; errors=[]
    frames_per_clip=80000
    for number,row in enumerate(originals,1):
        source=row['file_path']; path=BASE/source; group=groups[source]; q=audit[source]
        flags=['unresolved_provenance']
        if q['near_silent']=='True': flags.append('near_silent_source')
        if any(p['classification']=='uncertain_similarity' for p in edges[source]): flags.append('uncertain_similarity')
        if any(p['cross_species']=='True' for p in edges[source]): flags.append('cross_species_similarity_candidate')
        if any(p['cross_species']=='True' and p['classification']!='uncertain_similarity' for p in edges[source]): flags.append('cross_species_conflict')
        if int(group['exact_edges']): flags.append('exact_duplicate_source')
        if int(group['probable_edges']): flags.append('probable_acoustic_match_source')
        source_result=dict(file_path=source,species=row['species'],original_recording_id=row['original_recording_id'],
            sample_rate='',channels='',encoding='',source_frames='',source_duration_seconds='',shorter_than_five_seconds='',
            expected_clips=0,verified_clips=0,status='pending',error='')
        try:
            info=sf.info(path)
            source_result.update(sample_rate=info.samplerate,channels=info.channels,encoding=info.subtype,
                source_frames=info.frames,source_duration_seconds=info.duration,shorter_than_five_seconds=info.frames<frames_per_clip)
            if info.samplerate!=16000 or info.channels!=1 or info.subtype!='PCM_16' or info.format!='WAV':
                raise ValueError('Unexpected source format; no silent format conversion')
            if q['status']!='ok' and q['issues']!='near_silent_review':
                raise ValueError('Source audit reports an integrity issue: '+q['issues'])
            samples,rate=read_audio(path)
            mono=to_mono(samples,rate)
            source_result['expected_clips']=(len(mono)+frames_per_clip-1)//frames_per_clip
            for clip_index,start in enumerate(range(0,len(mono),frames_per_clip),1):
                end=min(start+frames_per_clip,len(mono)); valid=mono[start:end]
                padding=frames_per_clip-len(valid)
                clip=np.pad(valid,(0,padding))
                diagnostics=validate_audio(valid,rate)
                clip_flags=list(flags)
                if padding: clip_flags.append('zero_padded_short_source' if len(mono)<frames_per_clip else 'zero_padded_final_tail')
                if diagnostics['silent']: clip_flags.append('silent_source_interval')
                elif diagnostics['near_silent']: clip_flags.append('near_silent_source_interval')
                name=f'{path.stem}__clip_{clip_index:05d}.wav'
                dest=OUTPUT_ROOT/row['species']/name
                save_audio(dest,clip,rate,allow_silence=True)
                # Read back every generated sample: exact PCM-16 preservation including padding.
                out_info=sf.info(dest); decoded,out_rate=sf.read(dest,dtype='float64')
                if (out_info.format,out_info.subtype,out_rate,out_info.channels,out_info.frames)!=('WAV','PCM_16',16000,1,80000):
                    raise ValueError('Output format verification failed: '+str(dest))
                if not np.array_equal(decoded,clip):
                    raise ValueError('Output differs from parent samples or zero padding: '+str(dest))
                clips.append(dict(original_filename=path.name,original_file_path=source,species=row['species'],
                    original_recording_id=row['original_recording_id'],recording_group_id=group['possible_group_id'],
                    group_status=group['group_status'],exact_content_group_id=identities[source]['content_group_id'],
                    exact_edges=group['exact_edges'],probable_edges=group['probable_edges'],uncertain_edges=group['uncertain_edges'],
                    clip_filename=name,clip_file_path=dest.relative_to(BASE).as_posix(),clip_index=clip_index,
                    start_time_seconds=start/rate,end_time_seconds=end/rate,duration_seconds=5.0,
                    source_content_duration_seconds=(end-start)/rate,padding_seconds=padding/rate,
                    start_sample=start,end_sample_exclusive=end,padding_samples=padding,
                    sample_rate_hz=16000,channels=1,encoding='PCM_16',source_interval_rms_dbfs=diagnostics['rms_dbfs'],
                    quality_flags=';'.join(clip_flags),source_sha256=q['sha256'],clip_sha256=sha(dest),
                    source_samples_verified=True,format_verified=True,independent_provenance_verified=False))
                source_result['verified_clips']+=1
            source_result['status']='verified'
        except Exception as exc:
            source_result.update(status='error',error=str(exc))
            errors.append(dict(file_path=source,error=str(exc),action='retained original; inspect any partial outputs'))
        sources.append(source_result)
        if number%100==0: print(f'Prepared and verified {number}/945 sources; {len(clips)} clips',flush=True)
    after=snapshot()
    unchanged=before==after
    if not unchanged: errors.append(dict(file_path='original inputs',error='Input snapshot changed',action='investigate before use'))
    def write_csv(path,data,fields):
        with path.open('x',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader(); writer.writerows(data)
    if clips: write_csv(OUTPUT_ROOT/'metadata.csv',clips,list(clips[0]))
    write_csv(reports/'source_verification.csv',sources,list(sources[0]))
    write_csv(reports/'errors.csv',errors,['file_path','error','action'])
    summary=[]
    for species in sorted(SPECIES):
        ss=[r for r in sources if r['species']==species]; cc=[r for r in clips if r['species']==species]
        summary.append(dict(species=species,original_recordings=len(ss),verified_sources=sum(r['status']=='verified' for r in ss),
            clips=len(cc),padded_clips=sum(r['padding_samples']>0 for r in cc),
            short_recordings=sum(r['shorter_than_five_seconds'] is True for r in ss),
            clips_from_near_silent_sources=sum('near_silent_source' in r['quality_flags'].split(';') for r in cc),
            errors=sum(r['status']=='error' for r in ss)))
    write_csv(reports/'species_clip_summary.csv',summary,list(summary[0]))
    lines=['# Audio preprocessing report','',f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).','',
        f'Original recordings: {len(originals)}. Verified clips: {len(clips)}. Errors: {len(errors)}. Original bird/noise files and metadata unchanged: {unchanged}.','',
        '## Policy and verification','',
        'All sources must decode correctly and be 16 kHz mono PCM-16 WAV. No resampling, normalization or other signal transformation was needed. Non-overlapping source intervals are copied exactly; short sources and incomplete final tails are right-padded with zeros to 80,000 samples. No valid source samples are dropped. Short/tail clips may contain little audio: source content duration and padding are explicit metadata fields, not evidence of a complete five-second call.',
        'start_time_seconds and end_time_seconds refer to actual source audio (exclusive end); duration_seconds is the saved five-second duration including padding. Every generated WAV is reopened and compared sample-for-sample to its parent interval and zeros, and verified for sample rate, channels, frame count and encoding. Parent metadata/folder labels are checked; bird identity itself remains inherited, not verified by listening.',
        'Low-volume and silent intervals are retained and flagged. All unresolved provenance is carried forward. Exact content group IDs and possible similarity component IDs are preserved. Uncertain cross-species candidates are separately flagged from accepted cross-species conflicts. Possible groups are not proof of independence. Exact duplicate sources remain separate outputs with shared group evidence.',
        'Output metadata: birds_audio_prepared/metadata.csv. Source integrity and short recordings: source_verification.csv. Error table has headers only when no errors occur. No train/validation/test split, augmentation, pitch/speed changes or training was performed. No original recording or metadata was modified.','',
        '| Species | Sources | Clips | Padded clips | Short sources | Errors |','|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['species']} | {r['original_recordings']} | {r['clips']} | {r['padded_clips']} | {r['short_recordings']} | {r['errors']} |" for r in summary]
    lines += ['', '## Reproduction','',
        '`python components/audio_classification/src/prepare_audio.py --prepare`',
        'Refuses existing prepared outputs or report directories. Running without --prepare does not process audio. Further splitting requires user approval.']
    (reports/'audio_preprocessing_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (reports/'input_integrity.json').write_text(json.dumps({'unchanged':unchanged,'before':before,'after':after},indent=2),encoding='utf-8')
    print(f'Completed: {len(clips)} verified clips, {len(errors)} errors, originals unchanged={unchanged}',flush=True)
    if errors: raise RuntimeError('Review errors.csv before using prepared outputs')


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Create and verify five-second clips; never split datasets')
    args=parser.parse_args()
    if args.prepare: prepare_dataset()
    else: print('No files processed. Use --prepare for the approved clipping workflow.')
