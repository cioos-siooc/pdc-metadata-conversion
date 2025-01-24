import re
import uuid
import yaml
from pathlib import Path
from datetime import datetime, timezone
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
    "completed": "completed",
}

NAMES_MAPPING = {
    "Polar Data Catalogue": "Polar Data Catalogue",
}

ROLES_MAPPING = {
    "Originator": "originator",
    "Collaborator": "collaborator",
    "Author": "author",
    "coAuthor": "coauthor",
    "pointOfContact": "pointOfContact",
    "principalInvestigator": "principalInvestigator",
}

EOV_TO_KEYWORDS = yaml.safe_load(open(Path(__file__).parent / "eov_to_keywords.yaml"))


def _parse_date(date: str) -> str:
    """Parse a date."""
    return datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc).isoformat().replace("+00:00","Z")
    

def _apply_role_mapping(role: str) -> str:
    """Apply a mapping to a role."""
    result = ROLES_MAPPING.get(role)

    if result is None and role in ROLES_MAPPING.values():
        return role
    elif result is None:
        logger.warning("Mapping not found for role: {}", role)
        return None
    return result


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
        logger.debug("No contact name found")
        return [""]
    if ":" in author_text:
        author_text = author_text.split(":")[-1].strip()

    if "," in author_text:
        author_text = " ".join(author_text.split(",")[::-1])

    names = re.split(r"\s+", author_text)
    names = [name for name in names if name]
    if " ".join(names) in NAMES_MAPPING:
        names = [NAMES_MAPPING[" ".join(names)]]
    elif len(names) > 2:
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
        logger.debug("Creating contact: {}", contact)
        names = _contact_name(
            self.get(".//gmd:individualName/gco:CharacterString", contact)
        )

        return {
            "givenNames": " ".join(names[:-1]),
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
            "role": role
            or [_apply_role_mapping(self.get(".//gmd:CI_RoleCode", contact))],
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

    def get(self, tag, item=None, default=None, level="DEBUG") -> str:
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

    def _combine_contacts(self, contacts) -> dict:
        """Combine macthing contacts and join roles"""
        new_contacts = []
        new_contacts_roles = []
        for contact in contacts:
            roles = contact.pop("role")
            if contact not in new_contacts:
                new_contacts += [contact]
                new_contacts_roles += [roles]
            else:
                contact_id = new_contacts.index(contact)
                if roles:
                    new_contacts_roles[contact_id] += roles

        # Add back roles
        for i, new_contact in enumerate(new_contacts):
            new_contact["role"] = new_contacts_roles[i]
        return new_contacts

    def _get_keywords(self) -> list[str]:
        """Retrive theme type keywords."""
        keywords = []
        for kw in self.tree.findall(
            ".//gmd:descriptiveKeywords", namespaces=namespaces
        ):
            if (
                kw.find(".//gmd:MD_KeywordTypeCode", namespaces=namespaces).text
                == "theme"
            ):
                keywords += [
                    item.text
                    for item in kw.findall(
                        ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                    )
                ]
        if not keywords:
            logger.warning("No keywords found in metadata")
        return keywords

    def _get_eov_from_keywords(self) -> list[str]:
        """Extract EOV from keywords."""

        def _has_keyword(keyword):
            """Return the eovs that have the keyword."""
            return [
                eov
                for eov, keywords in EOV_TO_KEYWORDS.items()
                if keywords and keyword in keywords
            ]

        keywords = self._get_keywords()
        eovs = []
        for keyword in keywords:
            eovs += _has_keyword(keyword)
        if not eovs:
            logger.warning("No EOV found in keywords: {}", keywords)
        return list(set(eovs))

    def to_cioos(
        self,
        userID: str,
        filename: str,
        recordID: str,
        status: str,
        license: str,
        region: str,
        project: list[str],
        ressourceType: list[str],
        shares: list[str],
        distribution: list[dict],
        eov: list[str],
        identifier: uuid.UUID,
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
            "contacts": self._combine_contacts(
                [
                    self._create_contact(
                        self.tree.find(".//gmd:pointOfContact", namespaces=namespaces),
                        False,
                        ["pointOfContact"],
                    ),
                    self._create_contact(
                        self.tree.find(
                            ".//gmd:metadataMaintenance", namespaces=namespaces
                        ),
                        False,
                        ["custodian"],
                    ),
                    self._create_contact(
                        self.tree.find(".//gmd:distributor", namespaces=namespaces),
                        False,
                        ["distributor"],
                    ),
                    *[
                        self._create_contact(contact, in_citation=True)
                        for contact in self.tree.findall(
                            ".//gmd:CI_Citation/gmd:citedResponsibleParty",
                            namespaces=namespaces,
                        )
                    ],
                    # TODO missing owner role
                ]
            ),
            "created":  _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "datasetIdentifier": "https://doi.org/10.21963/"
            + self.get(".//gmd:dataSetURI/gco:CharacterString").split("=")[-1],
            "dateStart": _parse_date(self.get(".//gml:beginPosition")),
            "dateEnd": _parse_date(self.get(".//gml:endPosition")),
            "datePublished": _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "dateRevised": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
            "distribution": distribution,
            "doiCreationStatus": "",
            "edition": self.get(".//gmd:version"),
            "eov": self._get_eov_from_keywords(),
            "filename": filename,
            "history": [],  # Related to Lineage
            "identifier": str(
                identifier
            ),  # example  "147b8485-a0b4-450d-8847-de51158b04ec"
            "keywords": {
                "en": list(
                    set(
                        item.strip()
                        for kw in self.tree.findall(
                            ".//gmd:keyword/gco:CharacterString", namespaces=namespaces
                        )
                        for item in kw.text.split(",")
                    )
                ),
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
                    "en": " - ".join(self.get_places()),
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
                    "description": {"en": "CCGS Amundsen", "fr": "NGCC Amundsen"},
                    "id": "18DL",
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
            "sharedWith": {person: True for person in shares},
            "status": status,
            "timeFirstPublished": _parse_date(self.get(".//gmd:dateStamp/gco:Date")),
            "vertical": {},
            "noVerticalExtent": True,
            "verticalExtentDirection": "depthPositive",
            "verticalExtentMax": None,  # unavailable in PDC metadata
            "verticalExtentMin": None,  # unavailable in PDC metadata
            "associated_resources": [
                {
                    "association_type": "IsIdenticalTo",
                    "association_type_iso": "crossReference",
                    "authority": "URL",
                    "code": self.get(".//gmd:dataSetURI/gco:CharacterString"),
                    "title": {
                        "en": "Polar Data Catalogue equivalent record",
                        "fr": "Enregistrement équivalent du Catalogue de données polaires",
                    },
                }
            ],
        }