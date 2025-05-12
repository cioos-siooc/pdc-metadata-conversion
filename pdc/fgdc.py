import re

from loguru import logger
from lxml import etree as ET

# Define the namespaces
namespaces = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


def _create_contact(contact, in_citation: bool, role: list[str]) -> dict:
    """Add a contact to the metadata record."""
    logger.info("Creating contact: {}", contact)
    name = contact.find(".//cntper").text
    name = name.split(":")[-1].strip()
    names = re.split("\s+", name)
    if len(names) > 2:
        logger.warning("Name has more than two parts: {}", name)
    else:
        logger.debug("Name has two parts: {}", name)

    return {
        "givenName": " ".join(names[:-1]),
        "lastName": names[-1],
        "inCitation": in_citation,
        "indEmail": contact.find(".//cntemail").text,
        "indName": name,
        "indOrcid": "",
        "indPosition": _get(contact, ".//cntpos"),
        "orgAddress": contact.find(".//cntaddr/address").text,
        "orgCity": contact.find(".//cntaddr/city").text,
        "orgCountry": contact.find(".//cntaddr/country").text,
        "orgEmail": "",
        "orgName": contact.find(".//cntorg").text,
        "orgRor": "",
        "orgURL": "",
        "role": role or [],
    }


def _create_distribution(distribution) -> dict:
    """Add a distribution to the metadata record."""

    return {
        "description": {
            "en": distribution.find(".//description").text,
        },
        "name": {
            "en": distribution.find(".//name").text,
        },
        "url": {
            "en": distribution.find(".//url").text,
        },
    }


def _get(item, tag, default=None, level="INFO") -> str:
    """Get the text of an element with the given tag."""
    result = item.find(tag)
    if result is None:
        logger.log(level, "Item {} not found in ", tag, item)
        return default
    return result.text


def _get_author(author) -> dict:
    author_text = author.text
    if "," in author_text:
        author_text = " ".join(author_text.split(",")[::-1])

    names = re.split("\s+", author_text)
    names = [name for name in names if name]
    if len(names) > 2:
        logger.warning("Name has more than two parts: {}", names)
    else:
        logger.debug("Name has two parts: {}", names)
    return {
        "givenName": names[:-1],
        "lastName": names[-1],
        "role": ["author"],
        "inCitation": True,
    }


def main(
    file,
    userID: str,
    filename: str,
    recordID: str,
    status: str,
    license: str,
    region: str,
    ressourceType: list[str],
    sharedWith: list[str],
    projects: list[str] = [],
) -> dict:
    """Parse a Polar Data Catalogue FGDC metadata record."""
    logger.warning(
        "The FGDC metadata is incomplete and missine some parameters. We recommand using the ISO xml format instead."
    )
    tree = ET.parse(file)

    return {
        "userID": userID,
        "organization": tree.find(".//cntorg").text,
        "title": {"en": tree.find(".//title").text},
        "abstract": {"en": tree.find(".//abstract").text},
        "category": "dataset",  # TODO confirm this is related to the latest version of the schema
        "contact": [
            _create_contact(contact, False, ["pointOfContact"])
            for contact in tree.findall(".//ptcontac")
        ]
        + [
            _create_contact(contact, False, ["owner"])
            for contact in tree.findall(".//distrib")
        ]
        + [
            _create_contact(contact, False, ["custodian"])
            for contact in tree.findall(".//metc")
        ]
        + [_get_author(contact) for contact in tree.findall(".//origin")],
        # TODO Convert all dates to ISO 8601 format
        "created": _get(tree, ".//pubdate"),
        "datasetIdendifier": _get(tree, ".//idinfo"),
        "dateStart": _get(tree, ".//begdate"),
        "dateEnd": _get(tree, ".//enddate"),
        "datePublished": _get(tree, ".//pubdate"),
        "dateRevised": _get(tree, ".//revdate"),
        "distribution": [],
        "doiCreationStatus": "",
        "edition": "",
        "eov": [],
        "filename": filename,
        "history": [],  # Related to Lineage
        "identifier": tree.find(".//idinfo").text,
        "keywords": {
            "en": [kw.text for kw in tree.findall(".//themekey")]
            + tree.find(".//placekt").text.split("; "),
        },
        "language": "en",
        "lastEditedBy": {"displayName": "", "email": ""},
        "license": license,
        "limitations": {
            "en": tree.find(".//purpose").text + "\n\n" + tree.find(".//supplinf").text,
        },
        "map": {
            "description": {"en": ""},
            "north": tree.find(".//northbc").text,
            "south": tree.find(".//southbc").text,
            "east": tree.find(".//eastbc").text,
            "west": tree.find(".//westbc").text,
            "polygon": "",
        },
        "metadataScope": "Dataset",
        "noPlatform": False,
        "platforms": [
            {
                "description": {"en": ""},
                "id": "",
                "type": "ship",
            }
        ],
        "noTaxa": True,
        "progress": "onGoing",
        "projects": projects,
        "recordID": recordID,
        "region": region,
        "resourceType": ressourceType,  # Projects in form
        "sharedWith": {person: True for person in sharedWith},
        "status": status,
        "timeFirstPublished": tree.find(".//metd").text,
        "vertical": {},
        "noVerticalExtent": False,
        "verticalExtentDirection": "depthPositive",
        "verticalExtentMax": _get(tree, ".//depthmax"),
        "verticalExtentMin": _get(tree, ".//depthmix"),
    }
