"""Archive GDP report embeds, retaining the dated landing-page relationship."""
import json
import logging
import time
from urllib.parse import urljoin, urlparse, parse_qs, unquote
from bs4 import BeautifulSoup
from collect import archive, OUT, ROOT

def main():
    logging.basicConfig(filename=OUT/'collection.log',level=logging.INFO)
    relationships=[]
    for path in list(OUT.glob('*.json')):
        meta=json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(meta,dict) or not meta.get('raw_file_path','').endswith('.html'):
            continue
        soup=BeautifulSoup((ROOT/meta['raw_file_path']).read_bytes(),'html.parser')
        article=soup.select_one('div.item-page')
        if article is None:
            continue
        title=article.select_one('[itemprop=headline]')
        date=article.select_one('p.text-gray-600')
        for embed in article.select('iframe[src]'):
            url=urljoin(meta['source_url'],embed['src'])
            if 'file=' in url:
                url=parse_qs(urlparse(url).query)['file'][0]
            try:
                report=archive(url)
                relationships.append(dict(article_url=meta['source_url'],report_url=url,
                    title=title.get_text(' ',strip=True) if title else '',
                    publication_date=date.get_text(' ',strip=True) if date else '',
                    article_sha256=meta['sha256'],report_sha256=report['sha256']))
                print(url,flush=True)
            except Exception:
                logging.exception('Official embedded report failed %s',url)
            time.sleep(.4)
    (OUT/'embed_relationships.json').write_text(json.dumps(relationships,indent=2),encoding='utf-8')

if __name__=='__main__':
    main()
