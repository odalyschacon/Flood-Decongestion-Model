"""Apply one verified rainfall series to the existing event-volume screening."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from floodlab import ROOT, read_rainfall_csv, storage_scenario


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('rainfall_csv', type=Path)
    p.add_argument('--runoff-coefficient', type=float, default=0.6)
    p.add_argument('--capacity-m3', type=float, default=2000)
    args = p.parse_args()
    rain = read_rainfall_csv(args.rainfall_csv)
    routing = np.load(ROOT/'results/routing.npz')
    candidates = pd.read_csv(ROOT/'results/candidate_screening.csv')
    collectors = {int(c): args.capacity_m3 for c in candidates.cell}
    result = storage_scenario(routing['receiver'], routing['order'],
        float(routing['cell_area_m2']), float(rain.rain_mm.sum()),
        args.runoff_coefficient, collectors)
    if abs(result['mass_balance_error_m3']) > max(1e-6, result['generated_runoff_m3']*1e-9):
        raise RuntimeError('Event-volume conservation failed')
    result.update({
        'rainfall_sha256': hashlib.sha256(args.rainfall_csv.read_bytes()).hexdigest(),
        'rain_mm': float(rain.rain_mm.sum()),
        'start_utc': rain.start_utc.iloc[0].isoformat(),
        'end_utc': rain.end_utc.iloc[-1].isoformat(),
        'weather_model': str(rain.model.iloc[0]),
        'runoff_coefficient_assumed': args.runoff_coefficient,
        'capacity_per_collector_m3_assumed': args.capacity_m3,
        'limitations': 'Uniform rainfall across cropped terrain; collectors assumed empty at event start. No external runoff, travel times, pipe hydraulics, flood depths, or estimates of homes protected.'})
    target = ROOT/'results/forecast_storage_scenario.json'
    target.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
