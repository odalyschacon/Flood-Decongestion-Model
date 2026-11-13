# Three-minute demonstration

**Problem — 20 seconds**
“We want to help San Antonio investigate where stormwater collection could be useful before investing in detailed engineering studies.”

**Real local data — 40 seconds**
Open `FloodLab_Report.html`. Show the elevation/drainage figure: USGS terrain plus 9,443 city infrastructure features. Explain that eight points are ranked by terrain convergence, with a slope filter and spacing requirement. They are investigation points, not approved construction sites.

**Scenario comparison — 45 seconds**
Move the rainfall and storage sliders. With 50 mm rainfall, runoff coefficient 0.60, and 2,000 m³ per collector, the model stores 16,000 m³. Explain that this is event-volume accounting, with upstream storage removed before water reaches downstream collectors. It is not a flood-depth or peak-flow prediction.

**Actual AI integration — 45 seconds**
Show the live AI evidence section. Qwen analyzed three provided before/after image pairs using the supplied OpenAI-compatible API. The exact outputs, model IDs, timestamps and image hashes are cached. Explain that the imagery comes from Houston; it demonstrates the evidence-review component but does not validate San Antonio flooding or generate the candidate ranking.

**What comes next — 30 seconds**
“To move from screening to construction recommendations, we need residential buildings and parcels, drainage capacities, full watersheds, and a calibrated hydraulic model. Tunnel design and safe new development cannot be determined by a vision model or terrain convergence alone.”

**If asked about Earth-2**
“We ran NVIDIA Earth2Studio on the GB10 using FourCastNet and PrecipitationAFNO. Its 24-hour forecast produced 3.792 mm at the San Antonio grid point. We passed that rainfall into our event-volume screening. This is coarse weather guidance, not a neighborhood flood-depth prediction; the report also retains independent rainfall scenarios.”

**If the network drops**
The HTML report, cached AI results, notebook and local scenario calculations work offline. Only refreshing AI results requires the workshop network and credential.
