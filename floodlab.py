"""Transparent terrain screening and storage scenarios; not a hydraulic solver."""
from pathlib import Path
import heapq
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent


def audit_images(path=ROOT / 'data/texas/image_metadata.csv'):
    df = pd.read_csv(path, dtype='string', keep_default_na=False)
    if df.image_id.duplicated().any():
        raise ValueError('Duplicate image IDs')
    lat = pd.to_numeric(df.latitude, errors='coerce')
    lon = pd.to_numeric(df.longitude, errors='coerce')
    in_sa = lat.between(29.2, 29.8) & lon.between(-98.85, -98.2)
    return df, {
        'images': len(df), 'columns': len(df.columns),
        'san_antonio_bbox_images': int(in_sa.sum()),
        'missing_coordinates': int((lat.isna() | lon.isna()).sum()),
        'human_flood_labels': int(df.flood_visible.ne('').sum()),
        'localities': df.locality.value_counts().to_dict(),
        'sqlite_available': (path.parent / 'observations.sqlite').exists(),
    }


def terrain_routing(elevation):
    """Priority-flood drainage tree. Fill sinks; route each cell to its visited parent.

    Single-flow screening approximation. Flats follow deterministic heap order.
    All raster edges are open outlets; upstream area outside the crop is excluded.
    Returns filled elevation, receiver, processing order, accumulated cell count.
    """
    z = np.asarray(elevation, dtype=float)
    if z.ndim != 2 or min(z.shape) < 3 or not np.isfinite(z).all():
        raise ValueError('DEM must be finite, 2D and at least 3 by 3')
    h, w = z.shape
    filled = z.copy().ravel()
    seen = np.zeros(z.size, dtype=bool)
    receiver = np.full(z.size, -1, dtype=int)
    heap, order = [], []
    for r in range(h):
        for c in range(w):
            if r in (0, h - 1) or c in (0, w - 1):
                i = r * w + c
                seen[i] = True
                heapq.heappush(heap, (filled[i], i))
    while heap:
        level, i = heapq.heappop(heap)
        order.append(i)
        r, c = divmod(i, w)
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if not (0 <= rr < h and 0 <= cc < w):
                    continue
                j = rr * w + cc
                if seen[j]:
                    continue
                seen[j] = True
                receiver[j] = i
                filled[j] = max(level, filled[j])
                heapq.heappush(heap, (filled[j], j))
    counts = np.ones(z.size)
    for i in reversed(order):
        if receiver[i] >= 0:
            counts[receiver[i]] += counts[i]
    return filled.reshape(z.shape), receiver, np.asarray(order), counts.reshape(z.shape)


def storage_scenario(receiver, order, cell_area_m2, rain_mm, runoff_coefficient,
                     collectors=None):
    """Event-volume accounting. Each collector stores up to capacity once per event.

    No travel time, inlet-rate limit, sewer capacity, backwater or flood depth.
    Cascaded collectors see residual volume only, avoiding double-counting.
    """
    if not math.isfinite(rain_mm) or rain_mm < 0:
        raise ValueError('Rain must be finite and nonnegative')
    if not math.isfinite(runoff_coefficient) or not 0 <= runoff_coefficient <= 1:
        raise ValueError('Runoff coefficient must be between zero and one')
    if not math.isfinite(cell_area_m2) or cell_area_m2 <= 0:
        raise ValueError('Cell area must be positive')
    collectors = collectors or {}
    for i, capacity in collectors.items():
        if not isinstance(i, (int, np.integer)) or not 0 <= i < len(receiver):
            raise ValueError('Collector index outside raster')
        if not math.isfinite(capacity) or capacity < 0:
            raise ValueError('Storage must be finite and nonnegative')
    incoming = np.full(len(receiver), rain_mm / 1000 * cell_area_m2 * runoff_coefficient)
    captured, outflow = {}, 0.0
    for i in reversed(order):
        take = min(incoming[i], collectors.get(int(i), 0.0))
        if i in collectors:
            captured[int(i)] = float(take)
        remaining = incoming[i] - take
        if receiver[i] >= 0:
            incoming[receiver[i]] += remaining
        else:
            outflow += remaining
    generated = rain_mm / 1000 * cell_area_m2 * runoff_coefficient * len(receiver)
    return {'generated_runoff_m3': generated, 'stored_m3': sum(captured.values()),
            'boundary_outflow_m3': outflow, 'captured_by_cell': captured,
            'mass_balance_error_m3': generated - outflow - sum(captured.values())}


