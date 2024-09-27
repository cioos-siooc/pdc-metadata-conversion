import re

from loguru import logger
from lxml import etree as ET

# Define the namespaces
namespaces = {
    "gmd": "http://www.isotc211.org/2005/gmd",
    "gco": "http://www.isotc211.org/2005/gco",
    "gml": "http://www.opengis.net/gml",
}

MAP_ISO_LANGUAGE = {
    "eng; CAN": "en",
    "fra; CAN": "fr",
}
MAP_ISO_STATUS = {
    "underDevelopment": "ongoing",
}


def _apply_mapping(mapping: dict, value: str) -> str:
    """Apply a mapping to a value."""
    result = mapping.get(value)
    if result is None:
        logger.warning("Mapping not found for value: {}", value)
        return None
    return result


def _contact_name(author_text) -> list[str]:
    """Get the name of a contact."""
    if author_text is None:
        logger.warning("No contact name found")
        return [""]
    if ":" in author_text:
        author_text = author_text.split(":")[-1].strip()

    if "," in author_text:
        author_text = " ".join(author_text.split(",")[::-1])

    names = re.split("\s+", author_text)
    names = [name for name in names if name]
    if len(names) > 2:
        logger.warning("Name has more than two parts: {}", names)
    else:
        logger.debug("Name has two parts: {}", names)
    return names


class PDC_ISO:
    def __init__(self, file):
        self.file = file
        self.tree = ET.parse(file)

    def _create_contact(
        self, contact, in_citation: bool, role: list[str] = None
    ) -> dict:
        """Add a contact to the metadata record."""
        logger.info("Creating contact: {}", contact)
        names = _contact_name(
            self.get(".//gmd:individualName/gco:CharacterString", contact)
        )

        return {
            "givenName": " ".join(names[:-1]),
            "lastName": names[-1],
            "inCitation": in_citation,
            "indEmail": self.get(
                ".//gmd:electronicMailAddress/gco:CharacterString", contact
            ),
            "indName": " ".join(names),
            "indOrcid": "",
            # "indPosition": self.get(contact,".//cntpos"),
            "orgAddress": self.get(".//gmd:deliveryPoint/gco:CharacterString", contact),
            "orgCity": self.get(".//gmd:city/gco:CharacterString", contact),
            "orgCountry": self.get(".//gmd:country/gco:CharacterString", contact),
            "orgEmail": self.get(
                ".//gmd:electronicMailAddress/gco:CharacterString", contact
            ),
            "orgName": self.get(".//gmd:organisationName/gco:CharacterString", contact),
            "orgRor": "",
            "orgURL": "",
            "role": role or [self.get(".//gmd:CI_RoleCode", contact)],
        }

    @staticmethod
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

    def get(self, tag, item=None, default=None, level="INFO") -> str:
        """Extract specific tag element within item."""
        result = (item or self.tree).find(tag, namespaces=namespaces)
        if result is None:
            logger.log(level, "Item {} not found in ", tag, item)
            return default
        return result.text

    def get_places(self) -> list[str]:
        """Extract the places from the metadata record."""
        places = []
        for kw in self.tree.findall(
            ".//gmd:descriptiveKeywords", namespaces=namespaces
        ):
            if (
                kw.find(".//gmd:MD_KeywordTypeCode", namespaces=namespaces).text
                == "place"
            ):
                places.append(
                    kw.find(
                        ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                    ).text
                )
        return places

    def to_cioos(
        self,
        file,
        userID: str,
        filename: str,
        recordID: str,
        status: str,
        license: str,
        region: str,
        project: list[str],
        ressourceType: list[str],
        sharedWith: list[str],
        distribution: list[dict],
        eov: list[str],
    ) -> dict:
        """Parse a Polar Data Catalogue FGDC metadata record."""

        return {
            "userID": userID,
            # "organization": "",
            "title": {
                "en": self.get(".//gmd:title/gco:CharacterString"),
            },
            "abstract": {"en": self.get(".//gmd:abstract/gco:CharacterString")},
            "category": "dataset",  # TODO confirm this is related to the latest version of the schema
            "comment": "",
            "contacts": [
                self._create_contact(
                    self.tree.find(".//gmd:pointOfContact", namespaces=namespaces),
                    False,
                    ["pointOfContact"],
                ),
                self._create_contact(
                    self.tree.find(".//gmd:metadataMaintenance", namespaces=namespaces),
                    False,
                    ["custodian"],
                ),
                self._create_contact(
                    self.tree.find(".//gmd:distributor", namespaces=namespaces),
                    False,
                    ["distributor"],
                ),
                *[
                    self._create_contact(contact, False)
                    for contact in self.tree.findall(
                        ".//gmd:citedResponsibleParty", namespaces=namespaces
                    )
                ],
                # TODO missing owner role
            ],
            # TODO Convert all dates to ISO 8601 format
            "created": self.get(".//pubdate"),
            "datasetIdendifier": (self.get(".//gmd:dataSetURI") or "").split("=")[
                -1
            ],  # TODO empty in example
            "dateStart": self.get(".//gml:beginPosition"),
            "dateEnd": self.get(".//gml:endPosition"),
            "datePublished": self.get(".//gmd:dateStamp/gco:Date"),
            "dateRevised": self.get(".//revdate"),
            "distribution": distribution,
            "doiCreationStatus": "",
            "edition": self.get(".//gmd:version"),
            "eov": eov,
            "filename": filename,
            "history": [],  # Related to Lineage
            "identifier": "",  # example  "147b8485-a0b4-450d-8847-de51158b04ec"
            "keywords": {
                "en": [
                    item.strip()
                    for kw in self.tree.findall(
                        ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                    )
                    for item in kw.text.split(",")
                ],
            },
            "language": _apply_mapping(
                MAP_ISO_LANGUAGE, self.get(".//gmd:language/gco:CharacterString")
            ),
            "lastEditedBy": {"displayName": "", "email": ""},
            "license": license,  # eg "CC-BY-4.0"
            "limitations": {
                "en": (
                    "Purpose: "
                    + self.get(".//gmd:purpose/gco:CharacterString")
                    + "\n\n Supplemental Information: "
                    + self.get(".//gmd:supplementalInformation/gco:CharacterString")
                ),
            },
            "map": {
                "description": {
                    "en": self.get_places(),
                },
                "north": self.get(".//gmd:northBoundLatitude/gco:Decimal"),
                "south": self.get(".//gmd:southBoundLatitude/gco:Decimal"),
                "east": self.get(".//gmd:eastBoundLongitude/gco:Decimal"),
                "west": self.get(".//gmd:westBoundLongitude/gco:Decimal"),
                "polygon": "",
            },
            "metadataScope": "Dataset",  # TODO map to record type
            "noPlatform": False,
            "platforms": [
                {
                    "description": {"en": ""},
                    "id": "",
                    "type": "ship",
                }
            ],
            "noTaxa": True,
            "progress": _apply_mapping(
                MAP_ISO_STATUS, self.get(".//gmd:status/gmd:MD_ProgressCode")
            ),
            "project": project,
            "recordID": recordID,
            "region": region,
            "resourceType": ressourceType,  # Projects in form
            "sharedWith": {person: True for person in sharedWith},
            "status": status,
            "timeFirstPublished": self.get(".//gmd:dateStamp/gco:Date"),
            "vertical": {},
            "noVerticalExtent": True,
            "verticalExtentDirection": "depthPositive",
            "verticalExtentMax": None,  # unavailable in PDC metadata
            "verticalExtentMin": None,  # unavailable in PDC metadata
        }