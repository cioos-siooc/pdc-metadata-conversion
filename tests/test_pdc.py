from glob import glob

import pytest

import convert


@pytest.mark.parametrize("file", glob("tests/files/pdc*fgdc.xml"))
def test_fgdc(file):
    result = convert.fgdc(file, "userID", "filename", "test-recordID", "status")
    assert result
