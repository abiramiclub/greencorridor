import sys
from pathlib import Path

import click
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from analysis.geocoder import address_to_geom
from analysis.cvi_scorer import score_parcel
from analysis.species_lookup import get_species
from ai_layer.assessor import generate_assessment
from ai_layer.qa_engine import answer_question
from interface.map_renderer import make_map

DEMO_ADDRESSES = [
    "238 Main St, Cold Spring, NY",
    "1 Fahnestock State Park Rd, Carmel, NY",
    "8 Seminary Hill Rd, Cold Spring, NY",
]

BORDER = "═" * 44


def _bar(value: float, width: int = 10) -> str:
    filled = int(round(value / 10))
    return "█" * filled + "░" * (width - filled)


def _cvi_color(cvi: float) -> str:
    if cvi >= 65:
        return "green"
    if cvi >= 35:
        return "yellow"
    return "red"


def _run_assess(address: str, quiet: bool = False) -> dict:
    if not quiet:
        click.echo(f"\n{BORDER}")
        click.echo("CorridorGuardian Assessment")
        click.echo(address)
        click.echo(BORDER)

    geom = address_to_geom(address)
    lat, lon = geom["lat"], geom["lon"]

    cvi_result = score_parcel(lat, lon)
    species_list = get_species(lat, lon)

    cvi = cvi_result["cvi"]
    color = _cvi_color(cvi)

    if not quiet:
        click.echo("\n" + click.style("CONSERVATION VALUE INDEX", bold=True))
        bar_str = _bar(cvi)
        click.echo(f"Overall: {click.style(str(cvi), fg=color, bold=True)}/100  [{bar_str}]\n")

        click.echo("Factor Breakdown:")
        factor_labels = {
            "corridor_overlap": "Corridor overlap   ",
            "wetland_presence": "Wetland presence   ",
            "stream_adjacency": "Stream adjacency   ",
            "protected_proximity": "Protected proximity",
            "core_area": "Core area          ",
        }
        for key, label in factor_labels.items():
            val = cvi_result["factors"].get(key, 0)
            click.echo(f"  {label} [{_bar(val)}]  {int(val)}")

        click.echo(f"\nData sources loaded: {', '.join(cvi_result['data_sources']) or 'none'}")
        if cvi_result["warnings"]:
            for w in cvi_result["warnings"]:
                click.echo(click.style(f"Warnings: {w}", fg="yellow"))

        click.echo("\n" + click.style("SPECIES FINDINGS", bold=True))
        detected = [s for s in species_list if s.get("priority") and not s.get("not_detected")]
        other = [s for s in species_list if not s.get("priority") and not s.get("not_detected")]
        not_seen = [s for s in species_list if s.get("not_detected")]

        for s in detected:
            tag = click.style("[PRIORITY]", fg="red", bold=True)
            click.echo(f"  {tag} {s['common_name']} — {s['status']} — detected via {s['source']} ({s['observed_on']})")
        for s in other[:5]:
            click.echo(f"  [ other  ] {s['common_name']} — observed via {s['source']}")
        for s in not_seen:
            click.echo(f"  [not seen] {s['common_name']} — not detected within 2km")

        click.echo("\n" + click.style("BOARD ASSESSMENT", bold=True))
        click.echo("─" * 44)
        assessment = generate_assessment(geom["display_address"], cvi_result, species_list)
        click.echo(assessment)
        click.echo("─" * 44)

        map_path = make_map(lat, lon, address, cvi_result, species_list)
        click.echo(click.style(f"\nMap saved: {map_path}", fg="cyan"))
        click.echo(BORDER)

    return {
        "address": address,
        "display_address": geom["display_address"],
        "cvi": cvi,
        "cvi_result": cvi_result,
        "species_list": species_list,
        "lat": lat,
        "lon": lon,
    }


@click.group()
def cli():
    pass


@cli.command()
@click.argument("address")
def assess(address):
    """Run a full conservation assessment for ADDRESS."""
    try:
        _run_assess(address)
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"), err=True)
        sys.exit(1)


@cli.command()
@click.argument("question")
def ask(question):
    """Ask a question about Hudson Highlands Green Corridors."""
    click.echo(f"\n{'─' * 44}")
    click.echo(click.style("CorridorGuardian Q&A", bold=True))
    click.echo(f"{'─' * 44}")
    click.echo(f"Q: {question}\n")
    answer = answer_question(question)
    click.echo(answer)
    click.echo(f"{'─' * 44}\n")


@cli.command()
def demo():
    """Run assessments on 3 demo Philipstown parcels."""
    click.echo(click.style("\nCorridorGuardian Demo — Running 3 parcels...\n", bold=True))
    results = []
    for addr in DEMO_ADDRESSES:
        click.echo(click.style(f"Assessing: {addr}", fg="cyan"))
        try:
            result = _run_assess(addr)
            results.append(result)
            map_path = make_map(
                result["lat"], result["lon"], addr,
                result["cvi_result"], result["species_list"]
            )
            click.echo(click.style(f"  Map saved: {map_path}", fg="green"))
        except Exception as e:
            click.echo(click.style(f"  Error: {e}", fg="red"))
            results.append({"address": addr, "cvi": "ERROR"})

    click.echo(f"\n{'═' * 44}")
    click.echo(click.style("DEMO SUMMARY — CVI Scores", bold=True))
    click.echo(f"{'═' * 44}")
    for r in results:
        cvi = r.get("cvi", "ERROR")
        if isinstance(cvi, float):
            color = _cvi_color(cvi)
            score_str = click.style(f"{cvi:5.1f}/100  [{_bar(cvi)}]", fg=color)
        else:
            score_str = click.style("ERROR", fg="red")
        click.echo(f"  {r['address'][:38]:<38}  {score_str}")
    click.echo(f"{'═' * 44}\n")


if __name__ == "__main__":
    cli()
