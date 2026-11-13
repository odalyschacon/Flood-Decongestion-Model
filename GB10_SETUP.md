# Earth-2 on the connected GB10

Installed and live-tested on November 13, 2026. SSH alias `Dell` was successfully tested.
The machine reports ARM64, NVIDIA GB10, driver 580.178.04 and CUDA driver
compatibility 13.0. Temporarily stopping Qwen with user authorization freed
about 115 GiB of unified memory. Qwen was restarted after inference.

**Earth-2 completed both a six-hour smoke test and a 24-hour forecast.**
The tested image uses `Dockerfile.earth2-local`, based on the already-cached
`vllm/vllm-openai:v0.31.0` image, with PyTorch 2.13.0+cu130, Earth2Studio 0.18.0
and PhysicsNeMo 2.2.2. This is a separate container; the Qwen container was not
modified. The alternative NVIDIA PyTorch Dockerfile was not fully built.

The final forecast starts November 13, 2026 at 12:00 UTC and ends November 14
at 12:00 UTC (6 a.m. to 6 a.m. Central Standard Time). It was generated at
20:18 UTC, after initialization, so the earliest interval is retrospective.
FourCastNet + PrecipitationAFNO produced 3.791905 mm at 29.5°N, 98.5°W.
The GPU inference loop took approximately 3.4 seconds; setup and downloads
took much longer. The validated CSV and provenance are in `results/`.

The preparation files are staged at `/tmp/sanantonio-earth2` on the GB10.
This is temporary storage and can be cleared by a reboot; the repository is
the durable copy. No credentials are included.

When a suitable GPU window is available, run in that directory:

```bash
docker build -f Dockerfile.earth2-local -t sanantonio-earth2:0.18.0 .
# Supply an actual available GFS initialization at 00, 06, 12 or 18 UTC.
bash run_earth2_gb10.sh YYYY-MM-DDTHH:00:00Z 1
```

Start with one six-hour forecast step. The launcher refuses to run below
60 GiB available system memory and never stops other containers. This gate
is conservative, not a guarantee of sufficient peak memory. The container
build preserves NVIDIA's PyTorch version: a dependency conflict should fail
the build for investigation, rather than replacing that hardware dependency.
Building downloads packages; the first inference downloads model weights
and GFS initial conditions and needs network access.

Successful inference writes `earth2-results/earth2_rainfall.csv` and its
provenance JSON. The launcher uses `preloaded-models/` when a source-provenance
file is present, otherwise Earth2Studio downloads its official defaults.
Model source URLs and SHA-256 values are saved in `results/earth2_model_sources.json`;
the FourCastNet hash matches NVIDIA's published Hugging Face LFS hash.
The exact installed package listing is in `results/environment-freeze.txt`.
The tested Docker image ID is
`sha256:99ed44a496fa14f3049d3911aaf25a4a55a90f226b6f69c4474b9e0b7f71b7d2`.

Local handoff: `python analyze_forecast.py results/earth2_rainfall.csv`.
With assumed runoff coefficient 0.6 and eight initially empty 2,000 m³
collectors, the screening stores 16,000 m³ out of 120,783 m³ generated runoff.
The mass-balance residual is below 0.000001 m³. These are model assumptions,
not validated drainage capacities or demonstrated flood mitigation.
The nearest 0.25-degree weather grid point is not a neighborhood flood model:
terrain screening still requires local drainage and hydraulic validation.

Reference: https://nvidia.github.io/earth2studio/0.18.0/userguide/about/install/
