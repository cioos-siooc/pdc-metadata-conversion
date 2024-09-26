import json
from pathlib import Path

import pandas as pd
import requests
from loguru import logger
from tqdm import tqdm

from convert import fgdc

PDC_FGDC_URL = "https://www.polardata.ca/pdcsearch/xml/fgdc/13172_fgdc.xml"


def get_fgdc_url(ccin: str) -> dict:
    """Get the FGDC metadata for a dataset."""
    return f"https://www.polardata.ca/pdcsearch/xml/fgdc/{ccin}_fgdc.xml"


def main(
    local_dir: Path, output_file: Path, overwrite: bool = False, user: str = "unknown"
) -> None:
    """Convert PDC FGDC metadata to CIOOS Metadata Form firebase JSON."""

    if not local_dir.exists():
        local_dir.mkdir()

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
    local_files = local_dir.glob("*_fgdc.xml")
    # Download the FGDC metadata for each record
    for ccin in tqdm(pdc_records.index, "Downloading FGDC metadata"):
        local_file = local_dir / f"{ccin}_fgdc.xml"
        if output_file.exists() and not overwrite:
            continue
        fgdc_url = get_fgdc_url(ccin)
        response = requests.get(fgdc_url)
        if response.status_code != 200:
            logger.warning("Failed to download FGDC metadata for record: {}", ccin)
            continue

        local_file.write_text(response.text)

    # Convert the FGDC metadata to CIOOS Metadata Form
    results = {}
    for local_file in local_files:
        # TODO generate key and filename
        results[local_file.name] = fgdc(
            local_file,
            user,
            local_file.name,
            local_file.name.replace("_fgdc.xml", ""),
            "status",
            "CC-BY-4.0",
            "amundsen",
            "dataset",
            []
        )

    with output_file.open("w") as file:
        json.dump(results, file, indent=2)


if __name__ == "__main__":
    main(Path("data"), Path("output.json"))
