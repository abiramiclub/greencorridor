"""
Smoke test: run all 3 demo addresses through geocoder and cvi_scorer.
No assertions — verifies no crashes and prints scores.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.geocoder import address_to_geom
from analysis.cvi_scorer import score_parcel

DEMO_ADDRESSES = [
    "238 Main St, Cold Spring, NY",
    "1 Fahnestock State Park Rd, Carmel, NY",
    "8 Seminary Hill Rd, Cold Spring, NY",
]

if __name__ == "__main__":
    print(f"{'Address':<45} {'CVI':>6}  {'Sources'}")
    print("-" * 80)
    for addr in DEMO_ADDRESSES:
        geom = address_to_geom(addr)
        result = score_parcel(geom["lat"], geom["lon"])
        sources = ", ".join(result["data_sources"])
        print(f"{addr:<45} {result['cvi']:>6.1f}  {sources}")
        if result["warnings"]:
            for w in result["warnings"]:
                print(f"  WARNING: {w}")
    print("\nAll parcels processed without errors.")
