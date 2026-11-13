"""Download bounded public planning data without landowner personal information."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,urllib.parse,urllib.request
from floodlab import ROOT
from fetch_data import BBOX

SOURCES={
 'parcels':('https://services.arcgis.com/g1fRTDLeMgspWrYp/arcgis/rest/services/BCAD_Parcels/FeatureServer/0',
            'OBJECTID,PropID,state_cd,GBA_Living,legal_acre,LandSqft',
            'BCAD parcel geometry and tax-use codes, distributed by City of San Antonio. Not building footprints or household counts.'),
 'draft_floodplain':('https://services2.arcgis.com/Eb8y2VjBgkqbQJwk/arcgis/rest/services/Draft_Floodplain/FeatureServer/1',
                     '*','San Antonio River Authority Upper San Antonio DRAFT floodplain. Not the effective FEMA regulatory map; subject to revision.'),
 'aquifer':('https://gisweb.tceq.texas.gov/arcgis/rest/services/Public/EdwardsAquifer/MapServer/0',
             '*','TCEQ Edwards Aquifer regulatory zones. Regional geological/environmental context, not borehole or tunneling data.')}

def request(url,params):
    with urllib.request.urlopen(url+'?'+urllib.parse.urlencode(params),timeout=45) as response:
        data=json.load(response)
    if data.get('error'):raise RuntimeError(str(data['error']))
    return data

def fetch(name):
    url,fields,note=SOURCES[name]
    folder=ROOT/'data/planning';folder.mkdir(parents=True,exist_ok=True)
    target=folder/(name+'.geojson')
    if target.exists():return target
    meta=request(url,{'f':'json'})
    params={'f':'json','where':'1=1','geometry':','.join(map(str,BBOX)),
            'geometryType':'esriGeometryEnvelope','inSR':4326,
            'spatialRel':'esriSpatialRelIntersects','returnIdsOnly':'true'}
    ids=sorted(request(url+'/query',params).get('objectIds') or [])
    oid=meta.get('objectIdField') or next(f['name'] for f in meta['fields'] if f['type']=='esriFieldTypeOID')
    # Small bounded parallel batches avoid silent transfer truncation.
    def page(chunk):
        data=request(url+'/query',{'f':'geojson','objectIds':','.join(map(str,chunk)),
                     'outFields':fields,'outSR':4326,'returnGeometry':'true','geometryPrecision':7})
        if data.get('exceededTransferLimit'):raise RuntimeError('Truncated page')
        features=data.get('features',[])
        got={int(f['properties'][oid]) for f in features}
        if got!=set(chunk):raise RuntimeError('Returned object IDs differ from request')
        return features
    chunks=[ids[i:i+200] for i in range(0,len(ids),200)]
    features=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for batch in pool.map(page,chunks):features.extend(batch)
    data={'type':'FeatureCollection','features':features}
    raw=json.dumps(data,separators=(',',':')).encode()
    target.write_bytes(raw)
    target.with_suffix('.source.json').write_text(json.dumps({
        'service':url,'fields_requested':fields,'bbox_wgs84':BBOX,
        'retrieved_utc':datetime.now(timezone.utc).isoformat(),'features':len(features),
        'sha256':hashlib.sha256(raw).hexdigest(),'note':note,
        'description':meta.get('description'),'copyright':meta.get('copyrightText'),
        'editingInfo':meta.get('editingInfo')},indent=2),encoding='utf-8')
    print(name,':',len(features),'features',flush=True)
    return target

if __name__=='__main__':
    failures={}
    for name in SOURCES:
        try:fetch(name)
        except Exception as exc:
            failures[name]=str(exc);print(name,': FAILED:',str(exc)[:250],flush=True)
    (ROOT/'results/planning_download_status.json').write_text(json.dumps({
        'failures':failures,'sources':{k:v[0] for k,v in SOURCES.items()}},indent=2))
    if failures:raise SystemExit(1)
