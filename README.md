# CorridorGuardian
AI-powered conservation assessment for the Hudson Highlands Green Corridors Initiative.
Built for the Town of Philipstown, NY and Hudson Highlands Land Trust.

## What it does
Score any Philipstown parcel on a Conservation Value Index (CVI), identify at-risk species nearby, generate plain-language planning board memos, and render interactive maps overlaying Green Corridor priority zones.

## Setup
```
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY and EBIRD_API_KEY to .env
```

## Usage
```
python -m interface.cli assess "238 Main St, Cold Spring, NY"
python -m interface.cli ask "Does Garrison have bald eagle habitat?"
python -m interface.cli demo
```

## Data sources
Hudson Highlands Green Corridors Plan (HHLT, 2022) · NWI Wetlands (USFWS) · NHDPlus HR Streams (USGS) · NYPAD Protected Lands (NYNHP) · iNaturalist API · eBird API (Cornell Lab)

## Governance
All AI outputs include source citations and a mandatory human-review disclosure. This tool supports planning decisions — it does not replace them.
