"""Run the cached San Antonio pilot without GPU, API key or new packages."""
import base64
import html
import json
from pathlib import Path
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from floodlab import ROOT, audit_images, terrain_routing, select_candidates, storage_scenario
from geo import to_utm, to_lonlat


def load_dem():
    with Image.open(ROOT/'data/city/elevation.tif') as im:
        z=np.array(im,dtype=float)
        scale=im.tag_v2[33550]; tie=im.tag_v2[33922]
        keys=im.tag_v2[34735]
        records=[keys[i:i+4] for i in range(4,len(keys),4)]
        if (3072,0,1,32614) not in records:
            raise ValueError('Expected UTM zone 14N raster in metres')
        if (1025,0,1,1) not in records:
            raise ValueError('Expected RasterPixelIsArea georeferencing')
        dx,dy=scale[:2];xmin=tie[3]-tie[0]*dx;ymax=tie[4]+tie[1]*dy
    if not np.isfinite(z).all() or (z < -1000).any(): raise ValueError('DEM has missing cells')
    return z,dx,dy,xmin,ymax


def city_layers():
    return {p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'data/city').glob('*.geojson')}


def candidate_network(candidates,receiver,order,area):
    """Compress routing to selected collectors plus unconstrained boundary exits."""
    cells=candidates.cell.astype(int).tolist(); idx={v:i for i,v in enumerate(cells)}
    first=np.full(len(receiver),-1,dtype=int)
    # order visits downstream parent before child.
    for cell in order:
        if int(cell) in idx: first[cell]=idx[int(cell)]
        elif receiver[cell]>=0: first[cell]=first[receiver[cell]]
    exclusive=np.bincount(first[first>=0],minlength=len(cells))*area
    downstream=[]
    for cell in cells:
        parent=receiver[cell]
        downstream.append(int(first[parent]) if parent>=0 else -1)
    position={int(c):i for i,c in enumerate(order)}
    process=sorted(range(len(cells)),key=lambda i:position[cells[i]],reverse=True)
    return {'exclusive_area_m2':exclusive.tolist(),'downstream':downstream,
            'process':process,'total_area_m2':len(receiver)*area}


