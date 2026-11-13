# Buildings and draft floodplain screening

Open `Planning_Map.html` for the interactive layers (internet needed for map
tiles and JavaScript libraries). Import `SanAntonio_Planning.kmz` into Google
Earth for the same building outlines, draft polygons and investigation points.
The KMZ has been checked as valid XML, but has not been imported into Google
Earth in this session. Shapes are clamped to ground; no 3D heights are invented.

The pilot contains 4,568 OpenStreetMap building ways. Of these, 353 intersect
SARA's draft 1% annual-chance polygons and 16 intersect its draft future-condition
polygons. These sets may overlap. They count mapped footprints, not households,
people, flood damage or protected homes. OSM coverage is incomplete and the
query excludes multipolygon relations. Detailed areas and percentages are in
`results/building_draft_screening.csv`.

SARA's polygons are **draft**, subject to revision, and are not the effective
FEMA regulatory flood map. Footprint overlap is a screening observation rather
than a prediction of water depth. The eight investigation points remain based
on terrain convergence; this overlay does not establish construction suitability.

Also cached: 41,161 BCAD parcel features intersecting the pilot. Parcels are not
building footprints or household counts; owner names and addresses were excluded.
The TCEQ Edwards Aquifer layer returned no intersecting features. That does not
establish geotechnical suitability. USGS geological units and effective FEMA
polygons could not be retrieved, and are not included. Tunnel siting still needs
subsurface geology, utilities, hydraulic design and site investigation.

Sources and attribution:

- OpenStreetMap contributors, ODbL: https://www.openstreetmap.org/copyright
- SARA draft mapping: https://www.sariverauthority.org/projects/floodplain-mapping/
- City GIS / BCAD: https://www.sanantonio.gov/GIS/GISData
- TCEQ: https://www.tceq.texas.gov/gis/metadata/edwards_met.html

Reproduction:

```bash
python -m pip install -r requirements-planning.txt
python fetch_planning_layers.py
```

POST this query as the `data` form field to
`https://overpass-api.de/api/interpreter`, saving the JSON response locally:

```text
[out:json][timeout:45];way["building"](29.39,-98.57,29.46,-98.50);out geom;
```

Then run `python planning_map.py path/to/overpass_response.json`. Source metadata
and input SHA-256 are recorded beside the generated building GeoJSON.
