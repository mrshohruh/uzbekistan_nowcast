"""Follow only GDP publication links in archived official catalogues."""
import json
import logging
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from collect import archive, ROOT, OUT

def main():
    logging.basicConfig(filename=OUT/'collection.log', level=logging.INFO)
    candidates=json.loads((OUT/'discovered_candidates.json').read_text())
    for row in candidates:
        try:
            record=archive(row['url'])
            print(record['raw_file_path'],flush=True)
        except Exception as exc:
            logging.exception('Official source failed %s',row['url'])
            print('FAILED',row['url'],str(exc),flush=True)
        time.sleep(.4)
    # All GDP links in official annual catalogues; no endpoint guesses.
    seed=BeautifulSoup((OUT/'a9d3a5097ca873e7b7eb.html').read_bytes(),'html.parser')
    catalogues=[urljoin('https://stat.uz/',a['href']) for a in seed.find_all('a',href=True)
                if 'press-releases/' in a['href'] and any(str(y) in a.get_text() for y in range(2018,2027))]
    for url in dict.fromkeys(catalogues):
        try:
            record=archive(url)
            soup=BeautifulSoup((ROOT/record['raw_file_path']).read_bytes(),'html.parser')
            links=[urljoin(url,a['href']) for a in soup.find_all('a',href=True)
                   if 'gross domestic product' in a.get_text(' ',strip=True).lower()]
            for link in dict.fromkeys(links):
                try:
                    r=archive(link)
                    print(r['raw_file_path'],flush=True)
                except Exception:
                    logging.exception('Linked GDP source failed %s',link)
                time.sleep(.4)
        except Exception:
            logging.exception('Catalogue failed %s',url)

if __name__=='__main__':
    main()
