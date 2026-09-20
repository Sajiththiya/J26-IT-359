"""Read-only identity review using local metadata and existing audit evidence."""
import csv
import hashlib
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]
AUDIT = BASE / 'reports/dataset_audit'
OUT = BASE / 'reports/data_quality'


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def write(name, rows):
    with (OUT / name).open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    if OUT.exists():
        raise FileExistsError('Refusing to overwrite an existing data_quality review')
    originals = sorted(p for root in ('birds_audio', 'Noisy') for p in (BASE / root).rglob('*') if p.is_file())
    before = {p: (p.stat().st_size, p.stat().st_mtime_ns, sha(p)) for p in originals}
    metadata = read(BASE / 'birds_audio/metadata.csv')
    quality = {r['file_path']: r for r in read(AUDIT / 'audio_quality_report.csv') if r['dataset'] == 'birds_audio'}
    assert len(metadata) == len(quality) == 945
    assert len({r['file_path'] for r in metadata}) == len(metadata)
    for row in metadata:
        assert before[BASE / row['file_path']][2] == quality[row['file_path']]['sha256'], 'Stale audio audit'
        assert row['species'] == quality[row['file_path']]['category']
    groups = defaultdict(list)
    for row in metadata:
        groups[quality[row['file_path']]['sha256']].append(row)
    group_ids = {h: f'content_{h[:16]}' for h in groups}
    duplicates = []
    links = []
    for h, members in groups.items():
        if len(members) < 2:
            continue
        for row in members:
            duplicates.append(dict(group_id=group_ids[h], sha256=h, file_path=row['file_path'],
                species=row['species'], original_recording_id=row['original_recording_id'], source=row['source'],
                group_size=len(members), different_species=len({r['species'] for r in members})>1,
                different_recording_ids=len({r['original_recording_id'] for r in members})>1,
                identity_status='confirmed identical file content; original provenance unresolved'))
        links.append(dict(group_id=group_ids[h], file_paths=' | '.join(r['file_path'] for r in members),
            recording_ids=' | '.join(r['original_recording_id'] for r in members),
            evidence='SHA-256 equality reverified against current files',
            strength='confirmed content equality', future_constraint='keep together if future splits are approved'))
    audit_duplicates = read(AUDIT / 'duplicate_report.csv')
    assert {r['file_path'] for r in duplicates} == {r['file_path'] for r in audit_duplicates}
    near = []
    identity = []
    checklist = []
    for row in metadata:
        path = row['file_path']; q = quality[path]; h = q['sha256']; members = groups[h]
        local = not row['original_recording_id'].isdigit()
        quiet = q['near_silent'] == 'True'
        duplicate = len(members)>1
        status = 'confirmed_content_link' if duplicate else ('unresolved' if local else 'provisional_catalog_style')
        if quiet:
            near.append(dict(filename=PurePosixPath(path).name, file_path=path, species=row['species'],
                original_recording_id=row['original_recording_id'], rms_dbfs=q['rms_dbfs'],
                duration_seconds=q['duration_seconds'], peak_amplitude=q['peak_amplitude'],
                review_status='pending listening; not excluded'))
        identity.append(dict(file_path=path, species=row['species'], original_recording_id=row['original_recording_id'],
            source=row['source'], source_exists=(BASE / row['source']).is_file(),
            id_type='local sequential label' if local else 'numeric catalog-style label',
            id_equals_source_stem=row['original_recording_id']==PurePosixPath(row['source']).stem,
            content_group_id=group_ids[h], content_group_size=len(members), identity_status=status,
            independent_origin_verified=False,
            linked_ids=' | '.join(r['original_recording_id'] for r in members if r['file_path']!=path),
            leakage_risk='confirmed duplicate content' if duplicate else 'unresolved source identity; possible overlap/re-encoding',
            required_evidence='original source URL/recording, recorder, date, location, parent recording and edit history'))
        reasons = (['exact duplicate with conflicting ID'] if duplicate else []) + (['near-silent'] if quiet else [])
        reasons += ['local filename-derived identity' if local else 'numeric identity not externally verified']
        checklist.append(dict(file_path=path, species=row['species'], original_recording_id=row['original_recording_id'],
            priority='1: audio/duplicate review' if quiet or duplicate else ('2: local provenance' if local else '3: catalog verification'),
            reasons='; '.join(reasons), rms_dbfs=q['rms_dbfs'], duration_seconds=q['duration_seconds'],
            compare_with=' | '.join(r['file_path'] for r in members if r['file_path']!=path),
            reviewer='', review_date='', audible_target_bird='', species_confidence='', call_time_ranges='',
            background_or_other_species='', clipping_or_artifacts='', same_call_or_background_as_other_file='',
            source_url_or_original='', recorder_date_location='', parent_recording_id='',
            edit_history='', playback_gain_used='', decision='pending; retained', notes=''))
    summary = []
    for species in sorted({r['species'] for r in metadata}):
        rows = [r for r in identity if r['species']==species]
        statuses = Counter(r['identity_status'] for r in rows)
        numeric = sum(r['id_type']=='numeric catalog-style label' for r in rows)
        summary.append(dict(species=species, files=len(rows), declared_ids=len({r['original_recording_id'] for r in rows}),
            confirmed_content_link_files=statuses['confirmed_content_link'],
            confirmed_content_link_groups=len({r['content_group_id'] for r in rows if r['content_group_size']>1}),
            provisional_identity_files=statuses['provisional_catalog_style'], unresolved_identity_files=statuses['unresolved'],
            confirmed_independent_originals=0, numeric_ids=numeric,
            local_ids=sum(r['id_type']=='local sequential label' for r in rows),
            byte_unique_content_groups=len({r['content_group_id'] for r in rows}),
            near_silent_files=sum(r['species']==species for r in near),
            acquisition_priority='high: fewer than 20 numeric candidates' if numeric<20 else 'verify existing candidates first',
            conditional_gap_to_20=max(0,20-numeric), actual_independent_recording_shortfall='unknown'))
    after = {p: (p.stat().st_size, p.stat().st_mtime_ns, sha(p)) for p in originals}
    assert before == after, 'Original inputs changed during review'
    OUT.mkdir()
    write('near_silent_review.csv', near)
    write('duplicate_identity_review.csv', duplicates)
    write('recording_links.csv', links)
    write('recording_identity_review.csv', identity)
    write('unverified_local_ids.csv', [r for r in identity if r['id_type']=='local sequential label'])
    write('manual_listening_checklist.csv', sorted(checklist, key=lambda r:(r['priority'],r['species'],r['file_path'])))
    write('species_identity_summary.csv', summary)
    write('input_integrity.csv', [dict(file_path=str(p.relative_to(BASE)), sha256=v[2], size_bytes=v[0],
        mtime_ns=v[1], unchanged=True) for p,v in before.items()])
    mixed = sum(any(r['original_recording_id'].isdigit() for r in members) and any(not r['original_recording_id'].isdigit() for r in members) for members in groups.values() if len(members)>1)
    local_linked = sum(r['id_type']=='local sequential label' and r['content_group_size']>1 for r in identity)
    lines = ['# Dataset Quality and Original Recording Verification', '',
        f'Generated {datetime.now(timezone.utc).isoformat()} (UTC).', '',
        '## Scope and evidence', '',
        'Reviewed all 945 metadata rows, the existing dataset audit, filenames and source path strings. Recomputed SHA-256 for original inputs; current bird hashes match the audit. Original bird/noise files and metadata retained identical contents, sizes and modification times. No audio was processed, excluded, or listened to by this automated review. No external catalog was assumed or queried.', '',
        '## Near-silent recordings', '',
        f'{len(near)} recordings, all Sri Lanka Frogmouth, have whole-file RMS below -60 dBFS but are not digitally silent. Levels span {min(float(r["rms_dbfs"]) for r in near):.2f} to {max(float(r["rms_dbfs"]) for r in near):.2f} dBFS. Quiet calls can remain useful; low RMS alone does not justify removal.', '',
        '| Filename | Species | RMS dBFS | Duration seconds |', '|---|---|---:|---:|']
    lines += [f"| {r['filename']} | {r['species']} | {float(r['rms_dbfs']):.2f} | {float(r['duration_seconds']):.3f} |" for r in near]
    lines += ['', '## Confirmed duplicate links', '',
        f'{len(links)} exact duplicate groups contain {len(duplicates)} files. Every group has different declared recording IDs, but none has different species labels. {mixed} groups link a numeric ID with a local ID; the remaining group links two local IDs. Content identity is confirmed, not the correctness of either original ID. All files remain retained.', '',
        '| Species | File names | Declared IDs |', '|---|---|---|']
    for members in groups.values():
        if len(members)>1:
            lines.append('| '+members[0]['species']+' | '+'; '.join(PurePosixPath(r['file_path']).name for r in members)+' | '+'; '.join(r['original_recording_id'] for r in members)+' |')
    lines += ['', '## Investigation of original IDs', '',
        'All 648 unverified IDs are sequential species-name labels and exactly equal their historical source filename stems. They all reference audio/... paths. The other 297 numeric IDs reference dataset/... paths. Source extensions across all rows: '+str(dict(Counter(PurePosixPath(r['source']).suffix for r in metadata)))+'.',
        'None of the 945 historical source files is present at its recorded path. There are no repeated declared IDs or identical source-path strings. Neither numbered filenames nor matching species names establish independent recording events. Numeric IDs lack a verified catalog namespace, source URL, recorder, location and date in this CSV.',
        f'{local_linked} local-ID files are linked by exact content to other files. The other {648-local_linked} local-ID files have no confirmed counterpart from this evidence. The 648-row unverified_local_ids.csv records every case. Duplicate pairs crossing the audio/ and dataset/ collections demonstrate overlapping source collections.',
        'Distinct file hashes cannot rule out re-encoding, gain changes, trims, overlapping excerpts or different files from the same field session. Duration similarity is not proof of identity. No similarity fingerprinting, waveform alignment, embedded-tag extraction or external provenance verification was performed; these remain possible follow-up checks.', '',
        '## Species identity summary', '',
        'The three file-status columns below are mutually exclusive and sum to each species file count. Confirmed means confirmed duplicate-content linkage only. Provisional means an unlinked numeric ID. Unresolved means an unlinked local ID. All original recording identities remain unverified, including those with confirmed content links. Zero confirmed independent originals means zero verified by available evidence, not zero real originals.', '',
        '| Species | Files with confirmed content links | Provisional files | Unresolved files | Byte-unique groups | Numeric candidates |', '|---|---:|---:|---:|---:|---:|']
    lines += [f"| {r['species']} | {r['confirmed_content_link_files']} | {r['provisional_identity_files']} | {r['unresolved_identity_files']} | {r['byte_unique_content_groups']} | {r['numeric_ids']} |" for r in summary]
    lines += ['', '## Leakage and collection priorities', '',
        'The 22 exact duplicate files would cause definite content leakage if separated between future splits. Keep each confirmed group together when splitting is eventually authorized. All 945 records have unresolved provenance and therefore possible additional identity leakage; recording_identity_review.csv lists every record and required evidence. The 934 byte-unique groups are NOT 934 confirmed independent recordings.',
        'Crimson-fronted Barbet (13 numeric candidates) and Sri Lanka Grey Hornbill (14) are highest priority for provenance recovery or additional documented independent recordings. Relative to the earlier 20-recording screening target, conditional gaps are 7 and 6 only if every numeric candidate is independent and no local candidate can be verified. Actual shortfalls cannot yet be established for any species. The other eight species also need verification before sufficiency can be claimed. Frogmouth has the largest local-ID backlog (249) and all 20 quiet files.',
        'The audit also found one noise recording per category. Independent training/test noise sources are not established; future evaluation would need additional independent recordings or an explicitly limited evaluation design. No noise splitting or augmentation was performed.', '',
        '## Manual listening and provenance checklist', '',
        'manual_listening_checklist.csv includes all 945 records: urgent duplicate/quiet cases first, other local IDs next, numeric candidates last. Every decision is pending and every recording retained.', '',
        '1. Listen to the complete recording at a comfortable level; for quiet files note any playback-only gain used. Do not normalize or overwrite the source.',
        '2. Record target-bird audibility, identification confidence, call time ranges, other species, background sound and artifacts. Silence between calls is not the same as an unusable recording.',
        '3. Compare listed duplicate partners and other suspected relatives for matching call sequences, background events and overlapping sections. Listening similarity suggests a link but does not establish provenance.',
        '4. Recover original URLs/files and record catalog namespace, original ID, recorder, date, location, parent recording and edit/export history. Resolve conflicting IDs without editing the original metadata; document proposed corrections separately.',
        '5. Record reviewer, date, evidence and a proposed keep/review/exclude decision. No exclusion becomes automatic. Approve identities before any future split.', '',
        '## Deliverables and limits', '',
        'CSV files: near_silent_review, duplicate_identity_review, recording_links, recording_identity_review, unverified_local_ids, manual_listening_checklist, species_identity_summary, input_integrity.',
        'Reproducible script: src/review_data_quality.py. It refuses to overwrite an existing data_quality folder. The earlier audit reports were not regenerated or changed.',
        'No original recording or metadata was modified; no preprocessing, splitting, augmentation, training or Git operation was performed. Further work requires user approval.']
    (OUT/'data_quality_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Completed: {len(near)} quiet files; {len(links)} duplicate groups; {mixed} numeric/local links; {local_linked} linked local IDs. Original inputs unchanged.')


if __name__ == '__main__':
    main()
