# San Antonio Flood Lab — ready to demonstrate

This project runs on your laptop and uses the supplied OpenAI-compatible API for image analysis. No local GPU or GB10 terminal access is required. Your existing Anaconda environment happens to be named `gb10`.

## Open it

1. Open **FloodLab_Report.html** in a browser. The complete report and interactive controls work offline.
2. Double-click **Launch_Notebook.cmd**, open **SanAntonio_Flood_Planning.ipynb**, and run top to bottom.
3. Use **DEMO_SCRIPT.md** for a three-minute presentation. The ZIP contains the project and cached inputs/results for your team.

## What actually ran

- Reviewed the workshop repository and all 1,204 image metadata rows.
- Downloaded six demonstration images, real USGS terrain, and 9,443 San Antonio drainage features.
- Generated eight terrain investigation points and collector-storage scenarios.
- Completed three real before/after image analyses through `http://10.246.100.230/v1`, using `qwen3-vl-8b-instruct` and the supplied credential.
- Saved actual responses, timestamps, prompts, model IDs, request IDs and image hashes in `results/api_evidence/`.
- Built and executed the notebook, report, CSV/GeoJSON exports and calculation tests.

The endpoint serves Qwen through the OpenAI Python SDK. It is not the OpenAI-hosted service. Earth-2 is **not used** in this demonstration. The optional `earth2_forecast.py` is retained for future development only and has not been live-tested.

## Refresh AI results

You do not need the key to view or present the cached successful results. To request new results, double-click **Refresh_AI_Analysis.cmd**. It asks for the key in a hidden prompt, runs the three comparisons and rebuilds the report. The workshop network must be reachable.

Alternatively, from this project folder in Anaconda Prompt:

```bat
conda activate gb10
python api_evidence.py --refresh
python run_analysis.py
```

For unattended runs, set `FLOODLAB_API_KEY` in the process environment. Optional overrides: `FLOODLAB_BASE_URL` and `FLOODLAB_MODEL`. No credential is stored in the deliverables or Git history.

## Reproduce locally

```bat
conda activate gb10
python run_analysis.py
python -m unittest discover -s tests -v
python -m jupyterlab SanAntonio_Flood_Planning.ipynb
```

Dependencies are already present in your environment; `requirements.txt` supports other machines. No new GIS package is needed. Public downloads can be reproduced with `fetch_data.py`. Cached inputs support the offline demo.

## Explain the results accurately

**Terrain:** The west-side pilot is a rectangle at longitude −98.57 to −98.50 and latitude 29.39 to 29.46. A priority-flood drainage tree estimates contributing area inside this crop. Eight points are selected by accumulation, slope and spacing. These are investigation points, not optimized or approved construction sites. External inflows and pipe hydraulics are not represented.

**Storage:** Rainfall, runoff coefficient and capacity are assumptions. Collectors fill once; downstream collectors receive residual water, avoiding double counting. A 50 mm storm, coefficient 0.60 and eight 2,000 m³ collectors gives 16,000 m³ captured. This assumes unlimited inlet rates and is not a flood-depth, peak-flow or homes-protected result.

**AI:** The image pairs show Houston, not San Antonio. The model's unreviewed observations demonstrate evidence review, but do not calibrate local flood risk or determine the terrain ranking. Human flood-label fields in the full metadata are blank.

**Engineering still needed:** Tunnel routes and safe new development require buildings/parcels, a full watershed, pipe capacities/inverts, outfalls, soils, utility/land constraints and a calibrated hydraulic model. The full weather database is absent from the Hugging Face copy. The completed prototype does not claim to answer those engineering questions.

## Files

- `FloodLab_Report.html`: offline interactive report with actual AI outputs.
- `SanAntonio_Flood_Planning.ipynb`: executable walkthrough.
- `DEMO_SCRIPT.md`: presentation guide.
- `api_evidence.py`: authenticated API analysis and provenance cache.
- `floodlab.py`, `geo.py`: terrain, volume, coordinate and rainfall logic.
- `run_analysis.py`: regenerate exports and report.
- `fetch_data.py`: public inputs and provenance.
- `results/`: candidate CSV/GeoJSON, plots, scenarios and actual API records.
- `data/`: cached public inputs; all metadata but only six sample images.
- `REPOSITORY_REVIEW.md`: audit with final integration update.
- `workshop/`: upstream review copy with credentials scrubbed.

## Sources and reuse

[Workshop](https://github.com/jennifer-fowler/GB10competition), [UTSA data](https://huggingface.co/datasets/jennifer-fowler/UTSA-flood-images), [City GIS](https://www.sanantonio.gov/GIS/GISdata), [USGS terrain](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer), [OpenAI SDK documentation](https://developers.openai.com/api/reference/python).

Code retains the workshop GPL-3.0 license. The HF card states CC BY-NC 4.0; preserve agency attribution and source-specific terms. Current infrastructure snapshots are not historical reconstructions.
