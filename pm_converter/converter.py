from __future__ import annotations

from dataclasses import fields as get_fields, is_dataclass
from gceutils import AbstractTreePath, grepr
import json
from lxml import etree
from pathlib import Path
from PIL import Image
import pmp_manip as p
from pydub import AudioSegment
import shutil
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

def export_vector_costume(target: p.FRTarget, frcostume: p.FRCostume, srcostume: p.SRVectorCostume, output_dir: Path) -> None:
    file_path = output_dir / f"{target.name}-{frcostume.name}-{frcostume.asset_id}.svg"
    xml_content: etree._Element = srcostume.content
    etree.ElementTree(xml_content).write(
        str(file_path),
        encoding="utf-8",
        pretty_print=True,
        xml_declaration=True
    )

def export_bitmap_costume(target: p.FRTarget, frcostume: p.FRCostume, srcostume: p.SRBitmapCostumex, output_dir: Path) -> None:
    bmp_content: Image.Image = srcostume.content
    file_path = output_dir / f"{target.name}-{frcostume.name}-{frcostume.asset_id}.png"
    bmp_content.save(str(file_path), format="PNG")

def export_sound(target: p.FRTarget, frsound: p.FRSound, srsound: p.SRSound, output_dir: Path) -> None:
    audio_content: AudioSegment = srsound.content
    file_path = output_dir / f"{target.name}-{frsound.name}-{frsound.asset_id}.wav"
    audio_content.export(str(file_path), format="wav")

def unpack_project(packed_file: Path, unpacked_dir: Path) -> None:
    configure()

    frproject = p.FRProject.from_file(str(packed_file))
    project_json = as_json(frproject)
    del project_json["asset_files"]

    shutil.rmtree(unpacked_dir, ignore_errors=True)
    unpacked_dir.mkdir(parents=True, exist_ok=True)
    (unpacked_dir / "project.json").write_text(
        json.dumps(project_json, indent=4)
    )

    for target in frproject.targets:
        for frcostume in target.costumes:
            srcostume = frcostume.to_second(frproject.asset_files)
            if isinstance(srcostume, p.SRVectorCostume):
                export_vector_costume(target, frcostume, srcostume, unpacked_dir)

            elif isinstance(srcostume, p.SRBitmapCostumex):
                export_bitmap_costume(target, frcostume, srcostume, unpacked_dir)

        for frsound in target.sounds:
            srsound = frsound.to_second(frproject.asset_files)
            export_sound(target, frsound, srsound, unpacked_dir)


def pack_project(packed_file: Path, unpacked_dir: Path) -> None:
    configure()
    project_json = json.loads((unpacked_dir / "project.json").read_text())
    for sub_file in unpacked_dir.iterdir():
        if sub_file.name == "project.json":
            continue
        if sub_file.is_file():
            target_name, asset_name, asset_id = sub_file.name.split("-")
            file_extension = sub_file.name.split(".")[-1]

            # HERE: handle sounds and costumes

            with sub_file.open("rb") as f:
                asset_content = f.read()
            p.AssetFile(asset_id=asset_id, content=asset_content)
    frproject = p.FRProject.from_data(project_json, asset_files)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Convert PM save files to a better format.")
    parser.add_argument("packed_file", help="Path to the packed PM file")
    parser.add_argument("unpacked_dir", help="Path to the unpacked directory")
    args = parser.parse_args()

    #unpack_project(Path(args.packed_file), Path(args.unpacked_dir))
    pack_project(Path(args.packed_file), Path(args.unpacked_dir))


if __name__ == "__main__":
    main()
