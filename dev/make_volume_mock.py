"""Write a made-up, realistic-volume mock-IO file for get_incident_events.

200 incidents over a year (Nov 2025 - Oct 2026), ~1,000 events, 18 event types,
around Tsavo. No real site has this many incidents yet, so this is how we check
that the dashboard copes. Same columns as the real wd example
(mock-io/get-incident-events.example-return.parquet); icons are borrowed from it.

Usage (in the compiled workflow's env, which has geopandas):
    ecoscope-workflows-incident-reports-workflow/.pixi/envs/default/bin/python \
        dev/make_volume_mock.py [out.parquet]
"""

import json
import sys
import uuid
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Point

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "mock-io" / "get-incident-events.example-return.parquet"
OUT = (
    Path(sys.argv[1])
    if len(sys.argv) > 1
    else ROOT / "mock-io" / "volume-200.example-return.parquet"
)

rng = np.random.default_rng(7)


def uid() -> str:
    return str(uuid.UUID(int=int(rng.integers(0, 2**63)) << 64 | int(rng.integers(0, 2**63))))


# (display, category, weight): a few common types, a long tail
TYPES = [
    ("Wildlife Sighting", "Monitoring", 18),
    ("Animal Carcass", "Security", 12),
    ("Poacher Spoor (Human & Vehicle)", "Security", 10),
    ("Snare", "Security", 9),
    ("Arrest", "Security", 6),
    ("Human-Wildlife Conflict", "Community", 8),
    ("Crop Raid", "Community", 6),
    ("Livestock Predation", "Community", 6),
    ("Fence Damage", "Logistics", 5),
    ("Fire", "Monitoring", 4),
    ("Illegal Logging", "Security", 4),
    ("Charcoal Burning", "Security", 4),
    ("eBird Kilifi", "Monitoring", 3),
    ("Tree Species", "Monitoring", 3),
    ("Invasive Plant Cover", "Monitoring", 2),
    ("Water Point Status", "Logistics", 2),
    ("Vehicle Breakdown", "Logistics", 2),
    ("Rhino Sighting", "Monitoring", 2),
]
TITLES = [
    "Poaching", "Snaring line", "Elephant carcass", "Crop raid at {v}",
    "Livestock lost to lions near {v}", "Charcoal kilns", "Fence breach", "Bushfire",
    "Illegal logging on the {v} ridge", "Suspected ivory trafficking network around {v}",
    "Water point dry", "HWC follow-up", "Rhino monitoring", "Bird survey",
]
VILLAGES = ["Mbulia", "Bura", "Maktau", "Rukanga", "Kasigau", "Sagalla", "Mwatate"]
STATES = (["new", "active", "review", "resolved"], [0.15, 0.3, 0.1, 0.45])

real = gpd.read_parquet(REAL)
icons = list(real["icon"].dropna().unique())

t_start = pd.Timestamp("2025-11-01", tz="UTC")
t_end = pd.Timestamp("2026-10-31", tz="UTC")
span = (t_end - t_start).total_seconds()
weights = np.array([w for *_, w in TYPES], dtype=float)
weights /= weights.sum()

rows = []
serial = 10_000
for n in range(200):
    inc_time = t_start + pd.Timedelta(seconds=float(rng.uniform(0, span)))
    inc_serial = 20_000 + n
    title = rng.choice(TITLES).format(v=rng.choice(VILLAGES))
    inc_state = rng.choice(STATES[0], p=STATES[1])
    centre = (38.4 + rng.normal(0, 0.35), -3.0 + rng.normal(0, 0.3))
    n_events = int(np.clip(rng.geometric(0.2), 1, 25))  # mean ~5, a few long ones
    main = rng.choice(len(TYPES), p=weights)
    inc_id = uid()
    t = inc_time - pd.Timedelta(hours=float(rng.uniform(0, 6)))
    for k in range(n_events):
        typ = main if rng.random() < 0.5 else rng.choice(len(TYPES), p=weights)
        disp, cat, _ = TYPES[typ]
        t = t + pd.Timedelta(minutes=float(rng.exponential(600)))
        located = rng.random() > 0.1
        serial += 1
        details = {"Species": str(rng.choice(["Elephant", "Lion", "Buffalo", "Giraffe"]))}
        if rng.random() < 0.3:
            details["Notes from scene"] = "Tracks lead north towards the river; team followed for 2 km."
        rows.append(
            {
                "incident_id": inc_id,
                "incident": f"#{inc_serial} {title}",
                "incident_serial": inc_serial,
                "incident_title": title,
                "incident_state": inc_state,
                "incident_time": inc_time,
                "incident_created_at": inc_time,
                "incident_updated_at": inc_time + pd.Timedelta(days=3.0),
                "incident_priority": int(rng.choice([0, 100, 200, 300])),
                "id": uid(),
                "serial_number": serial,
                "time": t,
                "event_type": disp.lower().replace(" ", "_"),
                "event_category": cat.lower(),
                "title": None if rng.random() < 0.6 else f"{disp} report",
                "state": rng.choice(STATES[0], p=STATES[1]),
                "priority": int(rng.choice([0, 100, 200, 300])),
                "priority_label": "Gray",
                "reported_by": "",
                "notes": "" if rng.random() < 0.8 else "Ranger team informed.",
                "created_at": t,
                "updated_at": t,
                "event_details": json.dumps(details),
                "image_url": "",
                "geometry": Point(centre[0] + rng.normal(0, 0.02), centre[1] + rng.normal(0, 0.02))
                if located
                else None,
                "icon": icons[typ % len(icons)],
                "event_type_display": disp,
                "event_category_display": cat,
                "event_details_raw": json.dumps({"updates": []}),
            }
        )

df = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
df = df.astype({c: real[c].dtype for c in real.columns if c in df.columns and c != "geometry"})
df = df[list(real.columns)]
df.to_parquet(OUT)
print(
    f"{OUT}: {df['incident_id'].nunique()} incidents, {len(df)} events, "
    f"{df['event_type_display'].nunique()} event types"
)
