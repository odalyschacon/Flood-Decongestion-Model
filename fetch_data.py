"""Small, cached, reproducible public-data downloads. No credentials required."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
import pandas as pd

ROOT = Path(__file__).resolve().parent
BBOX = [-98.57, 29.39, -98.50, 29.46]
HF_REVISION = 'ad98e681e7cf6af9ced145833b522c4f6c0acad1'
HF = f'https://huggingface.co/datasets/jennifer-fowler/UTSA-flood-images/resolve/{HF_REVISION}/'
CITY = 'https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/'


def get_json(url):
    with urllib.request.urlopen(url, timeout=45) as response:
        data = json.load(response)
    if 'error' in data:
        raise RuntimeError(str(data['error']))
    return data


def download(url, target):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists(): return target
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read()
    tmp = target.with_suffix(target.suffix + '.part')
    tmp.write_bytes(content)
    tmp.replace(target)
    target.with_suffix(target.suffix+'.source.json').write_text(json.dumps({
        'url': url, 'retrieved_utc': datetime.now(timezone.utc).isoformat(),
        'sha256': hashlib.sha256(content).hexdigest(), 'bytes': len(content)
    }, indent=2), encoding='utf-8')
    return target


def fetch_city(name):
    target = ROOT / 'data/city' / (name+'.geojson')
    if target.exists(): return target
    service = CITY + name + '/FeatureServer/0'
    metadata = get_json(service+'?f=json')
    params = {'f':'json','where':'1=1','geometry':','.join(map(str,BBOX)),
              'geometryType':'esriGeometryEnvelope','inSR':4326,
              'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'}
    ids = get_json(service+'/query?'+urllib.parse.urlencode(params)).get('objectIds') or []
    features = []
    for offset in range(0,len(ids),200):
        query = {'f':'geojson','objectIds':','.join(map(str,ids[offset:offset+200])),
                 'outFields':'*','outSR':4326,'returnGeometry':'true'}
        page = get_json(service+'/query?'+urllib.parse.urlencode(query))
        if page.get('exceededTransferLimit'): raise RuntimeError('Truncated GIS response')
        features.extend(page['features'])
    if len(features)!=len(ids): raise RuntimeError('GIS feature count mismatch')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'type':'FeatureCollection','features':features}),encoding='utf-8')
    target.with_suffix('.source.json').write_text(json.dumps({
        'service':service,'bbox_wgs84':BBOX,'features':len(features),
        'retrieved_utc':datetime.now(timezone.utc).isoformat(),
        'copyright':metadata.get('copyrightText'), 'description':metadata.get('description'),
        'sha256':hashlib.sha256(target.read_bytes()).hexdigest()
    },indent=2),encoding='utf-8')
    return target


def fetch_dem():
    target = ROOT/'data/city/elevation.tif'
    if target.exists(): return target
    params={'f':'json','bbox':','.join(map(str,BBOX)),'bboxSR':4326,'imageSR':32614,
            'size':'400,450','format':'tiff','pixelType':'F32',
            'renderingRule':json.dumps({'rasterFunction':'None'}),
            'interpolation':'RSP_BilinearInterpolation','adjustAspectRatio':'false'}
    url='https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage?'+urllib.parse.urlencode(params)
    export=get_json(url)
    download(export['href'],target)
    target.with_suffix('.request.json').write_text(json.dumps({'request_url':url,'response':export},indent=2))
    return target


def main():
    texas=ROOT/'data/texas'
    for name in ['README.md','README.txt','DATA_DICTIONARY.txt','image_metadata.csv']:
        download(HF+name,texas/name)
    df=pd.read_csv(texas/'image_metadata.csv',keep_default_na=False)
    # Three before/after pairs; full 1.6 GB imagery is optional, not needed for setup.
    ids=['TX001_2016_NAIP','TX001_2017_NOAA','TX002_2016_NAIP',
         'TX002_2017_NOAA','TX003_2016_NAIP','TX003_2017_NOAA']
    paths=df.loc[df.image_id.isin(ids),'image_path'].tolist()
    jobs=[(HF+n,texas/n) for n in paths]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for result in pool.map(lambda x:download(*x),jobs): print(result.name,flush=True)
    for name in ['StormInlets','StormwaterUnderground','StormChannels','LowWaterCrossings']:
        print(fetch_city(name).name,flush=True)
    print(fetch_dem().name,flush=True)

if __name__=='__main__': main()
