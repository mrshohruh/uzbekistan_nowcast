"""Resolve the official download descriptor, preserving both HTTP payloads."""
import pandas as pd


def download(downloader, row):
    descriptor, descriptor_meta = downloader.get(row, row['machine_download_url'])
    if not isinstance(descriptor, dict) or not {'file', 'updated_at'} <= descriptor.keys():
        raise ValueError('SIAT download descriptor schema changed')
    release = pd.Timestamp(descriptor['updated_at']).isoformat()
    basis = 'dataset_update_timestamp; not historical first release'
    payload, meta = downloader.get(row, descriptor['file'], source_release_date=release, source_release_basis=basis)
    meta = dict(meta)
    meta['descriptor_raw_file_path'] = descriptor_meta['raw_file_path']
    meta['source_release_date'] = release
    meta['source_release_basis'] = basis
    return payload, meta
