from glob import glob

import pytest

import pdc.fgdc as fgdc


@pytest.mark.parametrize("file", glob("tests/files/pdc*fgdc.xml"))
def test_fgdc(file):
    result = fgdc.main(file, "userID", "filename", "test-recordID", "status" , "CC-BY-4.0", "region", ["dataset"], ["sharedWith"])
    assert result
