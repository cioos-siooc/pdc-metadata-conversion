from glob import glob

import pytest

import convert.fgdc as fgdc


@pytest.mark.parametrize("file", glob("tests/files/pdc*fgdc.xml"))
def test_fgdc(file):
    result = fgdc.main(file, "userID", "filename", "test-recordID", "status")
    assert result
