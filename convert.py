from lxml import etree as ET

# Define the namespaces
namespaces = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
}


def _create_contact(contact, in_citation: bool = True) -> dict:
    """Add a contact to the metadata record."""

    return {
        "individual": contact.find(".//name").text,
        "organization": contact.find(".//email").text,
        "roles": [role.text for role in contact.findall(".//role")],
        "inCitation": in_citation,
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


def iso(file) -> dict:
    """Convert a Polar Data Catalogue ISO xml metadata record."""

    # load xml
    tree = ET.parse(file)

    return {
        "contact": [_create_contact(contact) for contact in tree.findall(".//contact")],
        "distribution": [
            _create_distribution(distribution)
            for distribution in tree.findall(".//distribution")
        ],
        "identification": {
            "title": {
                "en": tree.find(
                    ".//gmd:identificationInfo/gmd:DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title",
                    namespaces,
                ).text,
                "fr": "",
            },
            "abstract": {
                "en": "",
            },
            "associated_ressources": [],
            "dates": {
                "creation": tree.find(".//date").text,
                "revision": tree.find(".//date").text,
            },
            "edition": tree.find(".//version").text,
            "keywords": {
                "default": {
                    "en": [kw.text for kw in tree.findall(".//keyword")],
                }
            },
            "progress_code": tree.find(".//status").text,
            "project": [],
            "temporal_begin": tree.find(".//temporal").text,
            "temporal_end": tree.find(".//temporal").text,
        },
        "metadata": {
            "dates": {
                "publication": tree.find(".//date").text,
                "revision": tree.find(
                    ".//gmd:metadataStandardVersion/gco:CharacterString", namespaces
                ).text,
            },
            "history": [],
            "identifier": tree.find(".//identifier").text,
            "language": tree.find(".//language").text,
            "maintenance_note": "Generated from Polar Data Catalogue metadata record converted by the CIOOS metadata converter.",
            "naming_authority": "Polar Data Catalogue",
            "use_constraints": {
                "licence": {
                    "code": tree.find(".//rights").text,
                    "title": {
                        "en": tree.find(".//rights").text,
                    },
                    "url": tree.find(".//rights").text,
                }
            },
        },
        "platform": [],
        "spatial": {
            "polygon": [],
            "vertical": {},
            "vertical_positive": tree.find(".//vertical").text,
        },
    }


def fgdc(file):
    """Parse a Polar Data Catalogue FGDC metadata record."""

    tree = ET.parse(file)

    return {
        "identification": {
            "title": {"en": tree.find(".//title").text},
            "abstract": {"en": tree.find(".//abstract").text},
            "dates": {
                "creation": tree.find(".//date").text,
                "revision": tree.find(".//pubdate").text,
            },
            "edition": "",
            "keywords": {
                "default": {
                    "en": [kw.text for kw in tree.findall(".//themekey")]
                    + tree.find(".//placekt").text.split("; "),
                }
            },
            "progress_code": tree.find(".//progress").text,
            "project": [],
            "temporal_begin": tree.find(".//begdate").text,
            "temporal_end": tree.find(".//enddate").text,
        },
        "metadata": {
            "dates": {
                "publication": tree.find(".//metd").text,
                "revision": tree.find(".//metrd").text,
            },
            "history": [],
            "identifier": tree.find(".//idinfo").text,
            "language": "english",
            "maintenance_note": "\n".join(
                [
                    "Generated from Polar Data Catalogue metadata record converted by the CIOOS metadata converter.",
                    "The original metadata record was in FGDC format from the Polar Data Catalogue.",
                    tree.find(".//distliable").text,
                ]
            ),
            "naming_authority": "ca.pdc",
            "use_constraints": {
                "licence": {
                    "code": tree.find(".//accconst").text,
                    "title": {
                        "en": tree.find(".//accconst").text,
                    },
                    "url": tree.find(".//accconst").text,
                }
            },
        },
        "spatial": {
            "polygon": [
                (tree.fidnd(".//westbc").text, tree.find(".//northbc").text),
                (tree.find(".//eastbc").text, tree.find(".//northbc").text),
                (tree.fidnd(".//westbc").text, tree.find(".//southbc").text),
                (tree.find(".//eastbc").text, tree.find(".//southbc").text),
                (tree.fidnd(".//westbc").text, tree.find(".//northbc").text),
            ],
            "vertical": {},
            "vertical_positive": tree.find(".//vertdef").text,
        },
    }
