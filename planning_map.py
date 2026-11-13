"""Screen OSM building footprints against SARA draft polygons; export map and KMZ.

Requires shapely and folium. OSM ways only: incomplete building coverage.
No inferred building heights, household counts, or approved construction sites.
"""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from floodlab import ROOT
sys.path.append(str(ROOT/'.deps'))
import folium
import pandas as pd
from shapely import make_valid
from shapely.geometry import shape, mapping, Polygon, box
from shapely.ops import transform, unary_union
from geo import to_utm
from fetch_data import BBOX


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('overpass_json',type=Path)
    args=p.parse_args()
    raw=json.loads(args.overpass_json.read_text(encoding='utf-8'))
    if raw.get('remark'): raise ValueError(raw['remark'])
    bounds=box(*BBOX)
    floods=json.loads((ROOT/'data/planning/draft_floodplain.geojson').read_text())
    groups={key:[] for key in ['draft_annual','draft_future']}
    for f in floods['features']:
        subtype=f['properties'].get('ZONE_SUBTY','')
        key={'1 PCT FUTURE CONDITIONS':'draft_future',
             '1 PCT ANNUAL CHANCE FLOOD HAZARD':'draft_annual'}.get(subtype)
        if key and f.get('geometry'):
            groups[key].append(make_valid(shape(f['geometry'])).intersection(bounds))
    unions={k:unary_union(v) for k,v in groups.items()}
    features=[]; rows=[]
    for item in raw['elements']:
        coords=[(v['lon'],v['lat']) for v in item.get('geometry',[])]
        if item.get('type')!='way' or len(coords)<4 or coords[0]!=coords[-1]: continue
        geom=make_valid(Polygon(coords)).intersection(bounds)
        if geom.is_empty or geom.area==0: continue
        area=transform(to_utm,geom).area
        props={'osm_way_id':item['id'],'footprint_m2':round(area,2)}
        tags=item.get('tags',{})
        props.update({k:tags[k] for k in ['building','height','building:levels'] if k in tags})
        for key,union in unions.items():
            overlap=transform(to_utm,geom.intersection(union)).area
            props[key+'_overlap_m2']=round(overlap,2)
            props[key+'_overlap_pct']=round(100*overlap/area,2)
        features.append({'type':'Feature','geometry':mapping(geom),'properties':props})
        rows.append(props)
    buildings={'type':'FeatureCollection','features':features}
    folder=ROOT/'data/planning'
    (folder/'osm_buildings.geojson').write_text(json.dumps(buildings),encoding='utf-8')
    provenance={'source':'https://www.openstreetmap.org/copyright',
        'license':'ODbL; OpenStreetMap contributors',
        'overpass_query':'[out:json][timeout:45];way["building"](29.39,-98.57,29.46,-98.50);out geom;',
        'overpass_endpoint':'https://overpass-api.de/api/interpreter',
        'osm_metadata':raw.get('osm3s'),
        'raw_sha256':hashlib.sha256(args.overpass_json.read_bytes()).hexdigest(),
        'limitations':'Ways only, excludes multipolygon relations. Incomplete coverage. Draft polygon overlap is not predicted flood depth or a safety designation.'}
    (folder/'osm_buildings.source.json').write_text(json.dumps(provenance,indent=2))
    pd.DataFrame(rows).to_csv(ROOT/'results/building_draft_screening.csv',index=False)
    m=folium.Map(location=[29.425,-98.535],zoom_start=13,tiles='OpenStreetMap')
    colors={'draft_annual':'#1565c0','draft_future':'#9c27b0'}
    for key,union in unions.items():
        folium.GeoJson(mapping(union),name=key.replace('_',' ').title(),
            style_function=lambda f,c=colors[key]:{'color':c,'weight':1,'fillOpacity':0.22}).add_to(m)
    folium.GeoJson(buildings,name='OSM buildings (incomplete)',
        style_function=lambda f:{'color':'#d84315' if f['properties']['draft_annual_overlap_m2']>0 else '#455a64','weight':1,'fillOpacity':0.5},
        tooltip=folium.GeoJsonTooltip(fields=['osm_way_id','footprint_m2','draft_annual_overlap_pct','draft_future_overlap_pct'])).add_to(m)
    candidates=json.loads((ROOT/'results/candidate_screening.geojson').read_text())
    folium.GeoJson(candidates,name='Terrain investigation points; feasibility unknown').add_to(m)
    folium.LayerControl().add_to(m)
    m.get_root().html.add_child(folium.Element('<div style="position:fixed;bottom:20px;left:10px;z-index:9999;background:white;padding:12px;max-width:440px">San Antonio screening: SARA DRAFT polygons, not effective FEMA mapping. OSM coverage is incomplete. No flood depths or approved building/tunnel sites. Map requires internet. © OpenStreetMap contributors, ODbL.</div>'))
    m.save(str(ROOT/'Planning_Map.html'))
    ns='http://www.opengis.net/kml/2.2'; ET.register_namespace('',ns)
    def elem(parent,name,text=None):
        child=ET.SubElement(parent,'{'+ns+'}'+name)
        if text is not None: child.text=str(text)
        return child
    kml=ET.Element('{'+ns+'}kml');doc=elem(kml,'Document')
    elem(doc,'name','San Antonio draft screening — not design approval')
    elem(doc,'description',provenance['limitations']+' © OpenStreetMap contributors, ODbL. Flood polygons: SARA draft.')
    def geometry(parent,g):
        if g.geom_type=='Polygon':
            poly=elem(parent,'Polygon');elem(poly,'altitudeMode','clampToGround')
            for name,ring in [('outerBoundaryIs',g.exterior)]+[('innerBoundaryIs',r) for r in g.interiors]:
                linear=elem(elem(poly,name),'LinearRing')
                elem(linear,'coordinates',' '.join(f'{x},{y},0' for x,y in ring.coords))
        elif g.geom_type=='Point': elem(elem(parent,'Point'),'coordinates',f'{g.x},{g.y},0')
        elif hasattr(g,'geoms'):
            multi=elem(parent,'MultiGeometry')
            for part in g.geoms: geometry(multi,part)
    for name,fc in [('OSM buildings',buildings),('Investigation points',candidates)]:
        folder_el=elem(doc,'Folder');elem(folder_el,'name',name)
        for f in fc['features']:
            mark=elem(folder_el,'Placemark');elem(mark,'name',f['properties'].get('osm_way_id',f['properties'].get('rank','Point')))
            elem(mark,'description',json.dumps(f['properties']));geometry(mark,shape(f['geometry']))
    for key,g in unions.items():
        mark=elem(doc,'Placemark');elem(mark,'name',key);geometry(mark,g)
    with zipfile.ZipFile(ROOT/'SanAntonio_Planning.kmz','w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('doc.kml',ET.tostring(kml,encoding='utf-8',xml_declaration=True))
    summary={'building_ways_screened':len(rows),
        'draft_annual_overlap_buildings':sum(r['draft_annual_overlap_m2']>0 for r in rows),
        'draft_future_overlap_buildings':sum(r['draft_future_overlap_m2']>0 for r in rows),
        'limitations':provenance['limitations']}
    (ROOT/'results/planning_summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
