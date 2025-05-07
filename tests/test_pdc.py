from glob import glob
import os

import pytest

import pdc.fgdc as fgdc
from pdc.iso import PDC_ISO
from pdc.translate import get_french_translated_cioos_record
from dotenv import load_dotenv
load_dotenv()


FGDC_TEST_FILES = glob("tests/files/pdc*fgdc.xml")
ISO_TEST_FILES = glob("tests/files/pdc*iso.xml")

def test_fgdc_files_exist():
    assert len(FGDC_TEST_FILES) > 0, "No FGDC files found in tests/files/"
    assert isinstance(FGDC_TEST_FILES, list), "FGDC_TEST_FILES should be a list"

def test_iso_files_exist():
    assert len(ISO_TEST_FILES) > 0, "No ISO files found in tests/files/"
    assert isinstance(ISO_TEST_FILES, list), "ISO_TEST_FILES should be a list"


@pytest.mark.parametrize("file", glob("tests/files/pdc*fgdc.xml"))
def test_parse_fgdc(file):
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


@pytest.mark.parametrize("file", ISO_TEST_FILES)
def test_parse_iso_xml(file):
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


@pytest.mark.skipif(
    not os.getenv("AWS_ACCESSKEYID")
    or not os.getenv("AWS_SECRETACCESSKEY"),
    reason="AWS credentials are not set in environment variables."
)
@pytest.mark.parametrize("file", [ISO_TEST_FILES[0]])
def test_iso_xml_translation(file):
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
    result = get_french_translated_cioos_record(
        result,
    )
    assert result
    assert result["title"]["fr"]
    assert result["abstract"]["fr"]
    assert result["limitations"]["fr"]