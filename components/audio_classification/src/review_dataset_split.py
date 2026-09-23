"""Read-only seed-42 group split proposal and clip verification. No final splits."""
import csv
import hashlib
import json
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timezone
import numpy as np
import soundfile as sf

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'reports/dataset_split_review'
SPLITS=['train','validation','test']
RATIOS=np.array([.8,.1,.1])


def read(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''): h.update(b)
    return h.hexdigest()


def main():
    if OUT.exists(): raise FileExistsError('Refusing to overwrite split review')
    prior=[]
    for folder in ['audio_preprocessing','recording_similarity','data_quality']:
        for p in sorted((BASE/'reports'/folder).iterdir()):
            if p.is_file():
                if p.suffix=='.csv': read(p)
                elif p.suffix=='.json': json.loads(p.read_text(encoding='utf-8'))
                else: p.read_bytes()
                prior.append((p,sha(p)))
    clips=read(BASE/'birds_audio_prepared/metadata.csv')
    originals=read(BASE/'birds_audio/metadata.csv')
    source_meta={r['file_path']:r for r in originals}
    oldgroups={r['file_path']:r for r in read(BASE/'reports/recording_similarity/possible_recording_groups.csv')}
    pairs=read(BASE/'reports/recording_similarity/similarity_pairs.csv')
    identities={r['file_path']:r for r in read(BASE/'reports/data_quality/recording_identity_review.csv')}
    tracked=sorted(p for root in ['birds_audio','Noisy','birds_audio_prepared'] for p in (BASE/root).rglob('*') if p.is_file())
    before={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in tracked}
    assert len(clips)==9233 and len(originals)==945
    assert len({c['clip_file_path'] for c in clips})==9233
    assert {c['clip_file_path'] for c in clips}=={p.relative_to(BASE).as_posix() for p in (BASE/'birds_audio_prepared').rglob('*.wav')}
    parent={s:s for s in source_meta}
    def find(s):
        if parent[s]!=s: parent[s]=find(parent[s])
        return parent[s]
    def union(a,b): parent[find(b)]=find(a)
    # Shared IDs, declared source paths and earlier component IDs all constrain grouping.
    for field in ['original_recording_id','source']:
        seen={}
        for s,r in source_meta.items():
            if r[field] in seen: union(s,seen[r[field]])
            seen[r[field]]=s
    for mapping,field in [(oldgroups,'possible_group_id'),(identities,'content_group_id')]:
        seen={}
        for s,r in mapping.items():
            if r[field] in seen: union(s,seen[r[field]])
            seen[r[field]]=s
    for p in pairs:
        if p['classification'] in ['confirmed_exact_duplicate','probable_acoustic_match']: union(p['file_a'],p['file_b'])
    bysource=defaultdict(list)
    for c in clips: bysource[c['original_file_path']].append(c)
    assert set(bysource)==set(source_meta)
    pcm_groups=defaultdict(list)
    for n,(s,rows) in enumerate(bysource.items(),1):
        original=BASE/s; source,sr=sf.read(original,dtype='int16',always_2d=True)
        assert sr==16000 and source.shape[1]==1
        rows.sort(key=lambda r:int(r['clip_index'])); previous=0
        for c in rows:
            p=BASE/c['clip_file_path']; info=sf.info(p); x,rate=sf.read(p,dtype='int16')
            assert (info.format,info.subtype,rate,info.channels,len(x))==('WAV','PCM_16',16000,1,80000)
            assert before[p][2]==c['clip_sha256'] and before[original][2]==c['source_sha256']
            assert c['species']==source_meta[s]['species']==p.parent.name
            assert c['original_recording_id']==source_meta[s]['original_recording_id']
            assert c['original_filename']==original.name and c['clip_filename']==p.name
            assert c['recording_group_id']==oldgroups[s]['possible_group_id']
            assert c['exact_content_group_id']==identities[s]['content_group_id']
            start,end,pad=map(int,[c['start_sample'],c['end_sample_exclusive'],c['padding_samples']])
            assert start==previous and 0<end-start<=80000 and end-start+pad==80000 and end<=len(source)
            assert np.array_equal(x[:end-start],source[start:end,0]) and not np.any(x[end-start:])
            assert abs(float(c['start_time_seconds'])-start/16000)<1e-9 and abs(float(c['end_time_seconds'])-end/16000)<1e-9
            assert float(c['duration_seconds'])==5 and float(c['padding_seconds'])==pad/16000
            assert float(c['source_content_duration_seconds'])==(end-start)/16000
            previous=end
            y=x.astype('float64')/32768; valid=y[:end-start]
            def db(v):
                rms=float(np.sqrt(np.mean(v*v))); return 20*np.log10(rms) if rms else -np.inf
            full,content=db(y),db(valid)
            c.update(padding_percent=pad/800,heavy_padding=pad>=40000,
                measured_silent=not np.any(x),measured_near_silent=bool(np.any(x) and content < -60),
                full_clip_rms_dbfs=full,source_content_rms_dbfs=content,verification='passed')
            pcm_groups[hashlib.sha256(x.tobytes()).hexdigest()].append(c)
        assert previous==len(source)
        if n%100==0: print(f'Verified {n}/945 sources and their clips',flush=True)
    decoded_links=set()
    for cc in pcm_groups.values():
        if len(cc)>1 and not cc[0]['measured_silent']:
            first=cc[0]['original_file_path']
            for c in cc[1:]:
                other=c['original_file_path']
                if other!=first:
                    union(first,other)
                    decoded_links.add(tuple(sorted((first,other))))
    components=defaultdict(list)
    for s in sorted(source_meta): components[find(s)].append(s)
    group_data={}; source_group={}
    for members in components.values():
        gid='review_'+hashlib.sha256('|'.join(members).encode()).hexdigest()[:16]
        species={source_meta[s]['species'] for s in members}
        if len(species)!=1: raise ValueError('Cross-species accepted component requires review before stratified proposal')
        group_data[gid]=dict(members=members,species=next(iter(species)),clips=sum(len(bysource[s]) for s in members))
        for s in members: source_group[s]=gid
    # Select among reproducible random whole-group assignments; fixed group quotas.
    rng=np.random.default_rng(42); assignments={}
    for species in sorted({r['species'] for r in originals}):
        gids=sorted(g for g,r in group_data.items() if r['species']==species)
        n=len(gids); quotas=np.floor(RATIOS*n).astype(int)
        for k in np.argsort(-(RATIOS*n-quotas),kind='stable')[:n-int(quotas.sum())]: quotas[k]+=1
        weights=np.array([[group_data[g]['clips'],len(group_data[g]['members'])] for g in gids])
        target=RATIOS[:,None]*weights.sum(axis=0); best=None
        for trial in range(2000):
            order=rng.permutation(n); parts=np.split(order,np.cumsum(quotas)[:-1])
            totals=np.array([weights[part].sum(axis=0) for part in parts])
            loss=float(np.sum(((totals-target)/np.maximum(target,1))**2))
            if best is None or loss<best[0]: best=(loss,[part.copy() for part in parts])
        for split,part in zip(SPLITS,best[1]):
            for k in part: assignments[gids[k]]=split
    for c in clips:
        c['proposed_group_id']=source_group[c['original_file_path']]
        c['proposed_split']=assignments[c['proposed_group_id']]
        c['seed']=42
    audit=[]
    def event(check,status,a='',b='',sa='',sb='',detail=''):
        audit.append(dict(check=check,status=status,recording_or_clip_a=a,recording_or_clip_b=b,
            split_a=sa,split_b=sb,detail=detail))
    source_split={s:assignments[source_group[s]] for s in source_meta}
    for s,cc in bysource.items():
        event('parent_recording_single_split','PASS' if len({c['proposed_split'] for c in cc})==1 else 'FAIL',s,sa=source_split[s])
        event('unknown_provenance','REVIEW',s,sa=source_split[s],detail='Original recording independence unverified')
    for p in pairs:
        a,b=p['file_a'],p['file_b']; sa,sb=source_split[a],source_split[b]
        uncertain=p['classification']=='uncertain_similarity'
        event(p['classification'],'RISK' if uncertain and sa!=sb else ('REVIEW' if uncertain else ('PASS' if sa==sb else 'FAIL')),
            a,b,sa,sb,f"cross_species={p['cross_species']}; median_correlation={p['median_abs_correlation']}; offset_seconds={p['offset_b_minus_a_seconds']}")
    for a,b in sorted(decoded_links):
        event('identical_nonsilent_clip_parent_link','PASS' if source_split[a]==source_split[b] else 'FAIL',a,b,source_split[a],source_split[b],
            'New exact decoded non-silent clip evidence; conservatively grouped parents')
    for h,cc in pcm_groups.items():
        if len({c['proposed_split'] for c in cc})>1:
            first=cc[0]
            for c in cc[1:]:
                if c['proposed_split']!=first['proposed_split']:
                    event('identical_decoded_clip_across_splits','RISK',first['clip_file_path'],c['clip_file_path'],first['proposed_split'],c['proposed_split'],
                        f"PCM hash={h}; silent={c['measured_silent']}; silence is not proof of source identity")
    for field in ['recording_group_id','exact_content_group_id','original_recording_id']:
        values=defaultdict(set)
        for c in clips: values[c[field]].add(c['proposed_split'])
        for key,ss in values.items(): event(field+'_single_split','PASS' if len(ss)==1 else 'FAIL',key,sa=';'.join(sorted(ss)))
    group_rows=[]
    for s in sorted(source_meta):
        g=source_group[s]; record=source_meta[s]
        group_rows.append(dict(original_file_path=s,species=record['species'],original_recording_id=record['original_recording_id'],
            proposed_group_id=g,prior_similarity_group_id=oldgroups[s]['possible_group_id'],exact_content_group_id=identities[s]['content_group_id'],
            group_sources=len(group_data[g]['members']),group_clips=group_data[g]['clips'],source_clips=len(bysource[s]),
            proposed_split=source_split[s],unknown_provenance=True,uncertain_edges=oldgroups[s]['uncertain_edges']))
    summary=[]; split_counts=[]
    for species in sorted({c['species'] for c in clips}):
        cc=[c for c in clips if c['species']==species]
        summary.append(dict(species=species,clips=len(cc),padded_clips=sum(float(c['padding_percent'])>0 for c in cc),
            heavily_padded_ge_50_percent=sum(c['heavy_padding'] for c in cc),silent_clips=sum(c['measured_silent'] for c in cc),
            near_silent_nonpadding_content=sum(c['measured_near_silent'] for c in cc),
            near_silent_full_clip=sum(not c['measured_silent'] and c['full_clip_rms_dbfs'] < -60 for c in cc),
            mean_padding_percent=float(np.mean([c['padding_percent'] for c in cc])),max_padding_percent=max(c['padding_percent'] for c in cc)))
        for split in SPLITS:
            selected=[c for c in cc if c['proposed_split']==split]
            split_counts.append(dict(species=species,split=split,recordings=len({c['original_file_path'] for c in selected}),
                groups=len({c['proposed_group_id'] for c in selected}),clips=len(selected),percent_of_species_clips=100*len(selected)/len(cc)))
    after={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in tracked}
    assert before==after and all(sha(p)==h for p,h in prior),'Inputs changed'
    event('input_integrity','PASS',detail='All original, noise, prepared files and existing metadata/reports unchanged')
    event('clip_verification','PASS',detail='9233 decoded WAVs, hashes, parent samples, zero padding, format and contiguous source coverage verified')
    OUT.mkdir()
    def write(name,data):
        with (OUT/name).open('x',encoding='utf-8',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0])); w.writeheader(); w.writerows(data)
    write('clip_quality_summary.csv',summary)
    write('proposed_recording_groups.csv',group_rows)
    write('proposed_split_assignments.csv',clips)
    write('split_leakage_audit.csv',audit)
    risk=[r for r in audit if r['status']=='RISK']; uncertain_cross=[r for r in risk if r['check']=='uncertain_similarity']
    totals=[]
    for split in SPLITS:
        cc=[c for c in clips if c['proposed_split']==split]
        totals.append((split,len({c['proposed_group_id'] for c in cc}),len({c['original_file_path'] for c in cc}),len(cc)))
    lines=['# Dataset split preparation and leakage safety review','',f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).','',
        '**Not safe to finalize as a verified leakage-free split.** This is a proposal only. Accepted source links remain together, but uncertain similarities and unknown provenance require review. No files were moved or excluded.','',
        '## Verification and quality','',
        'All 9,233 clips were decoded, checked for 80,000 samples / 16 kHz / mono / PCM-16 WAV, compared with stored hashes and their original source samples, and checked for exact right-padding. Metadata labels, IDs, group IDs, filenames, times and full non-overlapping source coverage were verified. All 945 parents are covered. Original, noise, prepared audio, metadata and prior reports remained unchanged.',
        'Padding percent = declared padding samples / 80,000 × 100, verified against source boundaries and zero samples. Natural trailing silence is not counted as padding. Heavy padding is defined here as ≥50%. Digital silence means every sample is zero. Near-silence means nonzero RMS below -60 dBFS; source-content RMS excludes padding to avoid conflating padding with quiet calls. Full-clip RMS is also recorded.',
        f"Padded clips: {sum(r['padded_clips'] for r in summary)}; heavily padded: {sum(r['heavily_padded_ge_50_percent'] for r in summary)}; silent: {sum(r['silent_clips'] for r in summary)}; near-silent nonpadding content: {sum(r['near_silent_nonpadding_content'] for r in summary)}.",
        'Per-clip measurements and inherited flags are in proposed_split_assignments.csv; species totals are in clip_quality_summary.csv. All clips, including duplicates and low-quality clips, remain in the proposal.','',
        '## Group construction and allocation','',
        f'Connected components join shared original IDs, historical source paths, prior similarity group IDs, exact-content IDs, all confirmed-exact/probable-acoustic edges, and {len(decoded_links)} parent pairs sharing identical decoded non-silent clips. These extra links prevent exact clip leakage missed by the previous fingerprint search. Silence alone does not join parents. Uncertain edges are flagged but do not merge groups. No cross-species accepted component was present. Singleton groups do not prove recording independence.',
        'Seed 42 (NumPy default_rng). Within each species, allocate integer group quotas by largest remainder for 80/10/10, then evaluate 2,000 reproducible random whole-group allocations. Select the lowest summed squared relative deviation from per-species clip and parent-recording targets. No outcome/model data is used. This heuristic aims for balance, not a mathematical optimum; no group is broken.',
        'Rounding whole-group quotas and unequal recording lengths make exact 80/10/10 clip and parent counts generally impossible. Allocation preserves existing class imbalance; it does not equalize species by removing or duplicating clips.','',
        '| Split | Groups | Parent recordings | Clips | Clip percent |','|---|---:|---:|---:|---:|']
    lines += [f'| {s} | {g} | {p} | {c} | {100*c/len(clips):.2f}% |' for s,g,p,c in totals]
    lines += ['', '| Species | Split | Groups | Parent recordings | Clips | Species clip percent |','|---|---|---:|---:|---:|---:|']
    lines += [f"| {r['species']} | {r['split']} | {r['groups']} | {r['recordings']} | {r['clips']} | {r['percent_of_species_clips']:.2f}% |" for r in split_counts]
    lines += ['', '## Leakage findings and required review','',
        f"Hard constraint failures: {sum(r['status']=='FAIL' for r in audit)}. All 11 exact duplicate pairs and 51 probable acoustic pairs stay together. All parent recordings, prior similarity components, exact-content groups and declared IDs stay in one proposed split.",
        f'Uncertain similarity pairs crossing splits: {len(uncertain_cross)} of 71. All 44 cross-species uncertain candidates remain unresolved regardless of assignment. Unknown source provenance applies to all 945 recordings, so acoustic separation cannot certify independent field sessions.',
        f"Additional identical decoded-clip cross-split risk rows: {sum(r['check']=='identical_decoded_clip_across_splits' for r in risk)}. These are flagged separately; identical silent waveforms do not imply common source provenance.",
        'split_leakage_audit.csv lists each uncertain pair with endpoints, proposed splits, correlation and offset; RISK rows identify cross-split cases. Review them before approval. Recover source URLs/recording events for unresolved parents. If an uncertain link is accepted, regroup and generate a new proposal before finalizing. Review heavy padding and silence for evaluation suitability without automatically excluding anything.', '',
        '| Uncertain pair A | Pair B | Split A | Split B |','|---|---|---|---|']
    lines += [f"| {r['recording_or_clip_a']} | {r['recording_or_clip_b']} | {r['split_a']} | {r['split_b']} |" for r in uncertain_cross]
    lines += ['', '## Reproduce and next step','',
        '`python components/audio_classification/src/review_dataset_split.py`',
        'Refuses to overwrite the review directory. No final train/validation/test folders, augmentation, training or Git operations were performed. Wait for approval and resolution of flagged risks before finalizing.']
    (OUT/'dataset_split_review_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Proposal totals: '+str(totals),flush=True)
    print(f'Cross-split uncertain pairs: {len(uncertain_cross)}; risk rows: {len(risk)}; hard failures: {sum(r["status"]=="FAIL" for r in audit)}',flush=True)


if __name__=='__main__': main()