def main():
    results=ROOT/'results';results.mkdir(exist_ok=True)
    images,audit=audit_images()
    (results/'data_audit.json').write_text(json.dumps(audit,indent=2))
    z,dx,dy,xmin,ymax=load_dem()
    filled,receiver,order,acc=terrain_routing(z)
    candidates=select_candidates(z,acc,dx,dy)
    candidates['easting_m']=xmin+(candidates.col+.5)*dx
    candidates['northing_m']=ymax-(candidates.row+.5)*dy
    candidates['longitude'],candidates['latitude']=to_lonlat(candidates.easting_m,candidates.northing_m)
    layers=city_layers()
    for name in ['StormInlets','LowWaterCrossings']:
        layer=layers.get(name,{'features':[]})
        points=[f['geometry']['coordinates'][:2] for f in layer['features'] if f.get('geometry') and f['geometry']['type']=='Point']
        if points:
            xy=np.asarray(points);px,py=to_utm(xy[:,0],xy[:,1])
            candidates['nearest_'+name+'_m']=cKDTree(np.column_stack([px,py])).query(candidates[['easting_m','northing_m']])[0]
        else: candidates['nearest_'+name+'_m']=np.nan
    candidates.to_csv(results/'candidate_screening.csv',index=False)
    features=[]
    for _,row in candidates.iterrows():
        properties=json.loads(row.to_json())
        features.append({'type':'Feature','geometry':{'type':'Point','coordinates':[row.longitude,row.latitude]},'properties':properties})
    (results/'candidate_screening.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},indent=2))
    scenarios=[]
    for rain in [25,50,100,150]:
        for capacity in [0,500,2000,5000]:
            collectors={int(i):capacity for i in candidates.cell}
            result=storage_scenario(receiver,order,dx*dy,rain,.6,collectors)
            scenarios.append({'rain_mm':rain,'runoff_coefficient':.6,'capacity_per_site_m3':capacity,
                              **{k:v for k,v in result.items() if k!='captured_by_cell'}})
    scenarios=pd.DataFrame(scenarios)
    scenarios.to_csv(results/'storage_scenarios.csv',index=False)
    if scenarios.mass_balance_error_m3.abs().max()>1e-5: raise AssertionError('Water balance failed')
    network=candidate_network(candidates,receiver,order,dx*dy)
    (results/'collector_network.json').write_text(json.dumps(network,indent=2))
    np.savez_compressed(results/'routing.npz',receiver=receiver,order=order,cell_area_m2=dx*dy)
    extent=[xmin,xmin+z.shape[1]*dx,ymax-z.shape[0]*dy,ymax]
    fig,axes=plt.subplots(1,2,figsize=(15,8),layout='constrained')
    for ax in axes:
        ax.set_xlabel('UTM 14N easting (m)');ax.set_ylabel('Northing (m)')
        ax.ticklabel_format(style='plain',useOffset=False)
    im=axes[0].imshow(z,extent=extent,cmap='terrain',origin='upper')
    fig.colorbar(im,ax=axes[0],shrink=.65,label='Elevation (m; USGS source datum)')
    axes[0].set_title('San Antonio west-side pilot: terrain + city drains')
    colors={'StormwaterUnderground':'#1b5eaa','StormChannels':'#142c41','StormInlets':'#e76f51','LowWaterCrossings':'#dc2626'}
    for name,layer in layers.items():
        labelled=False
        for feature in layer['features']:
            g=feature.get('geometry')
            if not g: continue
            sequences=([g['coordinates']] if g['type']=='LineString' else g['coordinates'] if g['type']=='MultiLineString' else [])
            if g['type']=='Point': sequences=[[g['coordinates']]]
            for seq in sequences:
                a=np.asarray(seq);xx,yy=to_utm(a[:,0],a[:,1])
                axes[0].plot(xx,yy,'.' if g['type']=='Point' else '-',color=colors.get(name,'gray'),markersize=2,linewidth=.6,alpha=.65,label=name if not labelled else None)
                labelled=True
    axes[0].legend(fontsize=8,loc='upper right')
    im=axes[1].imshow(np.log10(acc*dx*dy),extent=extent,cmap='Blues',origin='upper')
    fig.colorbar(im,ax=axes[1],shrink=.65,label='log10 upstream area within crop (m²)')
    axes[1].set_title('Terrain convergence: investigation points, not approved sites')
    for _,c in candidates.iterrows():
        axes[1].scatter(c.easting_m,c.northing_m,s=100,facecolor='#e76f51',edgecolor='white')
        axes[1].annotate(str(int(c['rank'])),(c.easting_m,c.northing_m),ha='center',va='center',fontsize=8,color='white')
    fig.savefig(results/'pilot_map.png',dpi=140);plt.close(fig)
    # Honest sample gallery: geographic domain differs from the San Antonio pilot.
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    for ax,image_id in zip(axes,['TX001_2016_NAIP','TX001_2017_NOAA']):
        row=images.set_index('image_id').loc[image_id]
        with Image.open(ROOT/'data/texas'/row.image_path) as im: ax.imshow(im)
        ax.set_title(row.acquisition_date+' | '+row.source_agency);ax.axis('off')
    fig.suptitle('Dataset evidence: Bear Creek / west Houston (not San Antonio)')
    fig.savefig(results/'evidence_pair.png',dpi=120);plt.close(fig)
    write_report(results,audit,candidates,network,layers,dx,dy)
    print(json.dumps({'audit':audit,'city_feature_counts':{k:len(v['features']) for k,v in layers.items()},
                      'cell_size_m':[dx,dy],'candidates':len(candidates),
                      'max_mass_balance_error_m3':float(scenarios.mass_balance_error_m3.abs().max())},indent=2))


def write_report(results,audit,candidates,network,layers,dx,dy):
    def data_image(name): return 'data:image/png;base64,'+base64.b64encode((results/name).read_bytes()).decode()
    table=candidates[['rank','latitude','longitude','upstream_area_within_crop_m2','slope_degrees','nearest_StormInlets_m']].round(3).to_html(index=False,border=0)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>San Antonio Flood Lab — pilot screening</title><style>
*{box-sizing:border-box}body{margin:0;background:#edf2f4;color:#132d3f;font:16px/1.5 system-ui,sans-serif}main{max-width:1180px;margin:auto;padding:32px}h1{font-size:44px;line-height:1.12;margin:12px 0}h2{margin:0 0 12px}p{max-width:950px}.tag{color:#167d8d;letter-spacing:2px;font-size:12px;font-weight:800}.card{background:white;border:1px solid #dce5e9;border-radius:15px;padding:24px;margin:22px 0}.notice{border-left:5px solid #e76f51;padding:14px;background:#fff5ec}img{max-width:100%;height:auto}label{display:block;margin:16px 0}input{width:250px;max-width:100%}strong.value{display:inline-block;min-width:80px;color:#087d87}.metrics{display:flex;gap:20px;flex-wrap:wrap}.metric{flex:1;min-width:180px;padding:15px;background:#eaf4f5;border-radius:10px}.metric b{display:block;font-size:30px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}td,th{text-align:left;padding:10px;border-bottom:1px solid #e0e8ed}a{color:#087d87}.small{font-size:13px;color:#526774}</style>
<main><div class="tag">UTSA DATATHON / WORKING PROTOTYPE</div><h1>Where could we capture stormwater?</h1>
<p>A San Antonio terrain-screening pilot with real USGS elevation and city drainage data, historical Texas image evidence, and a transparent collector-storage experiment.</p>
<div class="notice"><b>Current result:</b> investigation points, not optimal construction sites. Rainfall below is a user-defined scenario. Earth-2 has not run. This model does not predict flood depth, damage, homes protected, tunnel performance, or construction suitability.</div>
<section class="card"><h2>1. Follow the terrain</h2><p>West-side pilot bounding box: −98.57 to −98.50 longitude, 29.39 to 29.46 latitude. Points rank by upstream area within the cropped raster, with slopes below 8° and a 350 m minimum separation. Current pipes and channels are context overlays; their hydraulic operation is not modeled.</p><img alt="Elevation, drainage infrastructure, and terrain screening points" src="MAP"><p class="small">UTM zone 14N, approximately CELL metres per cell. This is a cropped pilot, not a full watershed: external inflows are omitted. Sink filling and a single-flow drainage tree simplify urban surface flow. No parcel, building, utility-conflict, soil, habitat, or ownership screening has been applied.</p></section>
<section class="card"><h2>2. Compare collector storage assumptions</h2><p>Event runoff volume = rainfall × area × runoff coefficient. All eight candidate collectors receive the same assumed storage capacity. Collectors fill once, and downstream collectors receive only water not already captured. Capture is an optimistic volume bound because inlet rates are unlimited.</p>
<label>Event rainfall: <strong class="value" id="rainValue"></strong><input id="rain" aria-label="Event rainfall in millimetres" type="range" min="0" max="200" value="50" step="5"></label>
<label>Runoff coefficient: <strong class="value" id="coefValue"></strong><input id="coef" aria-label="Runoff coefficient" type="range" min="0" max="1" value="0.6" step="0.05"></label>
<label>Storage per collector: <strong class="value" id="capacityValue"></strong><input id="capacity" aria-label="Storage per collector in cubic metres" type="range" min="0" max="10000" value="2000" step="500"></label>
<div class="metrics"><div class="metric">Generated runoff<b id="generated"></b></div><div class="metric">Captured volume<b id="stored"></b></div><div class="metric">Capture fraction<b id="fraction"></b></div></div><p id="residual"></p><p class="small">These are scenario assumptions, not observed rainfall or Earth-2 predictions. Stored water must eventually be drained or reused; this model does not estimate peak-flow reduction.</p></section>
<section class="card"><h2>3. Inspect the candidate coordinates</h2><div class="scroll">TABLE</div><p class="small">Upstream area is in m²; nearest-inlet distance is in metres and does not imply available sewer capacity. Multiple candidates may lie along the same drainage path. Low-water crossing locations are contextual evidence, not records of flooding during this scenario.</p></section>
<section class="card"><h2>4. Keep imagery evidence geographically honest</h2><img alt="Before and response aerial images from Bear Creek, Houston" src="PAIR"><p>The provided metadata contains 1,204 Texas aerial images and 273 fields. None lie within our broad San Antonio bounding box. Human flood labels are blank. Six images (three before/after pairs) are cached for demonstration; all metadata is retained. Image review supports evidence gathering, not calibrated flood-depth estimation. Differences in season, year, and imaging affect comparisons.</p></section>
<section class="card"><h2>5. Earth-2 and construction: next integration steps</h2><p>The included optional Earth2Studio runner couples FourCastNet with PrecipitationAFNO and exports rainfall for the pilot. It requires a compatible NVIDIA environment and model downloads. The forecast grid is 0.25°, much coarser than a neighborhood. Forecast rainfall must be evaluated against local observations; applying it to fine terrain is not weather downscaling.</p><p>For tunnel and new-construction comparisons, assemble pipe topology, invert elevations, capacities, outfalls and downstream boundary conditions; buildings and parcels; soils and protected areas; and a complete watershed DEM. Calibrate an EPA SWMM or coupled surface-flow model before optimizing cost and residential exposure reduction. New construction also adds runoff and must be evaluated for downstream impacts.</p></section>
<section class="card"><h2>Sources and reproducibility</h2><p><a href="https://github.com/jennifer-fowler/GB10competition">Workshop repository</a> · <a href="https://huggingface.co/datasets/jennifer-fowler/UTSA-flood-images">UTSA flood data (CC BY-NC 4.0)</a> · <a href="https://www.sanantonio.gov/GIS/GISdata">City GIS</a> · <a href="https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer">USGS 3DEP</a> · <a href="https://nvidia.github.io/earth2studio/0.18.0/examples/01_getting_started/02_diagnostic_workflow/">NVIDIA diagnostic workflow</a> · <a href="https://www.epa.gov/water-research/storm-water-management-model-swmm">EPA SWMM</a></p><p class="small">Per-file source URLs and retrieval records accompany downloaded assets. Current snapshots are not historical infrastructure reconstructions. Open START_HERE.md for the notebook, scripts, assumptions, and remaining blockers.</p></section></main>
<script>const net=NETWORK;const ids=['rain','coef','capacity'];function update(){const rain=+document.getElementById('rain').value,coef=+document.getElementById('coef').value,capacity=+document.getElementById('capacity').value;document.getElementById('rainValue').textContent=rain+' mm';document.getElementById('coefValue').textContent=coef.toFixed(2);document.getElementById('capacityValue').textContent=capacity+' m³';let incoming=net.exclusive_area_m2.map(a=>a*rain/1000*coef),stored=0;for(const i of net.process){const take=Math.min(capacity,incoming[i]);stored+=take;const d=net.downstream[i];if(d>=0)incoming[d]+=incoming[i]-take;}const generated=net.total_area_m2*rain/1000*coef;const fmt=x=>Math.round(x).toLocaleString()+' m³';document.getElementById('generated').textContent=fmt(generated);document.getElementById('stored').textContent=fmt(stored);document.getElementById('fraction').textContent=(generated?100*stored/generated:0).toFixed(2)+'%';document.getElementById('residual').textContent='Remaining event volume at cropped-domain outlets: '+fmt(generated-stored)+'.';}ids.forEach(id=>document.getElementById(id).addEventListener('input',update));update();</script></html>'''
    evidence=[]
    for path in sorted((results/'api_evidence').glob('TX*.json')):
        record=json.loads(path.read_text(encoding='utf-8'))
        if record.get('status')!='live_api_inference_completed': continue
        evidence.append('<article><h3>'+html.escape(record['pair']+' — '+record['locality'])+'</h3>'
                        '<p class="small">'+html.escape(record['model_returned']+' | '+record['completed_utc'])+'</p>'
                        '<p style="white-space:pre-wrap">'+html.escape(record['answer'])+'</p></article>')
    api_section='<section class="card"><h2>Live AI evidence review</h2>'
    if evidence:
        api_section+='<p>Three image pairs were analyzed through the supplied OpenAI-compatible API. The responses below are actual cached model outputs, not examples. They describe Houston imagery and do not determine the San Antonio site ranking.</p>'+''.join(evidence)
        api_section+='<p class="small">AI observations have not been human-validated. Source images, prompts, timestamps, model IDs and image hashes are retained in results/api_evidence. No API credential is embedded in this report.</p>'
    else:
        api_section+='<p>No successful API image analyses are cached. Run api_evidence.py to generate them.</p>'
    api_section+='</section>'
    page=page.replace('<section class="card"><h2>5. Earth-2 and construction: next integration steps</h2>',api_section+'<section class="card"><h2>5. Construction: next validation steps</h2>')
    forecast_path=results/'forecast_storage_scenario.json'
    if forecast_path.exists():
        forecast=json.loads(forecast_path.read_text())
        forecast_section=('<section class="card"><h2>Completed Earth-2 forecast on NVIDIA GB10</h2>'
            '<p>FourCastNet + PrecipitationAFNO, initialized '+html.escape(forecast['start_utc'])+
            ', through '+html.escape(forecast['end_utc'])+'. This forecast was generated after initialization; it is not an operational warning.</p>'
            f'<p><b>{forecast["rain_mm"]:.3f} mm</b> total rainfall at 29.5°N, 98.5°W on the 0.25° model grid. '
            f'Assuming runoff coefficient {forecast["runoff_coefficient_assumed"]} and eight initially empty '
            f'{forecast["capacity_per_collector_m3_assumed"]:,.0f} m³ collectors, the cropped-terrain scenario stores '
            f'{forecast["stored_m3"]:,.0f} m³ of {forecast["generated_runoff_m3"]:,.0f} m³ generated runoff.</p>'
            '<p>This is event-volume accounting, not a flood-depth, tunnel-performance or homes-protected prediction. '
            'The sliders above remain independent hypothetical scenarios.</p>'
            '<p><a href="results/earth2_rainfall.csv">Forecast CSV</a> · '
            '<a href="results/earth2_rainfall.provenance.json">Run provenance</a> · '
            '<a href="Planning_Map.html">Buildings and draft floodplain</a> · '
            '<a href="SanAntonio_Planning.kmz">Google Earth export</a></p></section>')
        page=page.replace('Earth-2 has not run.', 'A completed GB10 Earth-2 forecast is reported separately below.')
        page=page.replace('<section class="card"><h2>5. Construction:',forecast_section+'<section class="card"><h2>5. Construction:')
    page=page.replace('MAP',data_image('pilot_map.png')).replace('PAIR',data_image('evidence_pair.png')).replace('TABLE',table).replace('NETWORK',json.dumps(network)).replace('CELL',f'{dx:.1f} × {dy:.1f}')
    (ROOT/'FloodLab_Report.html').write_text(page,encoding='utf-8')

if __name__=='__main__': main()
