"""Optional GPU runner, based on NVIDIA Earth2Studio 0.18.0 diagnostic workflow.

Live-validated on NVIDIA GB10 with CUDA 13; not intended for the Intel laptop.
Reference: https://nvidia.github.io/earth2studio/0.18.0/examples/01_getting_started/02_diagnostic_workflow/
"""
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial-time',required=True,help='Available GFS initialization, YYYY-MM-DDTHH:00:00Z')
    parser.add_argument('--steps',type=int,default=4,help='Six-hour steps, default 24-hour forecast')
    parser.add_argument('--output',default='data/earth2_rainfall.csv')
    parser.add_argument('--model-directory',type=Path,help='Optional directory of preloaded official fcn/ and precip/ packages')
    args=parser.parse_args()
    t=datetime.fromisoformat(args.initial_time.replace('Z','+00:00'))
    if t.tzinfo is None: raise ValueError('Initialization must include UTC timezone')
    t=t.astimezone(timezone.utc)
    if t.hour%6 or t.minute or t.second or not 1<=args.steps<=40:
        raise ValueError('Use a 00/06/12/18 UTC initialization and 1–40 steps')
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('Run this optional script on the NVIDIA GB10; CUDA is unavailable here')
    import numpy as np
    import pandas as pd
    import earth2studio
    import earth2studio.run as run
    from earth2studio.data import GFS
    from earth2studio.io import ZarrBackend
    from earth2studio.models.px import FCN
    from earth2studio.models.dx import PrecipitationAFNO
    from earth2studio.models.auto import Package
    from collections import OrderedDict
    from floodlab import read_rainfall_csv

    # The nearest 0.25-degree grid point to the pilot center, not neighborhood resolution.
    lat,lon=29.5,261.5
    print('Loading FourCastNet weights',flush=True)
    prognostic=FCN.load_model(Package(str(args.model_directory/'fcn')) if args.model_directory else FCN.load_default_package())
    print('Loading PrecipitationAFNO weights',flush=True)
    diagnostic=PrecipitationAFNO.load_model(Package(str(args.model_directory/'precip')) if args.model_directory else PrecipitationAFNO.load_default_package())
    print('Starting GFS initialization and GPU inference',flush=True)
    io=run.diagnostic([t.replace(tzinfo=None).isoformat()],args.steps,prognostic,diagnostic,
                      GFS(),ZarrBackend(),
                      output_coords=OrderedDict(lat=np.array([lat]),lon=np.array([lon])),
                      device=torch.device('cuda'))
    tp=np.asarray(io['tp'][:]).reshape(-1)
    if len(tp)!=args.steps+1 or not np.isfinite(tp).all() or (tp<0).any():
        raise ValueError('Unexpected precipitation output')
    # AFNO returns six-hour accumulation ENDING at validity time, in metres.
    # Lead zero describes a preceding interval: exclude it from the future event.
    rows=[]
    for step in range(1,args.steps+1):
        end=t+timedelta(hours=6*step)
        rows.append({'start_utc':(end-timedelta(hours=6)).isoformat(),
                     'end_utc':end.isoformat(),'rain_mm':float(tp[step]*1000),
                     'source':'NVIDIA Earth2Studio','model':'FCN + PrecipitationAFNO',
                     'member':'deterministic','latitude':lat,'longitude':lon-360})
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(rows).to_csv(target,index=False)
    read_rainfall_csv(target)
    target.with_suffix('.provenance.json').write_text(json.dumps({
        'earth2studio_version':getattr(earth2studio,'__version__','unknown'),
        'initial_time_utc':t.isoformat(),'gpu':torch.cuda.get_device_name(0),
        'grid_degrees':.25,'rainfall_units':'mm per six-hour interval',
        'initial_conditions':'GFS','status':'live model inference completed',
        'torch_version':torch.__version__,'cuda_version':torch.version.cuda,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'forecast_steps':args.steps,
        'limitations':'Coarse deterministic forecast; no local calibration or urban downscaling'
    },indent=2))
    print(target)

if __name__=='__main__': main()
