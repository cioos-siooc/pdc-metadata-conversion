import json
import secrets
import string
import sys
from pathlib import Path
from glob import glob

import click
import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm

from convert.fgdc import main as fgdc
from convert.iso import PDC_ISO

PDC_FGDC_URL = "https://www.polardata.ca/pdcsearch/xml/fgdc/13172_fgdc.xml"
logger_format = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "{extra[iso_file]} - <level>{message}</level>"
)

logger.remove(0)
logger = logger.bind(iso_file="")
logger.add(sys.stderr, level="DEBUG", format=logger_format)


def generate_random_string(length=20):
    """Generate a random string of specified length."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def load_pdc_records() -> pd.DataFrame:
    """Load the PDC records from the Excel file."""
    pdc_records = pd.concat(
        [
            pd.read_excel(
                "AmundsenSept2024records.xlsx", index_col=0, sheet_name="Confirmed"
            ).assign(status_amundsen="confirmed"),
            pd.read_excel(
                "AmundsenSept2024records.xlsx", index_col=0, sheet_name="Candidates"
            ).assign(status_amundsen="candidate"),
        ]
    )
    return pdc_records


@click.group()
def cli():
    pass

@cli.command()
@click.argument("ccins", nargs=-1)
@click.option("--output-dir", type=click.Path(), required=True)
@click.option("--xml-type", type=click.Choice(["fgdc", "iso"]), required=True)  
@click.option("--overwrite", is_flag=True, default=False)
def download(ccins, output_dir, xml_type, overwrite=False):
    """Download the metadata for the specified CCINs."""
    if ccins == ():
        logger.info("Retrieve ccins from the excel file")
        ccins = load_pdc_records().index

    for ccin in ccins:
        output_file = output_dir / f"{ccin}_{xml_type}.xml"
        if output_file.exists() and not overwrite:
            continue
        response = requests.get(f"https://www.polardata.ca/pdcsearch/xml/fgdc/{ccin}_{xml_type}.xml")
        if response.status_code != 200:
            logger.warning("Failed to download FGDC metadata for record: {}", ccin)
            continue

        output_file.write_text(response.text)


def from_fgdc(
    files: list[Path] | str,
    local_dir: Path,
    output_file: Path,
    overwrite: bool = False,
    user: str = "unknown",
    ccins: str = None,
) -> None:
    """Convert PDC FGDC metadata to CIOOS Metadata Form firebase JSON."""

    if not local_dir.exists():
        local_dir.mkdir()
    if isinstance(files, str):
        files = glob(files, recursive=True)
    
    local_files = local_dir.glob("*_fgdc.xml")

    # Convert the FGDC metadata to CIOOS Metadata Form
    results = {}
    for file in files:
        if file in local_files and not overwrite:
            continue

        random_key = generate_random_string()
        results[random_key] = fgdc(
            file,
            user,
            file.name,
            file.name.replace("_fgdc.xml", ""),
            "status",
            "CC-BY-4.0",
            "amundsen",
            "dataset",
            [],
        )

    with output_file.open("w") as file:
        json.dump(results, file, indent=2)


def from_iso(
    files: list[Path] | str,
    local_dir: Path,
    output_file: Path,
    overwrite: bool = False,
    user: str = "unknown",
) -> None:
    """Convert PDC ISO metadata to CIOOS Metadata Form firebase JSON."""
    if not local_dir.exists():
        local_dir.mkdir()

    pdc_records = load_pdc_records()
    if isinstance(files, str):
        files = glob(files, recursive=True)
    local_files = local_dir.glob("*_iso.xml")
    # Download the ISO metadata for each record


    # Convert the ISO metadata to CIOOS Metadata Form
    results = {}
    for file in files:
        if file in local_files and not overwrite:
            continue

        with logger.contextualize(iso_file=file.name):
            # firebase uses a random key for the record
            random_key = generate_random_string()

            pdc_iso = PDC_ISO(file)
            results[random_key] = pdc_iso.to_cioos(
                file,
                user,
                file.name,
                file.name.replace("_iso.xml", ""),
                status="status",
                license="CC-BY-4.0",
                region="amundsen",
                project=[],
                ressourceType=["oceanographic"],
                sharedWith=[],
                distribution=[],
                eov=[],
            )
    output_file.write_text(json.dumps(results, indent=2))


@cli.command()
@click.argument("--iso_format", type=click.Choice(["fgdc", "iso"]), default="iso")
@click.option("--files", type=str, required=True)
@click.option(
    "--local-dir", type=click.Path(exists=True), required=True, default=Path("data")
)
@click.option(
    "--output-file",
    type=click.Path(),
    required=True,
    help="Output file path",
    default=Path("output.json"),
)
@click.option(
    "--user", default="unknown", help="User ID TO assign to the records within CIOOS"
)
@click.option("--overwrite", is_flag=True, default=False)
def convert(iso_format, **kwargs):
    """Convert PDC metadata to CIOOS Metadata Form."""
    if iso_format == "fgdc":
        from_fgdc(**kwargs)
    elif iso_format == "iso":
        from_iso(**kwargs)



if __name__ == "__main__":
    cli()
