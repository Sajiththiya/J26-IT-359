"""Seed-42 precautionary group split; validate before staging byte-identical copies."""
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import shutil
import numpy as np
import soundfile as sf

BASE=Path(__file__).resolve().parents[1]
REPORT=BASE/'reports/final_dataset_split'
DEST=BASE/'birds_audio_split'
STAGE=BASE/'birds_audio_split_staging'
SPLITS=['train','val','test']


def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()


def write(name,rows):
    with (REPORT/name).open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    if any(p.exists() for p in [REPORT,DEST,STAGE]): raise FileExistsError('Refusing to overwrite final outputs or staging')
    prior=[]
    for folder in ['dataset_split_review','recording_similarity','data_quality']:
        for p in sorted((BASE/'reports'/folder).glob('*')):
            if p.is_file():
                if p.suffix=='.csv': read(p)
                else: p.read_bytes()
                prior.append((p,sha(p)))
    metadata=read(BASE/'birds_audio_prepared/metadata.csv')
    proposed=read(BASE/'reports/dataset_split_review/proposed_split_assignments.csv')
    previous_audit=read(BASE/'reports/dataset_split_review/split_leakage_audit.csv')
    pairs=read(BASE/'reports/recording_similarity/similarity_pairs.csv')
    originals=read(BASE/'birds_audio/metadata.csv'); sources={r['file_path']:r for r in originals}
    species=sorted({r['species'] for r in originals})
    tracked=sorted(p for root in ['birds_audio','Noisy','birds_audio_prepared'] for p in (BASE/root).rglob('*') if p.is_file())
    before={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in tracked}
    assert len(metadata)==9233 and len(sources)==945 and len(species)==10
    old={r['clip_file_path']:r for r in proposed}; assert len(old)==len(metadata)
    parent={s:s for s in sources}
    def find(s):
        if parent[s]!=s: parent[s]=find(parent[s])
        return parent[s]
    def union(a,b): parent[find(b)]=find(a)
    bysource=defaultdict(list)
    seen=defaultdict(dict)
    previous_split={}
    for c in metadata:
        prior_row=old[c['clip_file_path']]
        assert all(prior_row[k]==v for k,v in c.items())
        s=c['original_file_path']; bysource[s].append(c); previous_split[s]=prior_row['proposed_split']
        for field,value in [('prior_group',prior_row['proposed_group_id']),('original_id',c['original_recording_id']),('content',c['exact_content_group_id'])]:
            if value in seen[field]: union(s,seen[field][value])
            seen[field][value]=s
    assert set(bysource)==set(sources)
    risk_pairs={(r['recording_or_clip_a'],r['recording_or_clip_b']) for r in previous_audit if r['check']=='uncertain_similarity' and r['status']=='RISK'}
    assert len(risk_pairs)==21
    decisions=[]
    for p in pairs:
        a,b=p['file_a'],p['file_b']; union(a,b)
        precaution=p['classification']=='uncertain_similarity'
        offset=float(p['offset_b_minus_a_seconds'])
        intervals=[]
        for interval in p['tested_intervals_a'].split(';'):
            if interval:
                lo,hi=map(float,interval.split('-')); intervals.append(f'{lo+offset:.3f}-{hi+offset:.3f}')
        decisions.append(dict(p,decision='precautionary_coallocation_not_identity' if precaution else ('confirmed_content_link' if p['classification']=='confirmed_exact_duplicate' else 'probable_acoustic_link_not_human_verified'),
            was_cross_split_uncertain=(a,b) in risk_pairs,previous_split_a=previous_split[a],previous_split_b=previous_split[b],
            tested_intervals_b=';'.join(intervals),human_verified=False,
            interpretation='Evidence insufficient to confirm duplicate; coallocate only' if precaution else 'Preserve existing evidence classification'))
    # Validate prepared audio and original content before any copy operation.
    for n,(s,cc) in enumerate(bysource.items(),1):
        original,rate=sf.read(BASE/s,dtype='int16',always_2d=True); assert rate==16000 and original.shape[1]==1
        previous=0
        for c in sorted(cc,key=lambda r:int(r['clip_index'])):
            path=BASE/c['clip_file_path']; info=sf.info(path); x,r=sf.read(path,dtype='int16')
            assert (info.format,info.subtype,r,info.channels,len(x))==('WAV','PCM_16',16000,1,80000)
            assert before[path][2]==c['clip_sha256'] and before[BASE/s][2]==c['source_sha256']
            assert c['species']==sources[s]['species']==path.parent.name
            assert c['original_recording_id']==sources[s]['original_recording_id']
            start,end,padding=map(int,[c['start_sample'],c['end_sample_exclusive'],c['padding_samples']])
            assert start==previous and end-start+padding==80000
            assert np.array_equal(x[:end-start],original[start:end,0]) and not np.any(x[end-start:])
            previous=end
        assert previous==len(original)
        if n%200==0: print(f'Validated {n}/945 parents before allocation',flush=True)
    components=defaultdict(list)
    for s in sorted(sources): components[find(s)].append(s)
    members=sorted(components.values(),key=lambda v:v[0]); gids=['final_'+hashlib.sha256('|'.join(v).encode()).hexdigest()[:16] for v in members]
    source_group={s:g for g,ss in zip(gids,members) for s in ss}
    # Multi-species components require joint allocation; keep labels separate.
    weights=np.zeros((len(members),21))
    for i,ss in enumerate(members):
        for s in ss:
            k=species.index(sources[s]['species']); weights[i,k]+=len(bysource[s]); weights[i,10+k]+=1
        weights[i,20]=1
    target=np.array([.8,.1,.1])[:,None]*weights.sum(axis=0)
    scale=1/np.maximum(target,1)**2; scale[:,20]*=2
    rng=np.random.default_rng(42); best=None
    for trial in range(30):
        order=np.argsort(-(weights[:,:10].sum(axis=1)*(1+rng.uniform(0,.3,len(members)))))
        allocation=np.full(len(members),-1); totals=np.zeros((3,21))
        for i in order:
            changes=np.sum(((totals+weights[i]-target)**2-(totals-target)**2)*scale,axis=1)
            k=int(np.argmin(changes)); allocation[i]=k; totals[k]+=weights[i]
        for iteration in range(5):
            moved=False
            for i in rng.permutation(len(members)):
                a=allocation[i]; cost=float(np.sum((totals-target)**2*scale)); chosen=a
                for b in range(3):
                    if b==a: continue
                    trial_tot=totals.copy(); trial_tot[a]-=weights[i]; trial_tot[b]+=weights[i]
                    value=float(np.sum((trial_tot-target)**2*scale))
                    if value<cost-1e-12: cost=value; chosen=b
                if chosen!=a:
                    totals[a]-=weights[i]; totals[chosen]+=weights[i]; allocation[i]=chosen; moved=True
            if not moved: break
        loss=float(np.sum((totals-target)**2*scale))
        if best is None or loss<best[0]: best=(loss,allocation.copy(),totals.copy())
    group_split={g:SPLITS[int(k)] for g,k in zip(gids,best[1])}
    source_split={s:group_split[source_group[s]] for s in sources}
    assert np.all(best[2][:,:20]>0),'A species is missing from a split'
    checks=[]
    def check(kind,a,b='',detail=''):
        passed=not b or source_split[a]==source_split[b]
        checks.append(dict(check=kind,source_a=a,source_b=b,status='PASS' if passed else 'FAIL',detail=detail))
        assert passed,(kind,a,b)
    for s in sources: check('parent_one_split',s,detail=source_split[s])
    for d in decisions:
        a,b=d['file_a'],d['file_b']; check(d['classification'],a,b)
        d.update(final_group_id=source_group[a],final_split=source_split[a])
    for r in previous_audit:
        if r['check']=='identical_nonsilent_clip_parent_link': check(r['check'],r['recording_or_clip_a'],r['recording_or_clip_b'])
    for field in ['proposed_group_id','recording_group_id','exact_content_group_id','original_recording_id']:
        buckets=defaultdict(set)
        for c in proposed: buckets[c[field]].add(source_split[c['original_file_path']])
        assert all(len(v)==1 for v in buckets.values()),field
        checks.append(dict(check=field+'_one_split',source_a='',source_b='',status='PASS',detail=f'{len(buckets)} groups checked'))
    final=[]; destinations=set()
    for c in metadata:
        s=c['original_file_path']; split=source_split[s]
        destination=Path(split)/c['species']/c['clip_filename']
        assert str(destination) not in destinations; destinations.add(str(destination))
        final.append(dict(c,final_group_id=source_group[s],split=split,split_file_path=(Path('birds_audio_split')/destination).as_posix(),
            grouping_human_verified=False,provenance_status='unresolved',seed=42))
    assert len(final)==9233 and len(destinations)==9233
    assert {r['clip_file_path'] for r in final}=={p.relative_to(BASE).as_posix() for p in (BASE/'birds_audio_prepared').rglob('*.wav')}
    required=sum(before[BASE/c['clip_file_path']][0] for c in final)
    assert shutil.disk_usage(BASE).free>required+100_000_000,'Insufficient disk space'
    print('All pre-copy checks passed; copying to temporary staging directory',flush=True)
    STAGE.mkdir()
    try:
        for split in SPLITS:
            for sp in species: (STAGE/split/sp).mkdir(parents=True)
        for n,c in enumerate(final,1):
            src=BASE/c['clip_file_path']; dest=STAGE/c['split']/c['species']/c['clip_filename']
            with src.open('rb') as inp,dest.open('xb') as out: shutil.copyfileobj(inp,out)
            assert sha(dest)==c['clip_sha256'],f'Copy verification failed: {dest}'
            if n%2000==0: print(f'Copied and hash-verified {n}/9233 clips',flush=True)
        assert len(list(STAGE.rglob('*.wav')))==9233
        after={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in tracked}
        assert before==after and all(sha(p)==h for p,h in prior),'Input changed'
        assert {p.relative_to(STAGE).as_posix() for p in STAGE.rglob('*.wav')}=={Path(c['split_file_path']).relative_to('birds_audio_split').as_posix() for c in final}
    except Exception:
        # Never publish a partial final dataset; preserve staging for inspection.
        raise RuntimeError('Validation/copy failed. Final folder NOT created; inspect staging before retry.')
    STAGE.rename(DEST)
    REPORT.mkdir()
    checks += [dict(check=k,source_a='',source_b='',status='PASS',detail=v) for k,v in [
        ('copy_hash_verification','9233 copies byte-identical to prepared sources'),('coverage','Every prepared clip appears exactly once'),
        ('input_integrity','Original/prepared audio, metadata and prior reports unchanged'),('labels_preserved','All original species names and IDs retained')]]
    cross=[dict(d,possible_species_label_conflict=True,label_changed=False,review_status='unresolved; precautionary allocation only') for d in decisions if d['cross_species']=='True']
    assert len(cross)==44
    summary=[]
    for sp in species+['ALL_SPECIES']:
        for split in SPLITS:
            cc=[c for c in final if c['split']==split and (sp=='ALL_SPECIES' or c['species']==sp)]
            denominator=sum(sp=='ALL_SPECIES' or c['species']==sp for c in final)
            summary.append(dict(species=sp,split=split,original_recordings=len({c['original_file_path'] for c in cc}),
                groups_represented=len({c['final_group_id'] for c in cc}),clips=len(cc),clip_percentage=100*len(cc)/denominator))
    write('final_split_assignments.csv',final); write('recording_group_decisions.csv',decisions)
    write('cross_species_review.csv',cross); write('final_split_leakage_audit.csv',checks); write('final_split_summary.csv',summary)
    lines=['# Final dataset splitting and similarity risk resolution','',f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).','',
        '**Automated grouping and copy checks passed. This is not proof of leakage-free independent field recordings.** Species labels and original IDs remain unchanged; no human identity verification is claimed.','',
        '## Evidence and grouping decisions','',
        'Read prior prepared metadata, proposed assignments, leakage audit and all top-level similarity/data-quality reports. All 21 previously crossing uncertain pairs are identified in recording_group_decisions.csv (was_cross_split_uncertain=True), including seven cross-species pairs. Their prior waveform correlations, fingerprint votes, offsets and tested A intervals are preserved, with corresponding B intervals computed from the offset. These existing measurements were reviewed; no new acoustic identity claim or human listening is made.',
        'Keep the 11 exact-content pairs and 51 probable acoustic pairs at their original evidence levels. Coallocate ALL 71 uncertain pairs precautionarily, not just the previous 21 crossings, so the rebuilt split cannot introduce crossings among previously within-split candidates. The 44 cross-species uncertain candidates are all listed in cross_species_review.csv as possible label conflicts; none is relabeled or classified as a confirmed duplicate.',
        'Prior review groups (including additional exact decoded non-silent clip links) and declared recording IDs remain indivisible. Transitive precautionary components may contain several species: files keep their own species folders and labels. An entire component shares one split. Uncertain similarities can reflect common calls/backgrounds, so conservative grouping sacrifices allocation flexibility without resolving identity.',
        f'Final components: {len(members)}; multi-species components: {sum(len({sources[s]["species"] for s in ss})>1 for ss in members)}. Evidence decisions are pair-level; final_split_assignments.csv carries every parent’s final component.','',
        '## Allocation method','',
        'Seed 42; NumPy default_rng. Thirty deterministic randomized greedy allocations followed by up to five whole-group local-move passes. Joint objective is squared relative deviation from 80/10/10 per-species clip counts, per-species parent counts, and global group counts (group term weight 2). Select the lowest objective. This supports multi-species groups and does not use model outcomes. Unequal group sizes and cross-species components prevent exact proportions; no clip or parent is removed to improve balance.',
        'Group counts per species count components represented in that species and therefore cannot be summed across species for multi-species groups. ALL_SPECIES rows count unique groups.','',
        '| Species | Split | Parent recordings | Groups represented | Clips | Clip percent |','|---|---|---:|---:|---:|---:|']
    lines += [f"| {r['species']} | {r['split']} | {r['original_recordings']} | {r['groups_represented']} | {r['clips']} | {r['clip_percentage']:.2f}% |" for r in summary]
    lines += ['', '## Validation and retained limitations','',
        'All 945 original parents and 9,233 clips retained. Every parent, prior group, exact-content group, probable pair and precautionary pair occurs in one split. Each clip was decoded before allocation, checked against its parent and padding, and its copied bytes verified by SHA-256. All copies were staged and validated before publishing birds_audio_split/. Original/prepared files and prior metadata/reports remained unchanged.',
        'No known exact/probable/precautionary pair crosses boundaries. Unknown source provenance remains for all originals; unobserved overlap or common field sessions can still cause leakage. Conservative grouping resolves allocation risks, not source identity. All four silent clips, near-silent and heavily padded clips and duplicate material remain. Padding and quality flags are carried forward. Silent content is not evidence of common origin.',
        'Copies are organized under birds_audio_split/train, val and test with the same ten species names and clip filenames. No augmentation, relabeling, training or Git operations occurred.', '',
        '## Reproduce','', '`python components/audio_classification/src/finalize_dataset_split.py`',
        'Requires absent output, report and staging directories; refuses overwrites. Any preflight failure prevents copying; copy/check failure prevents publication of a final folder. Wait for user approval before noise augmentation.']
    (REPORT/'final_dataset_split_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('COMPLETE '+str([r for r in summary if r['species']=='ALL_SPECIES']),flush=True)


if __name__=='__main__': main()
