from __future__ import annotations

from dataclasses import fields as get_fields, is_dataclass
from gceutils import AbstractTreePath
from pathlib import Path
import pmp_manip as p
from typing import Any


EXTENSION_URL_BASE = (
    #"https://raw.githubusercontent.com/GermanCodeEngineer/PM-Extensions/"
    #"refs/heads/main/extensions"
    "http://localhost:5173/extensions"
)

def configure() -> None:
    cfg = p.get_default_config()
    handler = (
        #lambda url: url.startswith(
        #    "https://raw.githubusercontent.com/GermanCodeEngineer/PM-Extensions/"
        #)
        lambda url: True
    )
    cfg.ext_info_gen.is_trusted_extension_origin_handler = handler
    cfg.ext_info_gen.node_js_exec_timeout = 10.0
    try:
        p.init_config(cfg)
    except p.MANIP_ConfigurationError as error:
        if "has already been initialized" in str(error):
            pass
        else:
            raise

def as_json(obj: Any) -> Any:
    """
    Converts a dataclass to a JSON-serializable dictionary.
    """
    if is_dataclass(obj):
        data = {"_type_": type(obj).__name__}
        for field in get_fields(obj):
            value = getattr(obj, field.name)
            data[field.name] = as_json(value)
        return data
    elif isinstance(obj, list):
        return [as_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {as_json(key): as_json(value) for key, value in obj.items()}
    else:
        return obj

    #if not is_dataclass(obj):
    #    raise ValueError("as_json can only be used with dataclasses.")

def convert_to_better(source_file: Path, output_file: Path) -> None:
    configure()

    frproject = p.FRProject.from_file(source_file)
    frproject.add_all_extensions_to_info_api(p.info_api)
    project = frproject.to_second(p.info_api)

    print(50 * "=", "Converted Project to SR", 50 * "=")
    print(project)

    project.validate(AbstractTreePath(), p.info_api)

    project_json = as_json(project)

    print(50 * "=", "Converted Project to JSON", 50 * "=")
    print(project_json)





def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Convert PM save files to a better format.")
    parser.add_argument("source_file", help="Path to the source save file")
    parser.add_argument("output_file", help="Path to the output file")
    args = parser.parse_args()

    convert_to_better(Path(args.source_file), Path(args.output_file))


if __name__ == "__main__":
    main()
