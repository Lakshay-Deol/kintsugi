"""CLI for ingest pipeline. Run locally only."""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")


@click.group()
def main() -> None:
    """Kintsugi ingestion CLI."""


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--manual-id", required=True, help="Unique manual ID")
@click.option("--brand", required=True, help="Appliance brand")
@click.option("--model", required=True, help="Appliance model number")
@click.option("--dry-run", is_flag=True, help="Parse only, no Atlas write")
def ingest(pdf_path: Path, manual_id: str, brand: str, model: str, dry_run: bool) -> None:
    """Ingest a PDF manual into Atlas."""
    from kintsugi.ingest.pipeline import ingest_manual, write_phase1_evidence

    stats = ingest_manual(pdf_path, manual_id, brand, model, dry_run=dry_run)
    click.echo(json.dumps(stats, indent=2))


@main.command()
@click.option("--manifest", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--pdf-dir", type=click.Path(exists=True, path_type=Path), required=True)
@click.option("--evidence-dir", type=click.Path(path_type=Path), default="evidence")
def ingest_all(manifest: Path, pdf_dir: Path, evidence_dir: Path) -> None:
    """Ingest all manuals from a JSON manifest file."""
    from kintsugi.ingest.pipeline import ingest_manual, write_phase1_evidence

    entries = json.loads(manifest.read_text())
    all_stats = []
    for entry in entries:
        pdf = pdf_dir / entry["filename"]
        if not pdf.exists():
            click.echo(f"SKIP {pdf} (not found)", err=True)
            continue
        stats = ingest_manual(pdf, entry["manual_id"], entry["brand"], entry["model"])
        all_stats.append(stats)

    write_phase1_evidence(all_stats, evidence_dir)
    click.echo(json.dumps(all_stats, indent=2))


if __name__ == "__main__":
    main()
