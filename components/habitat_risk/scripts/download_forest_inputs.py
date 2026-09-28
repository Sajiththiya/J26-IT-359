"""Fetch missing v1.12 inputs; verify all six files against provider MD5 headers."""
from pathlib import Path
import base64
import hashlib
import json
import subprocess
from email.parser import Parser
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://storage.googleapis.com/earthenginepartners-hansen/GFC-2024-v1.12/'

def main():
    records = []
    folder = ROOT / 'data/raw/forest'
    folder.mkdir(parents=True, exist_ok=True)
    for tile in ['10N_070E', '10N_080E']:
        for band in ['treecover2000', 'lossyear', 'datamask']:
            path = folder / f'Hansen_GFC-2024-v1.12_{band}_{tile}.tif'
            url = BASE + path.name
            raw_headers = subprocess.check_output(['curl', '--fail', '--silent', '--show-error', '--head', '--retry', '3', url], text=True)
            headers = Parser().parsestr(raw_headers.strip().split('\n\n')[-1].split('\n', 1)[1])
            length = int(headers['Content-Length'])
            hashes = ','.join(headers.get_all('x-goog-hash', []))
            expected = next(v.strip()[4:] for v in hashes.split(',') if v.strip().startswith('md5='))
            if not path.exists():
                print(f'Downloading {path.name} ({length:,} bytes)', flush=True)
                temp = path.with_suffix('.tif.part')
                subprocess.run(['curl', '--fail', '--silent', '--show-error', '--retry', '3', '--output', str(temp), url], check=True)
                candidate = temp
            else:
                candidate = path
            md5, sha = hashlib.md5(), hashlib.sha256()
            with candidate.open('rb') as source:
                while chunk := source.read(1024 * 1024):
                    md5.update(chunk)
                    sha.update(chunk)
            assert candidate.stat().st_size == length, f'Length mismatch: {path.name}'
            assert base64.b64encode(md5.digest()).decode() == expected, f'Provider checksum mismatch: {path.name}'
            if candidate != path:
                candidate.replace(path)
            records.append({'path': str(path.relative_to(ROOT)), 'url': url, 'bytes': length,
                            'sha256': sha.hexdigest(), 'provider_md5_base64': expected,
                            'provider_checksum_verified': True,
                            'verified_at_utc': datetime.now(timezone.utc).isoformat()})
            print(f'Verified {path.name}', flush=True)
    (ROOT / 'data/metadata/forest_download_manifest.json').write_text(json.dumps(records, indent=2) + '\n')

if __name__ == '__main__':
    main()