def select_candidates(z, accumulation, dx, dy, count=8, separation_m=350):
    """Rank terrain convergence only; parcel feasibility is not established."""
    gy, gx = np.gradient(z, dy, dx)
    slope = np.degrees(np.arctan(np.hypot(gx, gy)))
    valid = np.ones(z.shape, dtype=bool)
    # Exclude 250 m at crop edges, where truncation is particularly problematic.
    nr, nc = int(np.ceil(250 / dy)), int(np.ceil(250 / dx))
    valid[:nr] = valid[-nr:] = False
    valid[:, :nc] = valid[:, -nc:] = False
    valid &= slope < 8
    candidates = np.flatnonzero(valid.ravel())
    candidates = candidates[np.argsort(-accumulation.ravel()[candidates], kind='stable')]
    selected = []
    for i in candidates:
        r, c = divmod(int(i), z.shape[1])
        if any(np.hypot((r-a['row'])*dy, (c-a['col'])*dx) < separation_m for a in selected):
            continue
        selected.append({'rank': len(selected)+1, 'cell': int(i), 'row': r, 'col': c,
                         'upstream_area_within_crop_m2': accumulation[r,c]*dx*dy,
                         'terrain_elevation_m': z[r,c], 'slope_degrees': slope[r,c],
                         'status': 'terrain screening only; site feasibility unknown'})
        if len(selected) >= count:
            break
    return pd.DataFrame(selected)


def read_rainfall_csv(path):
    """Common handoff for observed or Earth-2 precipitation, with explicit provenance.

    Required rows: nonoverlapping intervals for ONE location and ONE ensemble member.
    rain_mm is interval accumulation, never cumulative-since-initialization or a rate.
    """
    df = pd.read_csv(path)
    required = {'start_utc','end_utc','rain_mm','source','model','member','latitude','longitude'}
    if not required.issubset(df.columns) or df.empty:
        raise ValueError(f'Required columns: {sorted(required)}')
    for c in ['start_utc','end_utc']:
        if not df[c].astype(str).str.contains(r'(?:Z|[+-]\d\d:\d\d)$', regex=True).all():
            raise ValueError('Timestamps must explicitly include timezone')
        df[c] = pd.to_datetime(df[c], utc=True, errors='raise')
    for c in ['rain_mm','latitude','longitude']:
        df[c] = pd.to_numeric(df[c], errors='raise')
        if not np.isfinite(df[c]).all(): raise ValueError(f'Nonfinite {c}')
    if (df.rain_mm < 0).any() or (df.end_utc <= df.start_utc).any():
        raise ValueError('Invalid rainfall or interval')
    if not df.latitude.between(-90,90).all() or not df.longitude.between(-180,180).all():
        raise ValueError('Invalid geographic coordinates')
    for c in ['source','model','member','latitude','longitude']:
        if df[c].isna().any() or df[c].astype(str).str.strip().eq('').any() or df[c].nunique()!=1:
            raise ValueError(f'Expected one nonempty {c}; select a single series')
    df = df.sort_values('start_utc').reset_index(drop=True)
    if len(df)>1 and not (df.start_utc.iloc[1:].to_numpy()==df.end_utc.iloc[:-1].to_numpy()).all():
        raise ValueError('Rainfall intervals must be contiguous and nonoverlapping')
    return df
