# Synthetic farmer personas

How to build a **table of synthetic farmer personas** (identity, place, land, crops, scheme-style ids, language/mood) using the same building blocks as `synth-data-bharat-oan-api` and `[mock_data.py](../../current_work/synth-data-bharat-oan-api/synthetic/mock_data.py)`. This is **only** the persona layer—not synthetic conversations, not training pair generation.

## 1. Start from `mock_data.py`

Use it for realistic pools: `random_name()` (Faker `en_IN`), `get_random_location()` or `LOCATIONS`, `FARMER_CROPS`, and the same optional pools if you need consistent labels later (`CROP_PRICE_RANGES`, `MANDI_NAMES`, `SHC_`*, weather helpers). That keeps names, places, and crop names coherent.

## 2. Match `FarmerProfile` (or a subset)

Field layout is in `[synthetic/user/profile.py](../../current_work/synth-data-bharat-oan-api/synthetic/user/profile.py)`. To produce personas, call `generate_random_profile()` from that project, or copy its sampling (1–3 crops, location, land acres, phone/aadhaar/PM-KISAN patterns, language, mood, verbosity, etc.) in your own script.

## 3. Export personas (e.g. JSONL)

One JSON object per line: the fields you need (e.g. `name`, `state`, `district`, `village`, `crops`, `land_acres`, `phone`, `pm_kisan_reg_no`, `language`, `mood`, `verbosity`, `shc_cycle`, `grievance_reg_no`). That file **is** the output; anything that consumes personas (simulators, eval harnesses, data pipelines) is separate.

## 5. What this doc does *not* cover

Generating **dialogues**, **Q&A**, or **training (input, target) pairs** from those personas. Those steps belong in whatever system uses the persona file next.