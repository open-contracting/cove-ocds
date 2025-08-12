import json
import os

from flattentool import decimal_datetime_default
from flattentool.input import FORMATS
from flattentool.lib import parse_sheet_configuration
from flattentool.schema import SchemaParser

JSON_FILENAME = "unflattened.json"
CSV_FILENAME = "releases.csv"


# A simple version of flattentool.unflatten().
def unflatten(path, *, file_type, metatab_schema, schema=None, output_name=None):
    data = {}

    spreadsheet_input_class = FORMATS[file_type]
    # If not writing data for download, the call is for the metatab.
    metatab_only = output_name is None
    # Source maps are only needed for data.
    unflatten_kwargs = {"with_cell_source_map": not metatab_only, "with_heading_source_map": not metatab_only}
    # disable_local_refs is True to not follow file:// URIs.

    # CARGO CULT: convert_titles is False if metatab only and True otherwise. Unsure of effect.
    # https://github.com/OpenDataServices/lib-cove/blob/19ae2ec/libcove/lib/common.py#L1381-L1403
    # https://github.com/OpenDataServices/lib-cove/blob/19ae2ec/libcove/lib/converters.py#L110
    convert_titles = not metatab_only

    # https://docs.python.org/3.12/library/codecs.html#standard-encodings
    encoding = None
    if file_type == "csv":
        for encoding in ("utf-8-sig", "cp1252"):
            try:
                with open(os.path.join(path, CSV_FILENAME), encoding=encoding) as f:
                    f.read()
                break
            except UnicodeDecodeError:
                pass
        else:
            encoding = "latin_1"

    # Metatab

    parser = SchemaParser(schema_filename=metatab_schema, disable_local_refs=True)
    parser.parse()

    spreadsheet_input = spreadsheet_input_class(
        input_name=path,
        convert_titles=convert_titles,
        use_configuration=False,
        include_sheets=["Meta"],
        root_list_path="meta",
        vertical_orientation=True,
    )
    spreadsheet_input.parser = parser
    spreadsheet_input.encoding = encoding
    spreadsheet_input.read_sheets()

    result, cell_meta, heading_meta = spreadsheet_input.fancy_unflatten(**unflatten_kwargs)

    if result:  # can be an empty list
        data.update(result[0])

    if metatab_only:
        return data, {}, {}, ""

    # Data

    base_configuration = parse_sheet_configuration(["RootListPath releases"])
    base_configuration.update(spreadsheet_input.sheet_configuration.get("Meta", {}))
    root_list_path = base_configuration.get("RootListPath", "releases")

    parser = SchemaParser(root_schema_dict=schema, disable_local_refs=True, root_id="ocid")
    parser.parse()

    spreadsheet_input = spreadsheet_input_class(
        input_name=path,
        convert_titles=convert_titles,
        base_configuration=base_configuration,
        exclude_sheets=["Meta"],
        root_list_path=root_list_path,
        root_id="ocid",
    )
    spreadsheet_input.parser = parser
    spreadsheet_input.encoding = encoding
    spreadsheet_input.read_sheets()

    result, cell_main, heading_main = spreadsheet_input.fancy_unflatten(**unflatten_kwargs)

    data[root_list_path] = result

    # Make the converted file available for download.
    with open(output_name, "w") as f:
        json.dump(data, f, indent=2, default=decimal_datetime_default)
    # We don't want decimals and datetimes when processing the data.
    with open(output_name, "rb") as f:
        data = json.load(f)

    cell_source_map_data = {key[7:]: value for key, value in cell_meta.items()}  # strip "meta/0/"
    heading_source_map_data = {key[5:]: value for key, value in heading_meta.items()}  # strip "meta/"
    cell_source_map_data.update(cell_main)
    heading_source_map_data.update(heading_main)

    return data, cell_source_map_data, heading_source_map_data, encoding
