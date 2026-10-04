"""Create the approved Colab folder and ZIP in one invocation; never overwrite."""
import csv
import hashlib
import io
import json
import shutil
import zipfile
from pathlib import Path
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import soundfile as sf

BASE=Path(__file__).resolve().parents[1]
FINAL=BASE/'colab_training_package'
ZIP=BASE/'colab_training_package.zip'
STAGE=BASE/'colab_training_package_staging'
ZIP_STAGE=BASE/'colab_training_package.zip.partial'

def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def write(p,rows):
    with p.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    if any(p.exists() for p in [FINAL,ZIP,STAGE,ZIP_STAGE]):raise FileExistsError('Refusing to overwrite package, ZIP or staging')
    reports=BASE/'reports'
    manifest=read(reports/'noise_augmentation/augmentation_manifest.csv')
    quality={r['clip_path']:r for r in read(reports/'noise_augmentation/training_clip_quality.csv')}
    assignments=read(reports/'final_dataset_split/final_split_assignments.csv')
    bypath={r['split_file_path']:r for r in assignments}
    species=sorted({r['species'] for r in assignments})
    assert len(species)==10 and 'Yellow-fronted_Barbet' in species and 'Ashy-headed_Laughingthrush' not in species
    labels={s:i for i,s in enumerate(species)}
    for key in ['final_group_id','original_file_path','original_recording_id']:
        groups=defaultdict(set)
        for r in assignments:groups[r[key]].add(r['split'])
        assert all(len(v)==1 for v in groups.values()),key
    review=reports/'noise_augmentation/final_quality_review.md'
    review.read_text(encoding='utf-8')
    selection=[];rows={'train':[],'val':[],'test':[]};jobs=[]
    def record(a,split,variant,path,snr='',target='',error='',flags='',energy='',audibility='human_review_required'):
        return dict(audio_path=path,species=a['species'],label=labels[a['species']],split=split,
            original_filename=a['original_filename'],parent_recording_id=a['original_recording_id'],final_group_id=a['final_group_id'],
            augmentation_level=variant,achieved_snr_db=snr,target_snr_db=target,snr_error_db=error,
            padding_fraction=float(a['padding_samples'])/80000,source_content_duration_seconds=a['source_content_duration_seconds'],
            source_content_rms_dbfs=energy,quality_flags=flags or a['quality_flags'],audibility_review_status=audibility,
            sha256='',sample_rate_hz=16000,channels=1,encoding='PCM_16',duration_seconds=5)
    for r in manifest:
        a=bypath[r['original_clean_clip_path']];assert a['split']=='train'
        q=quality[r['original_clean_clip_path']];variant=r['augmentation_type'];clean=variant=='clean'
        assert r['species']==a['species'] and r['parent_recording_id']==a['original_recording_id'] and r['final_recording_group']==a['final_group_id']
        delta='' if clean else float(r['achieved_snr_db'])-float(r['target_snr_db'])
        reason='included_by_approved_policy';include=True
        if clean and q['digital_silence']=='True':include=False;reason='excluded_digital_silence'
        elif not clean and abs(delta)>.5:include=False;reason='excluded_saved_snr_deviation_gt_0.5dB'
        relative=f"train/{a['species']}/{variant}/{a['clip_filename']}" if include else ''
        flags=r['quality_flags']
        if q['near_silent']=='True':flags+=';near_silent_content_review'
        if q['heavy_padding']=='True':flags+=';heavy_padding_review'
        flags+=';audibility_human_review_required'
        item=record(a,'train',variant,relative,r['achieved_snr_db'],r['target_snr_db'],delta,flags,q['source_content_rms_dbfs'])
        item['sha256']=r['output_sha256']
        # Excluded rows intentionally have no audio_path: there is no packaged WAV.
        # Filename/parent IDs and hashes preserve traceability without external paths.
        selection.append(dict(item,included=include,selection_reason=reason,clip_filename=a['clip_filename']))
        if include:
            rows['train'].append(item);jobs.append((BASE/r['output_path'],relative,r['output_sha256']))
    for a in assignments:
        if a['split']=='train':continue
        split=a['split'];relative=f"{split}/{a['species']}/{a['clip_filename']}"
        item=record(a,split,'clean',relative,energy=a['source_interval_rms_dbfs'])
        item['sha256']=a['clip_sha256'];rows[split].append(item);jobs.append((BASE/a['split_file_path'],relative,a['clip_sha256']))
    assert {s:len(v) for s,v in rows.items()}=={'train':29402,'val':925,'test':924}
    assert len(selection)==29524 and sum(not r['included'] for r in selection)==122
    assert Counter(r['augmentation_level'] for r in rows['train'])=={'clean':7380,'light_noise':7303,'medium_noise':7345,'heavy_noise':7374}
    assert len({r for p,r,h in jobs})==len(jobs)==31251
    groups=defaultdict(set)
    for split,items in rows.items():
        for item in items:groups[item['final_group_id']].add(split)
    assert all(len(s)==1 for s in groups.values())
    for src,relative,h in jobs:assert src.is_file() and not Path(relative).is_absolute() and '..' not in Path(relative).parts
    audio_bytes=sum(src.stat().st_size for src,relative,h in jobs)
    # Budget two full uncompressed copies, plus CSV/ZIP overhead and spare space.
    required=2*audio_bytes+512*1024**2;free=shutil.disk_usage(BASE).free
    print(f'Preflight: {len(jobs)} WAVs; audio {audio_bytes/2**30:.3f} GiB; conservative folder+ZIP need {required/2**30:.3f} GiB; free {free/2**30:.3f} GiB',flush=True)
    if free<required:raise RuntimeError('Insufficient disk space; no package audio created')
    protected=sorted(p for root in ['birds_audio','Noisy','birds_audio_prepared','birds_audio_split','birds_audio_augmented','reports'] for p in (BASE/root).rglob('*') if p.is_file())
    before={p:(p.stat().st_size,p.stat().st_mtime_ns) for p in protected}
    meta_paths=[reports/'noise_augmentation/augmentation_manifest.csv',reports/'noise_augmentation/training_clip_quality.csv',reports/'final_dataset_split/final_split_assignments.csv',review]
    metahashes={p:sha(p) for p in meta_paths}
    STAGE.mkdir()
    for s in species:
        for v in ['clean','light_noise','medium_noise','heavy_noise']:(STAGE/'train'/s/v).mkdir(parents=True)
        for split in ['val','test']:(STAGE/split/s).mkdir(parents=True)
    def copy(job):
        src,relative,expected=job;data=src.read_bytes()
        assert hashlib.sha256(data).hexdigest()==expected,f'Source changed: {src}'
        with sf.SoundFile(io.BytesIO(data)) as f:
            assert (f.format,f.samplerate,f.channels,f.subtype,f.frames)==('WAV',16000,1,'PCM_16',80000)
            assert len(f.read(dtype='int16'))==80000
        dest=STAGE/relative
        with dest.open('xb') as f:f.write(data)
        assert sha(dest)==expected
    with ThreadPoolExecutor(max_workers=4) as pool:
        for n,_ in enumerate(pool.map(copy,jobs),1):
            if n%4000==0:print(f'Copied, decoded and hash-verified {n}/{len(jobs)}',flush=True)
    for split in rows:write(STAGE/f'{split}.csv',rows[split])
    write(STAGE/'training_selection.csv',selection)
    with (STAGE/'label_mapping.json').open('x',encoding='utf-8') as f:
        json.dump({'label2id':labels,'id2label':{str(i):s for s,i in labels.items()}},f,indent=2)
    # Preserve the source review verbatim as a document, not as a loading manifest.
    shutil.copyfile(review,STAGE/'quality_review.md')
    details=['# Component 02 Colab training package','',
        'This package contains actual WAVs, including clean training audio. Resolve every nonempty audio_path in the CSV files relative to this directory. Do not resolve paths relative to the CSV filename or current notebook directory.',
        'train.csv: 29,402 examples (7,380 clean + 22,022 noisy). val.csv: 925 clean clips. test.csv: 924 clean clips. All are 16 kHz mono PCM-16, five seconds.',
        'training_selection.csv records all 29,524 candidate training examples, including 122 exclusions (4 silent clean and 118 noisy SNR warnings). Excluded rows intentionally have an empty audio_path; filter included=True before loading. Their filename, species, variant, parent IDs and hash preserve traceability. No excluded audio is packaged.',
        'Use label_mapping.json for the same integer labels in Wav2Vec2 and AST. Labels are the sorted finalized species names. Use the feature extractor appropriate to the selected checkpoint; this package does not train or install models.',
        'The authoritative split is preserved. Never randomly split CSV rows. No final recording group crosses train/val/test. Low-energy, heavy-padding, audibility-review and provenance flags remain; inclusion is not a claim that target-bird audibility or field-recording independence is verified.',
        'The historical quality_review.md is copied verbatim for evidence and contains original-project paths and pre-selection recommendations. Its statements about unmodified manifests refer to the original review; this package applies the subsequently approved selection policy. Use the package CSVs to load audio.',
        'Only clean validation/test audio is provided. Six single-source noise categories do not establish independent-noise evaluation. Augmented examples are not independent original recordings.', '',
        f'Preflight estimated folder+ZIP requirement including reserve: {required/2**30:.3f} GiB; available: {free/2**30:.3f} GiB.', '',
        '| Species | Train | Val | Test |','|---|---:|---:|---:|']
    details += [f"| {s} | {sum(r['species']==s for r in rows['train'])} | {sum(r['species']==s for r in rows['val'])} | {sum(r['species']==s for r in rows['test'])} |" for s in species]
    (STAGE/'README.md').write_text('\n'.join(details)+'\n',encoding='utf-8')
    expected_wavs={relative for src,relative,h in jobs}
    assert {p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*.wav')}==expected_wavs
    for split in rows:
        assert all((STAGE/r['audio_path']).is_file() for r in read(STAGE/f'{split}.csv'))
    print('Folder validation passed; creating ZIP',flush=True)
    files=sorted(p for p in STAGE.rglob('*') if p.is_file())
    with zipfile.ZipFile(ZIP_STAGE,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for n,p in enumerate(files,1):
            z.write(p,'colab_training_package/'+p.relative_to(STAGE).as_posix())
            if n%6000==0:print(f'Archived {n}/{len(files)} files',flush=True)
    print('Verifying ZIP CRC, manifest paths and archived WAV hashes',flush=True)
    with zipfile.ZipFile(ZIP_STAGE) as z:
        assert z.testzip() is None,'ZIP CRC failure'
        names=z.namelist();assert len(names)==len(set(names))==len(files)
        prefix='colab_training_package/'
        assert {n[len(prefix):] for n in names if n.endswith('.wav')}==expected_wavs
        archived=[]
        for split in rows:
            with z.open(prefix+split+'.csv') as raw:
                parsed=list(csv.DictReader(io.TextIOWrapper(raw,encoding='utf-8')))
            assert len(parsed)==len(rows[split]);archived+=parsed
        assert all(prefix+r['audio_path'] in names for r in archived)
        for n,r in enumerate(archived,1):
            assert hashlib.sha256(z.read(prefix+r['audio_path'])).hexdigest()==r['sha256']
            if n%8000==0:print(f'Verified archived WAV hashes {n}/{len(archived)}',flush=True)
        for name in ['training_selection.csv','label_mapping.json','quality_review.md','README.md']:assert prefix+name in names
    assert all((p.stat().st_size,p.stat().st_mtime_ns)==v for p,v in before.items())
    assert all(sha(p)==h for p,h in metahashes.items())
    # Publish only completely verified outputs. Failures leave clearly named staging.
    STAGE.rename(FINAL);ZIP_STAGE.rename(ZIP)
    print(f'COMPLETE ZIP bytes={ZIP.stat().st_size}; GiB={ZIP.stat().st_size/2**30:.3f}; WAVs=31251; train=29402; val=925; test=924',flush=True)

if __name__=='__main__':main()
