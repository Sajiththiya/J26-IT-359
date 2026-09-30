"""Seed-42 training-only augmentation with staged publication and immutable inputs."""
import csv
import io
import hashlib
import math
import shutil
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'birds_audio_augmented'
STAGE=BASE/'birds_audio_augmented_staging'
REPORT=BASE/'reports/noise_augmentation'
LEVELS=[('light_noise',20),('medium_noise',10),('heavy_noise',0)]

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def write(p,rows,fields=None):
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or list(rows[0]));w.writeheader();w.writerows(rows)

def noise_read(path):
    method='direct'
    try: stream=sf.SoundFile(path)
    except sf.LibsndfileError:
        data=path.read_bytes(); offset=0; pages=[]; serial=None
        while offset<len(data):
            if data[offset:offset+4]!=b'OggS' or offset+27>len(data):raise ValueError('Invalid Ogg')
            payload=offset+27+data[offset+26]
            end=payload+sum(data[offset+27:payload])
            if end>len(data):raise ValueError('Truncated Ogg')
            sid=data[offset+14:offset+18]
            if data[payload:payload+7]==b'\x01vorbis':
                if serial is not None and serial!=sid:raise ValueError('Multiple Vorbis streams')
                serial=sid
            pages.append((sid,data[offset:end]));offset=end
        if serial is None:raise ValueError('No Vorbis stream')
        stream=sf.SoundFile(io.BytesIO(b''.join(p for s,p in pages if s==serial)));method='in_memory_vorbis_selection'
    with stream as f:
        rate=f.samplerate;channels=f.channels;fmt=f.format;sub=f.subtype
        x=f.read(dtype='float64',always_2d=True).mean(axis=1)
    if not len(x) or not np.isfinite(x).all():raise ValueError('Invalid noise')
    g=math.gcd(rate,16000); x=resample_poly(x,16000//g,rate//g) if rate!=16000 else x
    if len(x)<80000 or not np.any(x):raise ValueError('Noise too short or silent')
    return x,dict(noise_file=path.relative_to(BASE).as_posix(),category=path.parent.name,original_format=fmt,
        original_subtype=sub,original_rate=rate,original_channels=channels,decoded_duration_seconds=len(x)/16000,decoder=method)

def rms(x):return float(np.sqrt(np.mean(x*x)))

def main():
    if any(p.exists() for p in [OUT,STAGE,REPORT]):raise FileExistsError('Output/staging/report already exists; refusing overwrite')
    rows=read(BASE/'reports/final_dataset_split/final_split_assignments.csv')
    assert Counter(r['split'] for r in rows)=={'train':7384,'val':925,'test':924}
    assert len({r['split_file_path'] for r in rows})==9233
    assert {r['split_file_path'] for r in rows}=={p.relative_to(BASE).as_posix() for p in (BASE/'birds_audio_split').rglob('*.wav')}
    for field in ['original_file_path','original_recording_id','final_group_id']:
        groups=defaultdict(set)
        for r in rows:groups[r[field]].add(r['split'])
        assert all(len(v)==1 for v in groups.values()),field
    for p in (BASE/'reports/dataset_audit').glob('*.csv'):read(p)
    (BASE/'reports/final_dataset_split/final_dataset_split_report.md').read_text(encoding='utf-8')
    train=[r for r in rows if r['split']=='train']
    maximum=len(train)*3*160044
    free=shutil.disk_usage(BASE).free
    print(f'Disk preflight: free={free/2**30:.2f} GiB; noisy audio upper bound={maximum/2**30:.2f} GiB; reserve=0.25 GiB',flush=True)
    if free<maximum+268435456:raise RuntimeError('Insufficient space; no audio generated')
    paths=sorted(p for p in (BASE/'Noisy').rglob('*') if p.suffix.lower() in ['.ogg','.mp3','.wav'])
    assert len(paths)==6 and len({p.parent.name for p in paths})==6
    noises=[];noise_info=[]
    for p in paths:
        x,info=noise_read(p);noises.append(x);noise_info.append(info)
        print(f"Noise decoded: {info['category']} ({len(x)/16000:.2f}s)",flush=True)
    tracked=sorted(p for root in ['birds_audio','Noisy','birds_audio_prepared','birds_audio_split','reports'] for p in (BASE/root).rglob('*') if p.is_file())
    def snapshot():
        with ThreadPoolExecutor(max_workers=4) as pool:
            hashes=list(pool.map(sha,tracked))
        return {p:(p.stat().st_size,p.stat().st_mtime_ns,h) for p,h in zip(tracked,hashes)}
    before=snapshot()
    for r in rows:assert before[BASE/r['split_file_path']][2]==r['clip_sha256']
    quality=[]
    for n,r in enumerate(train,1):
        path=BASE/r['split_file_path'];info=sf.info(path);x,rate=sf.read(path,dtype='float64')
        assert (info.format,info.subtype,rate,info.channels,len(x))==('WAV','PCM_16',16000,1,80000)
        valid=int(r['end_sample_exclusive'])-int(r['start_sample']);assert 0<valid<=80000
        assert valid+int(r['padding_samples'])==80000 and not np.any(x[valid:])
        energy=rms(x[:valid]);peak=float(np.max(np.abs(x[:valid])));db=20*np.log10(energy) if energy else -np.inf
        flags=r['quality_flags'].split(';');reasons=[]
        if energy==0:reasons.append('no_measurable_source_signal; never add noise')
        if 0<energy and db < -60:reasons.append('near_silent_source_content; review audibility, not automatically excluded')
        if int(r['padding_samples'])>=40000:reasons.append('at_least_50_percent_padding; review suitability')
        if 0<peak<=2/32768:reasons.append('source_peak_at_most_two_PCM_LSB; unusually low signal review')
        quality.append(dict(clip_path=r['split_file_path'],species=r['species'],original_recording_id=r['original_recording_id'],
            final_group_id=r['final_group_id'],source_content_samples=valid,padding_fraction=int(r['padding_samples'])/80000,
            source_content_rms=energy,source_content_rms_dbfs=db,source_peak=peak,digital_silence=energy==0,
            near_silent=bool(0<energy and db < -60),heavy_padding=int(r['padding_samples'])>=40000,
            recommended_augmentation_eligibility='ineligible_no_signal' if energy==0 else ('review' if reasons else 'eligible_signal_present'),
            augmentation_permitted=energy>0,review_reasons='; '.join(reasons),target_bird_audibility='human_review_required',
            quality_flags=';'.join(flags)))
        if n%2000==0:print(f'Screened {n}/7384 training clips',flush=True)
    print(f'Screening complete: {sum(q["augmentation_permitted"] for q in quality)} measurable clips; starting staged generation',flush=True)
    STAGE.mkdir();species=sorted({r['species'] for r in train})
    for sp in species:
        for variant in ['clean']+[a for a,b in LEVELS]:(STAGE/'train'/sp/variant).mkdir(parents=True)
    rng=np.random.default_rng(42);jobs=[];manifest=[];errors=[]
    def entry(r,q,variant):
        return dict(parent_recording_id=r['original_recording_id'],original_filename=r['original_filename'],
            parent_recording_path=r['original_file_path'],final_recording_group=r['final_group_id'],species=r['species'],split='train',
            original_clean_clip_path=r['split_file_path'],output_path=r['split_file_path'] if variant=='clean' else (OUT/'train'/r['species']/variant/r['clip_filename']).relative_to(BASE).as_posix(),
            augmentation_type=variant,storage_mode='reference' if variant=='clean' else 'generated_wav',noise_category='',noise_file='',noise_offset_samples='',
            noise_offset_seconds='',noise_selected_duration_seconds='',noise_added_duration_seconds='',target_snr_db='',achieved_snr_db='',
            prequantization_snr_db='',noise_gain='',common_final_gain=1,padding_fraction=q['padding_fraction'],
            quality_flags=q['quality_flags'],eligibility_recommendation=q['recommended_augmentation_eligibility'],audibility='human_review_required',
            random_seed=42,source_sha256=r['clip_sha256'],output_sha256=r['clip_sha256'] if variant=='clean' else '',verified=True)
    for r,q in zip(train,quality):
        manifest.append(entry(r,q,'clean'))
        if not q['augmentation_permitted']:
            errors.append(dict(clip_path=r['split_file_path'],augmentation_type='all_noise_levels',status='skipped',reason='digital silence / no measurable source signal; clean reference retained'))
            continue
        for variant,snr in LEVELS:
            k=int(rng.integers(6));offset=int(rng.integers(len(noises[k])-80000+1))
            jobs.append((r,q,variant,snr,k,offset))
    def generate(job):
        r,q,variant,snr,k,offset=job
        x,rate=sf.read(BASE/r['split_file_path'],dtype='float64');valid=q['source_content_samples']
        segment=noises[k][offset:offset+80000]; nr=rms(segment[:valid])
        if nr<=0:raise ValueError('Selected noise segment has zero RMS')
        scale=q['source_content_rms']/(nr*10**(snr/20))
        added=np.zeros(80000);added[:valid]=segment[:valid]*scale
        mixed=x+added;peak=float(np.max(np.abs(mixed)));gain=min(1.,.95/peak) if peak else 1.
        y=mixed*gain; bird=x*gain
        dest=STAGE/'train'/r['species']/variant/r['clip_filename']
        with dest.open('xb') as f:sf.write(f,y,16000,format='WAV',subtype='PCM_16')
        info=sf.info(dest);decoded,rate=sf.read(dest,dtype='float64')
        assert (info.format,info.subtype,rate,info.channels,len(decoded))==('WAV','PCM_16',16000,1,80000)
        assert np.isfinite(decoded).all() and np.max(np.abs(decoded))<1 and not np.any(decoded[valid:])
        assert np.max(np.abs(decoded-y))<=1/32768+1e-12 and np.any(decoded[:valid])
        achieved=20*np.log10(rms(bird[:valid])/rms(decoded[:valid]-bird[:valid]))
        pre=20*np.log10(rms(bird[:valid])/rms(added[:valid]*gain));assert abs(pre-snr)<1e-8
        row=entry(r,q,variant)
        row.update(noise_category=noise_info[k]['category'],noise_file=noise_info[k]['noise_file'],noise_offset_samples=offset,
            noise_offset_seconds=offset/16000,noise_selected_duration_seconds=5.,noise_added_duration_seconds=valid/16000,
            target_snr_db=snr,achieved_snr_db=float(achieved),prequantization_snr_db=float(pre),noise_gain=scale,common_final_gain=gain,output_sha256=sha(dest))
        if abs(achieved-snr)>.5:row['quality_flags']+=';quantization_snr_deviation_over_0.5dB'
        return row
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            for n,row in enumerate(pool.map(generate,jobs),1):
                manifest.append(row)
                if n%2000==0:print(f'Generated and verified {n}/{len(jobs)} noisy WAVs',flush=True)
        for sp in species:
            write(STAGE/'train'/sp/'clean'/'references.csv',[r for r in manifest if r['species']==sp and r['augmentation_type']=='clean'])
        assert len(list(STAGE.rglob('*.wav')))==len(jobs)
        assert all(r['original_clean_clip_path'] in {c['split_file_path'] for c in train} for r in manifest)
        assert snapshot()==before,'Protected input changed'
    except Exception as exc:
        REPORT.mkdir()
        write(REPORT/'augmentation_errors.csv',[dict(clip_path='',augmentation_type='',status='fatal',reason=str(exc))])
        (REPORT/'noise_augmentation_report.md').write_text('FAILED: Final augmented folder was not published. Staging preserved for inspection. Error: '+str(exc),encoding='utf-8')
        raise
    storage=sum(p.stat().st_size for p in STAGE.rglob('*') if p.is_file())
    summary=[]
    for sp in species:
        qq=[q for q in quality if q['species']==sp];rr=[r for r in manifest if r['species']==sp]
        for variant in ['clean']+[v for v,s in LEVELS]:
            selected=[r for r in rr if r['augmentation_type']==variant]
            summary.append(dict(species=sp,augmentation_type=variant,examples=len(selected),training_parent_files=len({r['parent_recording_path'] for r in selected}),
                digital_silent_training_clips=sum(q['digital_silence'] for q in qq),near_silent_training_clips=sum(q['near_silent'] for q in qq),
                heavily_padded_training_clips=sum(q['heavy_padding'] for q in qq),review_recommended_training_clips=sum(q['recommended_augmentation_eligibility']=='review' for q in qq)))
    usage=[]
    for info in noise_info:
        selected=[r for r in manifest if r['noise_file']==info['noise_file']]
        usage.append(dict(info,generated_examples=len(selected),unique_offsets=len({r['noise_offset_samples'] for r in selected}),
            target_rate=16000,target_channels=1,independent_noise_recordings=1))
    REPORT.mkdir();write(REPORT/'training_clip_quality.csv',quality);write(REPORT/'augmentation_manifest.csv',manifest)
    write(REPORT/'augmentation_summary.csv',summary);write(REPORT/'noise_usage_summary.csv',usage)
    write(REPORT/'augmentation_errors.csv',errors,['clip_path','augmentation_type','status','reason'])
    noisy=[r for r in manifest if r['augmentation_type']!='clean'];deviations=[r for r in noisy if abs(r['achieved_snr_db']-r['target_snr_db'])>.5]
    lines=['# Noise-robust training dataset preparation','',f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).','',
        f'Authoritative membership: train 7,384; val 925; test 924. Clean training references: 7,384. Generated noisy WAVs: {len(noisy)}. No-signal clips skipped for augmentation: {len(errors)}; their clean examples remain. Generation failures: 0.',
        f'Dataset storage including reference tables: {storage} bytes ({storage/2**30:.3f} GiB). Preflight free space {free/2**30:.2f} GiB; maximum noisy audio estimate {maximum/2**30:.2f} GiB plus 0.25 GiB reserve.', '',
        '## Quality and eligibility','',
        f"Training digital silence: {sum(q['digital_silence'] for q in quality)}; near-silence below -60 dBFS on non-padded content: {sum(q['near_silent'] for q in quality)}; padding >=50%: {sum(q['heavy_padding'] for q in quality)}.",
        'Fully silent/no-measurable-signal clips are never augmented. Quiet and heavily padded clips remain measurable-signal candidates and receive noisy versions with review flags; recommended eligibility is review rather than automatic exclusion. Peaks at most two PCM LSB are separately flagged as unusually low. All target-bird audibility requires human review: energy detection does not establish bird presence. No recording or clip was removed.', '',
        '## Mixing and reproducibility','',
        'Seed 42, NumPy default_rng; random category and integer sample offset selected in authoritative training row order for light/medium/heavy levels. Category and offset selection is serial and deterministic; parallel writes do not affect random choices. Noise decoded and converted to 16 kHz mono in memory only; multiplexed Rain Ogg uses existing Vorbis pages. Noise sample offsets refer to the decoded/resampled stream, seconds to its timeline.',
        'RMS-based levels: 20/10/0 dB. Signal and noise RMS use only the actual source-content samples, excluding zero padding. Noise is added only to this same region; padding remains zero. Noise gain = signal RMS / (noise RMS * 10^(SNR/20)). If the mixture peak exceeds 0.95, one common gain scales both bird and noise. Source audio is never overwritten.',
        'Every output is reopened and checked for 80,000 samples, 16 kHz mono PCM-16, finite/nonzero content, preserved zero padding and quantization error <= one PCM LSB. Prequantization SNR is verified against target. Achieved SNR after saving treats decoded output minus the gain-scaled bird as effective noise, including quantization error.',
        f'Post-PCM SNR deviations >0.5 dB: {len(deviations)}. These remain flagged in the manifest, not hidden or automatically removed. Very low-energy clips are sensitive to 16-bit quantization.', '',
        f'Maximum saved-audio SNR deviation: {max(abs(r["achieved_snr_db"]-r["target_snr_db"]) for r in noisy):.6f} dB. Flagged examples require review before claiming target-SNR compliance or use in SNR-controlled experiments. Effective noise includes PCM quantization.', '',
        '## Clean references and protection','',
        'birds_audio_augmented/train/<species>/clean/references.csv references existing clean training WAVs; no redundant clean audio copies. Paths are relative to the component directory. Clean reference hashes match authoritative assignment hashes. No validation/test waveform was used to estimate mixing parameters; they were only hashed for integrity. Validation and test stay in birds_audio_split/val and test. No noisy test outputs were made.',
        'Original bird, prepared, split, noise files, metadata and prior reports were hashed before/after and remained unchanged. Parent and final group membership checks passed. All generated examples derive only from training membership. Each measurable training clip has exactly three noisy versions.',
        'There is only one original noise recording in each category. Reusing these recordings for future noisy testing would not demonstrate independent-noise evaluation. Augmented example counts are not independent bird recordings: the training sources remain 755 parent files with unresolved original-event provenance.', '',
        '| Species | Type | Examples |','|---|---|---:|']
    lines += [f"| {r['species']} | {r['augmentation_type']} | {r['examples']} |" for r in summary]
    lines += ['', 'Script: `python components/audio_classification/src/augment_training_audio.py`. Refuses existing output/report/staging directories. Staging is published only after verification. No model training, Git operations, relabeling or previous-file changes. Stop pending approval before model training.']
    (REPORT/'noise_augmentation_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    STAGE.rename(OUT)
    print(f'COMPLETE: clean references={len(train)}, noisy={len(noisy)}, skipped parents/clips={len(errors)}, SNR review={len(deviations)}, storage GiB={storage/2**30:.3f}',flush=True)

if __name__=='__main__':main()
