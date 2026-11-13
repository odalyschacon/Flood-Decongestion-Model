"""Run and cache real image-pair analysis through the supplied compatible API."""
import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
from PIL import Image
from openai import OpenAI
from floodlab import ROOT, audit_images

DEFAULT_BASE_URL = 'http://10.246.100.230/v1'
DEFAULT_MODEL = 'qwen3-vl-8b-instruct'
PROMPT = '''Compare image A (first, baseline) and image B (second, response).
Describe two concrete visible changes involving water, roads, vegetation or buildings,
then state one important uncertainty. If flooding is unclear, say so. Ordinary water
in a channel alone is not evidence of flooding. Do not infer flood depth, damage costs,
the number of homes protected, or suitable construction locations. These images show
the Houston area, NOT San Antonio. Keep the answer under 170 words. Do not give engineering advice.'''


def image_content(path):
    with Image.open(path) as image:
        image = image.convert('RGB')
        image.thumbnail((1024,1024))
        buffer = io.BytesIO()
        image.save(buffer,format='JPEG',quality=90)
    return {'type':'image_url','image_url':{'url':'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()}}


def run(api_key=None, refresh=False):
    key=api_key or os.environ.get('FLOODLAB_API_KEY') or os.environ.get('OPENAI_API_KEY')
    if not key:
        raise ValueError('Set FLOODLAB_API_KEY or run python api_evidence.py for a hidden key prompt')
    base_url=os.environ.get('FLOODLAB_BASE_URL',DEFAULT_BASE_URL)
    model=os.environ.get('FLOODLAB_MODEL',DEFAULT_MODEL)
    images,_=audit_images();images=images.set_index('image_id')
    folder=ROOT/'results/api_evidence';folder.mkdir(parents=True,exist_ok=True)
    outputs=[]
    with OpenAI(base_url=base_url,api_key=key,timeout=120,max_retries=0) as client:
        available=[m.id for m in client.models.list().data]
        if model not in available: raise ValueError(f'Model {model} unavailable; served models: {available}')
        for pair in ['TX001','TX002','TX003']:
            ids=[pair+'_2016_NAIP',pair+'_2017_NOAA']
            paths=[ROOT/'data/texas'/images.loc[i,'image_path'] for i in ids]
            hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
            target=folder/(pair+'.json')
            if target.exists() and not refresh:
                cached=json.loads(target.read_text(encoding='utf-8'))
                if (cached.get('image_sha256')==hashes and cached.get('prompt')==PROMPT
                        and cached.get('model_requested')==model and cached.get('base_url')==base_url):
                    outputs.append(cached);print(pair+': cached live result',flush=True);continue
            reply=client.chat.completions.create(model=model,temperature=0,max_tokens=600,
                messages=[{'role':'system','content':'Describe only visible evidence. Preserve uncertainty and distinguish observation from inference.'},
                          {'role':'user','content':[{'type':'text','text':PROMPT}]+[image_content(p) for p in paths]}])
            answer=(reply.choices[0].message.content or '').strip()
            if not answer: raise RuntimeError('API returned an empty analysis')
            if reply.choices[0].finish_reason=='length': raise RuntimeError('API answer truncated; increase token budget')
            record={'status':'live_api_inference_completed','human_reviewed':False,
                    'pair':pair,'image_ids':ids,'image_sha256':hashes,
                    'locality':str(images.loc[ids[0],'locality']),
                    'dates':[str(images.loc[i,'acquisition_date']) for i in ids],
                    'base_url':base_url,'model_requested':model,'model_returned':reply.model,
                    'request_id':reply.id,'completed_utc':datetime.now(timezone.utc).isoformat(),
                    'prompt':PROMPT,'answer':answer,'finish_reason':reply.choices[0].finish_reason,
                    'usage':reply.usage.model_dump() if reply.usage else None,
                    'image_preprocessing':'RGB JPEG, max side 1024 px, quality 90',
                    'limitations':'Unreviewed model evidence, not ground-truth labels or hydraulic predictions.'}
            target.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
            outputs.append(record);print(pair+': live API analysis saved',flush=True)
    (ROOT/'results/api_status.json').write_text(json.dumps({
        'status':'live_api_inference_completed','base_url':base_url,'model':model,
        'pairs_completed':len(outputs),'earth2_used':False,
        'execution':'Laptop client calling user-specified API; no local GPU setup'},indent=2))
    return outputs


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh',action='store_true',help='Make new API calls instead of reusing matching results')
    args=parser.parse_args()
    key=os.environ.get('FLOODLAB_API_KEY') or os.environ.get('OPENAI_API_KEY') or getpass.getpass('Workshop API key (hidden): ')
    run(key,refresh=args.refresh)
