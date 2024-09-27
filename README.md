# PDC to CIOOS Conversion

PDC to CIOOS metadata conversion.

## Installation

To install the package, use poetry:

```sh
poetry install
```

## Usage

To convert a metadata file to YAML, use the following command:

```sh
cioos_metadata_converter convert <input_file> <output_file>
```

### Example

```sh
cioos-metadata-ingestor convert metadata.xml metadata.yaml
```
