# PDC to CIOOS Conversion

This package is use to convert the [Polar Data Catalogue](https://www.polardata.ca/) metadata records to a CIOOS firebase json compliant format. 

## Installation

To install the package, use uv. First create an environment:

```shell
uv venv
```

## Usage

1. Download specific PDC CCINs locally

    ```shell
    uv run python main.py download CCINS --xml-type iso --output-dir output
    ```

    Where CCINS can be a series of ccins from the pdc catalogue or from an
    excel document (define the sheet and column if that's the input)

2. To convert a metadata file to their CIOOS json equivalent, use the following command:

    ```sh
    run run python main.py convert --input <input_file> --output <output_file>
    ```

    You can define the user owner of the document and users to which the records are shared.
    
Once the file generated it can be manually added to the firebase database. 

> [!CAUTION}
> Please back up the firebase database prior to making any changes!!