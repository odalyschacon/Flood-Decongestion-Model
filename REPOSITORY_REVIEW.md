# Repository review — November 13, 2026

**Final integration update:** The user supplied the workshop API credential. Authentication succeeded, model discovery succeeded, and three real before/after analyses completed with `qwen3-vl-8b-instruct`. The notebook and report now include these results. No local GPU or GB10 terminal access is required; Earth-2 is outside the active demo. Earlier unauthenticated checks below describe the initial audit, not the final status.

Reviewed the current `main` checkout at `fb2e297`, the existing Downloads copy, all six main notebooks, Python helpers, README, supplemental data links, HTML primer, dependency lists, license, JSON manifests, CSV annotations, and image assets. `results/repository_inventory.json` records hashes and sizes for all 67 tracked working-tree files, including checkpoints. Image assets were decoded/verified and reviewed as a contact sheet. This is a current-tree review, not an audit of every historical commit.

## File-by-file findings

| File/group | Purpose and finding |
|---|---|
| `README.md` | Anaconda/`gb10`/Jupyter setup and GB10 API configuration. Refers to an absent `utils.py`, but the current checkout actually includes it; that note is stale. |
| `UTSAworkbook.ipynb` | GB10/ARM64, NVIDIA Sync, Docker, HF and vLLM guidance. Several cells contain shell examples rather than executable notebook Python. No Earth-2 implementation. |
| `1_Introduction_to_Vision_Prompting.ipynb` | Introductory pixel and VLM exercises. A cell labeled “remove red” zeros channel 2 (blue); server settings are embedded in cells. |
| `2_Basic_Vision_Prompt_Structure.ipynb` | VLM description, classification and extraction examples. Contains a hardcoded API credential in upstream source; it was scrubbed from this deliverable's copy. An organizer should rotate any still-active published credential. |
| `01_Image_Question_Answering.ipynb` | Single-image zero-shot flood-evidence prompt using Bear Creek/Houston imagery. No segmentation or flood-depth inference. |
| `02_Text_to_Image_Retrieval.ipynb` | Caption + TF-IDF and optional Qwen embeddings. Comments say six images, but the selected list contains twenty. Consecutive assignments overwrite the text query. Similarity is not flood probability. |
| `03_Before_After_Change_and_Weather.ipynb` | Pair comparison and preceding daily rain. Requires the missing observations database. Seasonal/year differences remain confounders. |
| `texas_flood.py` | Useful image and weather helpers; preserves missing/failed-quality precipitation. Original layout expects a sibling data directory. Model requests depend on workshop authentication. |
| `image_embeddings.py` | Local Qwen3-VL-Embedding-2B, CPU fallback, normalized vectors. Downloads large weights; not needed for the initial planning prototype. |
| `vlm_config.py` | Workshop server settings; API key `NONE` does not authenticate against the currently responding server. Server and model names differ between some notebooks. |
| `utils.py` | Image preprocessing, RGB conversion, resizing and base64 encoding. Present in current checkout. |
| `unsloth_test1.py` | Unfinished training experiment: syntax error at line 12, undefined `load_from_disk` and `dataset`, author-specific Linux cache path. Not an executable training pipeline; intentionally excluded from baseline execution. |
| `requirements.txt` | Laptop workshop dependencies. Already available in the user's Python 3.11 `gb10` environment. |
| `requirements-embeddings.txt` | Optional heavyweight embedding stack, not Earth-2 or hydrology. |
| `UTSA_more_data.md` | Useful source list, including city drainage layers used by this prototype. A resource list is not evidence that any of those layers were downloaded or validated by upstream. |
| `gb10-hackathon-primer-v4.html` | Beginner guide to local models, terminal, SSH and Git. No flood modeling implementation. |
| `package_inventory.json` | Packaging snapshot; several recorded hashes/byte counts refer to older content and it references `README.txt`, absent from this Git checkout. Do not use it as current-tree validation. |
| `validation.json` | Earlier tests used model stubs; explicitly does not establish successful live VLM or embedding inference. New tests in this project validate only the new baseline's stated computations. |
| `datasets/` | 35 primary teaching images: Alamo, hand signs, receipts, graphs, park, nutrition, food truck and VizWiz. These are not the external 1,204-image flood collection. VizWiz annotation CSV is a teaching asset, not flood labels. |
| `.ipynb_checkpoints/` and nested checkpoints | Saved exercise/source/image snapshots. Inventoried, not a second authoritative pipeline; omitted from the deliverable review copy. |
| `LICENSE` | GPL-3.0; retained at project root and in workshop copy. Dataset and third-party asset licenses remain separate. |

## External dataset findings

Hugging Face metadata and documentation were downloaded at revision `ad98e681e7cf6af9ced145833b522c4f6c0acad1`. There are 1,204 images and 273 metadata fields. Four images lack exact coordinates; 1,200 have geographic footprints. The collection includes 575 before/after pairs and Hill Country/USCG images. All `flood_visible` values are blank. Roles and candidate-condition fields must not be treated as verified labels.

PNG files do not contain embedded georeferencing. The documentation identifies WGS84 bounds and EPSG:3857 image grids; use both correctly when georeferencing them. Do not infer a geotransform from image centers alone. The metadata retains useful terrain, rainfall, gauge and provenance information, but these fields are not automatically local pixel observations.

No image centers fall in a broad San Antonio box (longitude −98.85 to −98.2, latitude 29.2 to 29.8). The main event domains are Houston-area Harvey flooding and the Guadalupe/Hill Country. No supervised San Antonio flood model can be claimed from these files alone.

The HF repository does not list `observations.sqlite`, although its README describes it. It may be available in the separately supplied SharePoint package; that folder was not accessible through the available web tool. We did not claim to have reviewed unseen database tables or the entire SharePoint package.

## Verified setup and actual new outputs

- Existing environment: `C:\Users\odaly\anaconda3\envs\gb10\python.exe`, Python 3.11.18.
- Existing Downloads project located and preserved.
- Full upstream repository cloned; new work is under `outputs/SanAntonioFloodLab`.
- No local `torch` or `earth2studio` installed in `gb10`; `nvidia-smi` was not found on PATH. This does not prove that the laptop has no GPU.
- Unauthenticated GB10 `/v1/models` request returned HTTP 401. No live VLM inference was performed.
- Public metadata, documentation, six sample images, USGS elevation, and city drainage layers downloaded.
- City snapshot: 3,563 inlets, 5,677 underground line features, 201 channel features and 2 low-water crossings intersecting the pilot box.
- Baseline report and CSV/GeoJSON exports generated; test coverage includes routing conservation, serial storage, precipitation intervals and coordinate conversion.
- Independent ArcGIS geometry-service check agreed with the local UTM projection to better than one millimetre at the pilot center.

## Limits that matter for the project

The current rank is terrain-based screening, not benefit/cost optimization. Many high-accumulation points lie along the same drainage corridor; storing water at them is only a hypothetical scenario. Existing channels, parcel access, residences, aquifer restrictions and underground utilities may make a point infeasible. No construction recommendation should be inferred from its rank.

Earth-2 produces meteorological inputs. Actual tunnel sizing and flood-damage reduction need a calibrated runoff/drainage model and local exposure data. The optional Earth-2 runner is prepared against the versioned NVIDIA example, but its CUDA dependencies, model loading and live inference have not been tested on the GB10.
