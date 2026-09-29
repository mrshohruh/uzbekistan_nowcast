"""Resumable official FX bootstrap, also reusable by the pilot CLI."""
from pathlib import Path
import logging
from uuid import uuid4
from datetime import date
from uznowcast.registry import load_registry
from uznowcast.io.http import Downloader
from uznowcast.io.cbu import download
from uznowcast.provenance import atomic_parquet

def main():
    root = Path.cwd()
    (root / 'logs').mkdir(exist_ok=True)
    logger = logging.getLogger('uznowcast')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.FileHandler(root / 'logs/pipeline.log', encoding='utf-8'))
    progress = logging.getLogger('uznowcast.progress')
    progress.propagate = False
    progress.addHandler(logging.StreamHandler())
    row = load_registry(root / 'registry/uzbekistan_nowcasting_v1_registry.xlsx').rows['usd_uzs']
    client = Downloader(root, uuid4().hex)
    frame = download(client, row, row['verified_start'].replace('-M', '-') + '-01', date.today())
    atomic_parquet(frame, root / 'data/processed/usd_uzs_daily.parquet')
    logging.getLogger('uznowcast.progress').info('FX bootstrap complete: %s activation dates', len(frame))

if __name__ == '__main__':
    main()
