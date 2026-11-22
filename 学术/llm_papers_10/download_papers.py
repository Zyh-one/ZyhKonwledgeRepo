#!/usr/bin/env python3
"""Download and package the 10 publicly available papers (stdlib only)."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from zipfile import ZipFile, ZIP_DEFLATED
import time

HERE = Path(__file__).resolve().parent
DEST = HERE / 'papers'
ZIP = HERE / 'LLM_AI_Infra_10_Papers.zip'
PAPERS = [
    ('01_Attention_Is_All_You_Need.pdf', 'https://arxiv.org/pdf/1706.03762'),
    ('02_FlashAttention.pdf', 'https://arxiv.org/pdf/2205.14135'),
    ('03_FlashAttention_2.pdf', 'https://arxiv.org/pdf/2307.08691'),
    ('04_vLLM_PagedAttention.pdf', 'https://arxiv.org/pdf/2309.06180'),
    ('05_Orca.pdf', 'https://www.usenix.org/system/files/osdi22-yu.pdf'),
    ('06_SGLang.pdf', 'https://proceedings.neurips.cc/paper_files/paper/2024/file/724be4472168f31ba1c9ac630f15dec8-Paper-Conference.pdf'),
    ('07_Sarathi_Serve.pdf', 'https://arxiv.org/pdf/2403.02310'),
    ('08_DistServe.pdf', 'https://arxiv.org/pdf/2401.09670'),
    ('09_Megatron_LM.pdf', 'https://arxiv.org/pdf/1909.08053'),
    ('10_DeepSeek_V2.pdf', 'https://arxiv.org/pdf/2405.04434'),
]

def is_pdf(p):
    return p.exists() and p.stat().st_size > 10000 and p.open('rb').read(5) == b'%PDF-'

def download(name, url):
    path = DEST / name
    if is_pdf(path):
        print('Already present:', name)
        return True
    for attempt in range(1, 4):
        try:
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0 (academic paper downloader)', 'Accept': 'application/pdf'})
            with urlopen(req, timeout=90) as response, path.open('wb') as f:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk: break
                    f.write(chunk)
            if not is_pdf(path):
                raise ValueError('Response was not a valid PDF')
            print('Downloaded:', name)
            return True
        except (URLError, HTTPError, OSError, ValueError) as e:
            path.unlink(missing_ok=True)
            print(f'Attempt {attempt}/3 failed for {name}: {e}')
            if attempt != 3: time.sleep(2 * attempt)
    return False

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    fails = []
    for name, url in PAPERS:
        if not download(name, url): fails.append((name, url))
    with ZipFile(ZIP, 'w', ZIP_DEFLATED) as z:
        for name, _ in PAPERS:
            path = DEST / name
            if is_pdf(path): z.write(path, name)
        z.write(HERE / 'README.md', 'README.md')
    print(f'\nPDFs: {len(PAPERS)-len(fails)}/{len(PAPERS)}; ZIP: {ZIP}')
    if fails:
        print('Please rerun to retry failures:')
        for name, url in fails: print(' -', name, url)
    else:
        print('All ten PDFs verified and packed successfully.')

if __name__ == '__main__': main()
