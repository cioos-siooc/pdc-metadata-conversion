import json
import secrets
import string
import sys
from pathlib import Path
from glob import glob
import uuid

import click
import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm

from convert import fgdc
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
logger.add(sys.stderr, level="INFO", format=logger_format)


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

    output_dir = Path(output_dir)
    if ccins == ():
        logger.info("Retrieve ccins from the excel file")
        ccins = load_pdc_records().index

    for ccin in tqdm(ccins, desc="Downloading metadata"):
        output_file = output_dir / f"{ccin}_{xml_type}.xml"
        if output_file.exists() and not overwrite:
            continue
        response = requests.get(
            f"https://www.polardata.ca/pdcsearch/xml/fgdc/{ccin}_{xml_type}.xml"
        )
        if response.status_code != 200:
            logger.warning("Failed to download FGDC metadata for record: {}", ccin)
            continue

        output_file.write_text(response.text)


def from_fgdc(
    files: list[Path] | str,
    local_dir: Path,
    user: str,
) -> None:
    """Convert PDC FGDC metadata to CIOOS Metadata Form firebase JSON."""

    if not local_dir.exists():
        local_dir.mkdir()
    if isinstance(files, str):
        files = [Path(file) for file in glob(files, recursive=True)]
    elif local_dir.exists():
        files = local_dir.glob("*_fgdc.xml")

    # Convert the FGDC metadata to CIOOS Metadata Form
    results = {}
    for file in files:
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

    return results


def from_iso(
    files: list[Path] | str,
    local_dir: Path,
    user: str,
    shares: list[str],
) -> None:
    """Convert PDC ISO metadata to CIOOS Metadata Form firebase JSON."""
    if not local_dir.exists():
        local_dir.mkdir()

    if isinstance(files, str):
        files = [Path(file) for file in glob(files, recursive=True)]
    else:
        files = local_dir.glob("*_iso.xml")
    # Download the ISO metadata for each record

    # Convert the ISO metadata to CIOOS Metadata Form
    results = {}
    for file in files:
        with logger.contextualize(iso_file=file.name):
            # firebase uses a random key for the record
            identifier = uuid.uuid4()

            pdc_iso = PDC_ISO(file)
            results[str(identifier.hex)] = pdc_iso.to_cioos(
                user,
                file.name,
                file.name.replace("_iso.xml", ""),
                status="submitted",
                license="CC-BY-4.0",
                region="amundsen",
                project=[],
                ressourceType=["oceanographic"],
                shares=shares,
                distribution=[],
                eov=[],
                identifier=identifier,
            )
    return results


def append_to_existing_records(append_to, records, shares):
    """Append new records to existing records."""

    with open(append_to) as f:
        previous = json.load(f)
    if "records" not in previous:
        previous["records"] = {}
    if "shares" not in previous:
        previous["shares"] = {}
    if any(set(records.keys() & previous["records"].keys())):
        raise ValueError("Records with similar ID already exists in the append_to file")

    # Append records
    previous["records"].update(records)

    # Append shares
    for share, users in shares.items():
        if share not in previous["shares"]:
            previous["shares"][share] = {}
        for user, record in users.items():
            if user not in previous["shares"][share]:
                previous["shares"][share][user] = {}
            previous["shares"][share][user] = record

    return previous


@cli.command()
@click.option("--xml-format", type=click.Choice(["fgdc", "iso"]), default="iso")
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
@click.option(
    "--append-to",
    type=click.Path(),
    default="",
    help="Append to user records provided in json format",
)
@click.option(
    "--shares",
    type=str,
    default="",
    help="Comma separated list of users to share the records with",
)
def convert(xml_format, files, local_dir, output_file, user, shares, append_to):
    """Convert PDC metadata to CIOOS Metadata Form."""

    shares = shares.split(",")
    local_dir = Path(local_dir)

    # Convert records metadata
    if xml_format == "fgdc":
        records = from_fgdc(files, local_dir=local_dir, user=user)
    elif xml_format == "iso":
        records = from_iso(files, local_dir=local_dir, user=user, shares=shares)

    records_shares = {}
    for share in shares:
        records_shares[share] = {
            user: {recordID: {"shared": True} for recordID in records.keys()}
        }

    if append_to:
        logger.debug("Appending records to existing records")
        output = append_to_existing_records(append_to, records, records_shares)
    else:
        logger.debug("Creating new records")
        output = [{"records": records, "shares": records_shares or {}}]

    logger.debug("Writing output to file: {}", output_file)
    Path(output_file).write_text(json.dumps(output, indent=2))


if __name__ == "__main__":
    cli()
