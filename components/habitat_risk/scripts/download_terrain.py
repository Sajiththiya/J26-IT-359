"""Download CGIAR-CSI SRTM v4 90m tiles; retain original archives and hashes."""
from pathlib import Path
import subprocess,zipfile,json,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def main():
    folder=ROOT/'data/raw/terrain';folder.mkdir(parents=True,exist_ok=True)
    rows=[]
    for tile in ['52_11','53_11']:
        path=folder/f'srtm_{tile}.zip'
        url=f'https://srtm.csi.cgiar.org/wp-content/uploads/files/srtm_5x5/TIFF/{path.name}'
        if not path.exists():
            temp=path.with_suffix('.zip.part')
            subprocess.run(['curl','--fail','--show-error','--silent','--retry','3','--output',str(temp),url],check=True)
            with zipfile.ZipFile(temp) as z:assert z.testzip() is None
            temp.replace(path)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            for name in z.namelist():
                if name.lower().endswith(('.tif','.txt')):
                    destination=folder/Path(name).name
                    if not destination.exists():destination.write_bytes(z.read(name))
        rows.append({'url':url,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'zip_crc_verified':True,'provider_checksum_available':False,'retrieved_at_utc':datetime.now(timezone.utc).isoformat()})
        print('Verified ZIP and extracted',path.name,flush=True)
    (ROOT/'data/metadata/terrain_download_manifest.json').write_text(json.dumps(rows,indent=2)+'\n')
if __name__=='__main__':main()
