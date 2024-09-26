# CIOOS Metadata Ingestor

The CIOOS Metadata Ingestor is a tool designed to convert various metadata standards into YAML format. This package simplifies the process of transforming metadata, making it easier to manage and integrate with other systems.

## Features

- Convert metadata from multiple standards to YAML
- Easy-to-use command-line interface
- Supports batch processing of metadata files
- Extensible architecture for adding new metadata standards

## Installation

To install the package, use pip:

```sh
pip install cioos-metadata-ingestor
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

## Supported Metadata Standards

- ISO 19115
- Dublin Core
- FGDC

## Contributing

We welcome contributions! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to get involved.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For any questions or issues, please open an issue on our [GitHub repository](https://github.com/yourusername/cioos-metadata-ingestor).
