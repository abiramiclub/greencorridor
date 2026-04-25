import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

SYSTEM_PROMPT = (
    "You are a conservation planning assistant for Philipstown, NY, supporting the Hudson Highlands "
    "Green Corridors Initiative. You write clear, specific assessments for town board members and "
    "planning staff who are not ecologists. You are direct and data-grounded. You never make a "
    "definitive land use recommendation — you present findings and suggest questions for further "
    "inquiry. Always cite data sources by name. Always end with: \"This assessment is AI-assisted "
    "and based on publicly available data. Field verification by a qualified ecologist is recommended "
    "before any land use or acquisition decision.\""
)


def generate_assessment(address: str, cvi_result: dict, species_list: list) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "[ANTHROPIC_API_KEY not set — AI assessment unavailable]"

    cvi = cvi_result["cvi"]
    factors = cvi_result["factors"]
    sources_loaded = ", ".join(cvi_result["data_sources"]) or "none"
    warnings = cvi_result.get("warnings", [])

    detected = [s for s in species_list if not s.get("not_detected") and s["priority"]]
    other_observed = [s for s in species_list if not s.get("not_detected") and not s["priority"]]
    not_detected = [s for s in species_list if s.get("not_detected")]

    factor_text = "\n".join(
        f"  - {k.replace('_', ' ').title()}: {v}/100 (weight {w:.0%})"
        for k, (v, w) in zip(
            factors.keys(),
            zip(factors.values(), [0.35, 0.15, 0.15, 0.15, 0.20]),
        )
    )

    detected_text = (
        "\n".join(f"  * {s['common_name']} ({s['scientific_name']}) — {s['status']} — via {s['source']} on {s['observed_on']}"
                  for s in detected)
        or "  None detected"
    )

    other_text = (
        "\n".join(f"  * {s['common_name']} — via {s['source']}" for s in other_observed[:5])
        or "  None"
    )

    not_detected_text = (
        "\n".join(f"  * {s['common_name']} ({s['status']})" for s in not_detected)
        or "  All target species detected"
    )

    user_message = f"""Please write an assessment for the following parcel:

ADDRESS: {address}

CONSERVATION VALUE INDEX (CVI): {cvi}/100
Factor breakdown:
{factor_text}

Data sources loaded: {sources_loaded}
Warnings / missing data: {'; '.join(warnings) if warnings else 'None'}

PRIORITY SPECIES DETECTED:
{detected_text}

OTHER SPECIES OBSERVED:
{other_text}

TARGET SPECIES NOT DETECTED NEARBY:
{not_detected_text}

Write exactly 3 paragraphs: (1) location and corridor context based on CVI data, (2) ecological values found from the species and habitat data, (3) exactly 3 specific questions the planning board should ask before making any land use decision. Keep the total under 400 words."""

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text
