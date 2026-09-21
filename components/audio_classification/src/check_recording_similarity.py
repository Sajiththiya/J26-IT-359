"""Read-only acoustic similarity investigation; no prepared audio or splits.

Dependencies: numpy, scipy, soundfile. Refuses to overwrite existing reports.
"""
from pathlib import Path
from collections import defaultdict, Counter
from functools import lru_cache
from itertools import combinations
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
import numpy as np
import scipy
from scipy import signal, ndimage
import soundfile as sf

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'reports/recording_similarity'
RATE, HOP = 8000, 128


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def csvread(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


@lru_cache(maxsize=6)
def audio(path):
    x, rate = sf.read(path, dtype='float32', always_2d=True)
    if not x.size or not np.isfinite(x).all():
        raise ValueError(f'Empty/nonfinite audio: {path}')
    x = x.mean(axis=1)
    g = math.gcd(rate, RATE)
    return signal.resample_poly(x, RATE//g, rate//g).astype('float32') if rate != RATE else x


def fingerprint(x):
    if len(x)<512 or not np.any(x):
        return []
    _, _, z = signal.stft(x, RATE, nperseg=512, noverlap=512-HOP, boundary=None, padded=False)
    db = 20*np.log10(np.maximum(np.abs(z), 1e-12))
    # Local spectral peaks are amplitude-invariant; exclude low-frequency rumble.
    peaks = (db == ndimage.maximum_filter(db, size=(9, 9))) & (db > db.max()-55)
    peaks[:8] = False
    by_time = defaultdict(list)
    for f,t in zip(*np.nonzero(peaks)):
        by_time[int(t)].append((float(db[f,t]),int(f)))
    points = [(t,f) for t, vals in sorted(by_time.items()) for _,f in sorted(vals,reverse=True)[:3]]
    result = set()
    for k,(t,f) in enumerate(points):
        targets=[]
        for next_index in range(k+1,len(points)):
            u,g=points[next_index]
            if u-t>60: break
            if u-t>=4:
                targets.append((u,g))
            if len(targets)>=5: break
        for u,g in targets:
            result.add(((f//2,g//2,(u-t)//2),t))
    return sorted(result)


def verify(a,b,offset):
    # offset means time_B = time_A + offset. Refine on the strongest of 5 anchors.
    start=max(0.,-offset); end=min(len(a)/RATE,len(b)/RATE-offset)
    overlap=end-start
    if overlap<.5: return None
    duration=min(2.,overlap-.05)
    anchors=np.linspace(start+.02,max(start+.02,end-duration-.02),5)
    best=(-1.,offset)
    for t in anchors:
        i=int(t*RATE); template=a[i:i+int(duration*RATE)].astype('float64')
        template-=template.mean(); energy=np.dot(template,template)
        lo=max(0,int((t+offset-.15)*RATE)); hi=min(len(b),int((t+offset+duration+.15)*RATE))
        search=b[lo:hi].astype('float64'); n=len(template)
        if len(search)<n or energy<1e-20: continue
        sums=np.r_[0,np.cumsum(search)]; squares=np.r_[0,np.cumsum(search*search)]
        variance=np.maximum(squares[n:]-squares[:-n]-(sums[n:]-sums[:-n])**2/n,1e-30)
        cc=signal.correlate(search,template,mode='valid',method='fft')/np.sqrt(energy*variance)
        k=int(np.argmax(np.abs(cc))); score=float(abs(cc[k]))
        if score>best[0]: best=(score,(lo+k-i)/RATE)
    offset=best[1]; lag=round(offset*RATE)
    ia=max(0,-lag); ib=max(0,lag); length=min(len(a)-ia,len(b)-ib)
    window=min(2*RATE,length)
    scores=[]; gains=[]; intervals=[]
    # Non-overlapping windows sampled across the aligned extent (up to 10).
    starts=sorted(set(int(v) for v in np.linspace(0,max(0,length-window), min(10,max(1,length//window)))))
    for pos in starts:
        x=a[ia+pos:ia+pos+window].astype('float64'); y=b[ib+pos:ib+pos+window].astype('float64')
        x-=x.mean(); y-=y.mean(); xx=np.dot(x,x); yy=np.dot(y,y)
        score=abs(float(np.dot(x,y)/np.sqrt(xx*yy))) if xx>1e-20 and yy>1e-20 else 0.
        scores.append(min(1.,score)); gains.append(float(np.dot(x,y)/xx) if xx>1e-20 else 0.)
        intervals.append(f'{(ia+pos)/RATE:.3f}-{(ia+pos+window)/RATE:.3f}')
    median=float(np.median(scores)); fraction=sum(s>=.90 for s in scores)/len(scores)
    tested=len(starts)*window/RATE
    label='probable_acoustic_match' if median>=.90 and fraction>=.8 and tested>=3 else 'uncertain_similarity'
    return dict(classification=label, offset_b_minus_a_seconds=offset, aligned_extent_seconds=length/RATE,
        tested_seconds=tested, median_abs_correlation=median, max_abs_correlation=max(scores),
        fraction_windows_ge_090=fraction, median_gain_b_over_a=float(np.median(gains)),
        tested_intervals_a=';'.join(intervals), window_correlations=';'.join(f'{v:.5f}' for v in scores))


def main():
    if OUT.exists(): raise FileExistsError('Refusing to overwrite existing recording_similarity reports')
    # Read every existing report, including the chart bytes; parse every CSV and Markdown.
    reports=[]
    for directory in ('dataset_audit','data_quality'):
        for p in sorted((BASE/'reports'/directory).iterdir()):
            if p.is_file():
                info={'path':str(p.relative_to(BASE)), 'sha256':sha(p)}
                if p.suffix=='.csv': info['rows']=len(csvread(p))
                elif p.suffix=='.md': info['characters']=len(p.read_text(encoding='utf-8'))
                else: info['bytes']=len(p.read_bytes())
                reports.append(info)
    rows=csvread(BASE/'birds_audio/metadata.csv')
    audit={r['file_path']:r for r in csvread(BASE/'reports/dataset_audit/audio_quality_report.csv')}
    paths=[BASE/r['file_path'] for r in rows]
    inputs=sorted(p for root in ('birds_audio','Noisy') for p in (BASE/root).rglob('*') if p.is_file())
    before={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in inputs}
    exact=defaultdict(list)
    for i,p in enumerate(paths):
        assert before[p][2]==audit[rows[i]['file_path']]['sha256'], 'Audit is stale'
        exact[before[p][2]].append(i)
    # All files are hashed; acoustics of byte-identical files need only be indexed once.
    representatives=[v[0] for v in exact.values()]
    index=defaultdict(list); counts={}
    for n,i in enumerate(representatives,1):
        fp=fingerprint(audio(paths[i])); counts[i]=len(fp)
        for token,t in fp: index[token].append((i,t))
        if n%100==0: print(f'Fingerprinted {n}/{len(representatives)} unique files',flush=True)
    print('Selecting candidates using fingerprint time-offset votes',flush=True)
    votes=defaultdict(Counter); anchors=defaultdict(set); skipped=0
    for token,postings in index.items():
        if len(postings)>80 or len({i for i,t in postings})>20:
            skipped+=1; continue
        for (i,t),(j,u) in combinations(postings,2):
            if i==j: continue
            if i>j: i,j,t,u=j,i,u,t
            bucket=round((u-t)/4)
            votes[i,j][bucket]+=1
            anchors[i,j,bucket].add(t)
    candidates=[]
    for (i,j),hist in votes.items():
        offsets=[]
        for bucket,count in hist.most_common(3):
            times=anchors[i,j,bucket]
            if count>=8 and len(times)>=4 and (max(times)-min(times))*HOP/RATE>=.5:
                offsets.append((bucket,count,len(times)))
        if offsets: candidates.append((i,j,offsets))
    del index,votes,anchors
    pairs=[]
    def base(i,j):
        return dict(file_a=rows[i]['file_path'],file_b=rows[j]['file_path'], species_a=rows[i]['species'],species_b=rows[j]['species'],
            recording_id_a=rows[i]['original_recording_id'],recording_id_b=rows[j]['original_recording_id'],
            cross_species=rows[i]['species']!=rows[j]['species'])
    for members in exact.values():
        for i,j in combinations(members,2):
            r=base(i,j); r.update(classification='confirmed_exact_duplicate',fingerprint_votes='',fingerprint_anchor_times='',
                offset_b_minus_a_seconds=0,aligned_extent_seconds=audit[rows[i]['file_path']]['duration_seconds'],
                tested_seconds='',median_abs_correlation='',max_abs_correlation='',fraction_windows_ge_090='',
                median_gain_b_over_a=1,tested_intervals_a='',window_correlations='',evidence='current full-file SHA-256 equality')
            pairs.append(r)
    for n,(i,j,offsets) in enumerate(candidates,1):
        results=[]
        for bucket,count,times in offsets:
            result=verify(audio(paths[i]),audio(paths[j]),bucket*4*HOP/RATE)
            if result:
                result.update(fingerprint_votes=count,fingerprint_anchor_times=times)
                results.append(result)
        if results:
            result=max(results,key=lambda r:(r['classification']=='probable_acoustic_match',r['median_abs_correlation'],r['max_abs_correlation']))
            # Keep failed waveform confirmations visible as uncertain candidates.
            r=base(i,j); r.update(result,evidence='spectral landmark alignment plus sampled waveform correlation')
            pairs.append(r)
        if n%100==0: print(f'Verified {n}/{len(candidates)} candidate pairs',flush=True)
    parent=list(range(len(rows)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    lookup={r['file_path']:i for i,r in enumerate(rows)}
    for r in pairs:
        if r['classification']!='uncertain_similarity':
            a,b=find(lookup[r['file_a']]),find(lookup[r['file_b']]); parent[b]=a
    components=defaultdict(list)
    for i in range(len(rows)): components[find(i)].append(i)
    membership=[]
    for members in components.values():
        gid='possible_'+hashlib.sha256('|'.join(sorted(rows[i]['file_path'] for i in members)).encode()).hexdigest()[:16]
        for i in members:
            edges=[r for r in pairs if rows[i]['file_path'] in (r['file_a'],r['file_b'])]
            membership.append(dict(possible_group_id=gid,file_path=rows[i]['file_path'],species=rows[i]['species'],
                original_recording_id=rows[i]['original_recording_id'],group_size=len(members),
                group_status='review linked component' if len(members)>1 else 'no accepted acoustic link; independence unknown',
                exact_edges=sum(r['classification']=='confirmed_exact_duplicate' for r in edges),
                probable_edges=sum(r['classification']=='probable_acoustic_match' for r in edges),
                uncertain_edges=sum(r['classification']=='uncertain_similarity' for r in edges),
                independent_recording_verified=False))
    after={p:(p.stat().st_size,p.stat().st_mtime_ns,sha(p)) for p in inputs}
    assert before==after,'Original input changed during investigation'
    OUT.mkdir()
    fields=list(base(0,1))+['classification','fingerprint_votes','fingerprint_anchor_times','offset_b_minus_a_seconds',
        'aligned_extent_seconds','tested_seconds','median_abs_correlation','max_abs_correlation','fraction_windows_ge_090',
        'median_gain_b_over_a','tested_intervals_a','window_correlations','evidence']
    def write(name,data,keys):
        with (OUT/name).open('x',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=keys); w.writeheader(); w.writerows(data)
    write('similarity_pairs.csv',pairs,fields)
    write('possible_recording_groups.csv',membership,list(membership[0]))
    manual=[dict(r,reviewer='',review_date='',listening_findings='',source_evidence='',decision='pending; retained') for r in pairs]
    write('manual_similarity_review.csv',manual,fields+['reviewer','review_date','listening_findings','source_evidence','decision'])
    totals=Counter(r['classification'] for r in pairs)
    lines=['# Recording similarity and provenance investigation','',f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).','',
        '## Results','',f'945 bird recordings; {len(representatives)} byte-unique representatives acoustically analyzed. All exact aliases remain in the output groups.',
        f'Fingerprint-selected pairs: {len(candidates)}. Reported pair classifications: {dict(totals)}.',
        f'Possible components: {len(components)}; multi-file components: {sum(len(v)>1 for v in components.values())}. These are review hypotheses, not confirmed independent recording events.',
        f'Cross-species reported pairs: {sum(r["cross_species"] for r in pairs)}. Original bird/noise files and metadata hashes, sizes and modification times unchanged: {before==after}.','',
        '## Method and thresholds','',
        'Read all prior audit and data-quality report files and parsed their CSV/Markdown contents. Revalidated bird hashes against the audit. Analyze byte-identical audio once and explicitly include all exact duplicate edges. No species restriction is used for candidate matching.',
        'Audio is decoded, averaged to mono and downsampled to 8 kHz in memory solely for analysis. No transformed audio is saved. STFT: 512 samples, hop 128; local spectral maxima over 9 frequency bins by 9 time frames, bins below 125 Hz ignored, peaks within 55 dB of recording maximum; retain up to three peaks per frame. Pair each peak with up to five subsequent peaks 4–60 frames away. Hash frequency bins in pairs and time differences in pairs of frames.',
        f'An inverted landmark index retrieves matches without all-pairs waveform scans. Suppress tokens with more than 80 postings or more than 20 distinct recordings ({skipped} suppressed tokens). For each candidate pair test at most three leading offset buckets (64 ms), requiring 8 votes, 4 distinct anchor times, and 0.5 seconds anchor span.',
        'Refine each candidate offset by normalized FFT cross-correlation over up to five two-second anchors, searching ±150 ms. At the strongest alignment, inspect up to ten non-overlapping two-second waveform windows spread across the overlap. Correlation is mean-centered, normalized and absolute, so gain changes and polarity inversion are tolerated. Offsets mean time in B = time in A + offset.',
        'Confirmed exact duplicates require full-file SHA-256 equality. Probable acoustic matches require median absolute waveform correlation ≥0.90, at least 80% of sampled windows ≥0.90, and ≥3 seconds tested. Other fingerprint-selected pairs are uncertain similarities, including failed waveform confirmation. They are not accepted identity links. Thresholds are heuristic, not calibrated probabilities.',
        'aligned_extent_seconds describes the extent available at the estimated lag, NOT a claim that the entire extent matches. tested_seconds and tested_intervals_a describe actual sampled evidence. Gain estimates are least-squares B/A slopes on analysis waveforms, not measured original recording gain settings.','',
        '## Possible groups and review','',
        'Connected components use confirmed exact and probable acoustic edges only. Uncertain edges remain in the pair/manual tables and do not merge groups. All 945 files appear once in the membership CSV. Transitive grouping is conservative and requires manual review; an edge does not establish the correctness of either original ID. No splits or exclusions were performed.',
        'For each listed pair, listen at the reported A intervals and corresponding B intervals using the offset. Compare call sequences AND background events, assess gain/re-encoding/trimming explanations, and record source URLs, catalog namespace, recorder, date/location and edit history. Cross-species matches require label review. Complete reviewer/date/findings/decision fields in manual_similarity_review.csv; all decisions start pending.',
        '## Limitations','',
        'A non-match never proves independence. Same field sessions with different excerpts can evade acoustic detection. Fingerprint pruning, frequency quantization, very quiet or short clips, overlaps shorter than three seconds, phase distortion, heavy compression, pitch/time changes and content above 4 kHz can cause missed matches. Repeated stereotyped bird calls and stationary background can produce false candidates or high correlation. Testing sampled windows does not verify every sample or local edits. No human listening or external provenance verification is claimed.',
        'The 11 known exact duplicate groups are included explicitly rather than counted as independently recovered positives. No synthetic transformation benchmark was performed; recall for re-encoded, gain-adjusted or trimmed copies is not quantified. Prior near-silent flags remain relevant to manual review.',
        'A small in-memory waveform sanity check recovered a two-second trim with 0.35 gain at the expected lag and did not accept unrelated random noise. This checks alignment logic only, not fingerprint retrieval recall or real-world classification accuracy.',
        'Analysis resampling/fingerprints are investigative measurements only: no preprocessing dataset, noise augmentation, model training, train/validation/test split, original-file modification or Git operation occurred. Stop here pending user approval.','',
        '## Reproduction','', '`python components/audio_classification/src/check_recording_similarity.py`',
        'Requires a nonexistent output directory; refuses overwrites. Dependencies: numpy '+np.__version__+', scipy '+scipy.__version__+', soundfile '+sf.__version__+'.','',
        '## Prior reports read','', '```json',json.dumps(reports,indent=2),'```']
    (OUT/'recording_similarity_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Complete: '+str(dict(totals)),flush=True)


if __name__=='__main__': main()
