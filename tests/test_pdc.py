from glob import glob

import pytest

import pdc.fgdc as fgdc
from pdc.iso import PDC_ISO


@pytest.mark.parametrize("file", glob("tests/files/pdc*fgdc.xml"))
def test_fgdc(file):
    result = fgdc.main(
        file,
        "userID",
        "filename",
        "test-recordID",
        "status",
        "CC-BY-4.0",
        "region",
        ["dataset"],
        ["sharedWith"],
    )
    assert result


@pytest.mark.parametrize("file", glob("tests/files/pdc*iso.xml"))
def test_iso_xml(file):
    pdc_iso = PDC_ISO(file)
    result = pdc_iso.to_cioos(
        "userID",
        "filename",
        "test-recordID",
        "status",
        "CC-BY-4.0",
        "region",
        [],
        ["dataset"],
        ["sharedWith"],
        [],
        ["eov"],
        "identifier",
    )
    assert result
