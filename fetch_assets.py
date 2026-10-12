"""Fetch public assets to exact paths; SHA256 is mandatory, mismatch fails closed."""
import hashlib,json,os,sys,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    entries=json.loads((ROOT/'assets-manifest.json').read_text())
    for entry in entries:
        path=(ROOT/entry['path']).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('Unsafe asset path')
        expected=entry['sha256']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==expected:
            print('Verified cached asset:',entry['path']);continue
        request=urllib.request.Request(entry['url'],headers={'User-Agent':'GK-Snippets-asset-fetch'})
        with urllib.request.urlopen(request,timeout=45) as response:
            payload=response.read(10*1024*1024+1)
        if len(payload)>10*1024*1024:raise ValueError('Asset too large')
        if hashlib.sha256(payload).hexdigest()!=expected:raise ValueError('SHA256 mismatch: '+entry['path'])
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:f.write(payload)
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        print('Fetched and verified:',entry['path'])
if __name__=='__main__':main()
