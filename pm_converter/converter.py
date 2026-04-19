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

def export_vector_costume(target: p.FRTarget, frcostume: p.FRCostume, srcostume: p.SRVectorCostume, unpacked_dir: Path) -> None:
    file_path = unpacked_dir / f"{target.name}-{frcostume.name}.svg"
    xml_content: etree._Element = srcostume.content
    etree.ElementTree(xml_content).write(
        str(file_path),
        encoding="utf-8",
        pretty_print=True,
        xml_declaration=True
    )

def export_bitmap_costume(target: p.FRTarget, frcostume: p.FRCostume, srcostume: p.SRBitmapCostumex, unpacked_dir: Path) -> None:
    bmp_content: Image.Image = srcostume.content
    file_path = unpacked_dir / f"{target.name}-{frcostume.name}.png"
    bmp_content.save(str(file_path), format="PNG")

def export_sound(target: p.FRTarget, frsound: p.FRSound, srsound: p.SRSound, unpacked_dir: Path) -> None:
    audio_content: AudioSegment = srsound.content
    file_path = unpacked_dir / f"{target.name}-{frsound.name}.wav"
    audio_content.export(str(file_path), format="wav")

def unpack_project(packed_file: Path, unpacked_dir: Path) -> None:
    configure()

    frproject = p.FRProject.from_file(str(packed_file))
    project_json, asset_files = frproject.to_data()

    shutil.rmtree(unpacked_dir, ignore_errors=True)
    unpacked_dir.mkdir(parents=True, exist_ok=True)
    (unpacked_dir / "project.json").write_text(
        json.dumps(project_json, indent=4)
    )

    for target in frproject.targets:
        for frcostume in target.costumes:
            srcostume = frcostume.to_second(asset_files)
            if isinstance(srcostume, p.SRVectorCostume):
                export_vector_costume(target, frcostume, srcostume, unpacked_dir)

            elif isinstance(srcostume, p.SRBitmapCostume):
                export_bitmap_costume(target, frcostume, srcostume, unpacked_dir)

        for frsound in target.sounds:
            srsound = frsound.to_second(asset_files)
            export_sound(target, frsound, srsound, unpacked_dir)


def pack_project(packed_file: Path, unpacked_dir: Path) -> None:
    configure()

    project_json = json.loads((unpacked_dir / "project.json").read_text())
    frproject = p.FRProject.from_data(project_json, asset_files={}) # Pass empty asset_files for now, see below

    asset_files = {}
    for target in frproject.targets:
        for frcostume in target.costumes:
            vector_file_path = unpacked_dir / f"{target.name}-{frcostume.name}.svg"
            bitmap_file_path = unpacked_dir / f"{target.name}-{frcostume.name}.png"
            if vector_file_path.exists():
                asset_files[frcostume.md5ext] = vector_file_path.read_bytes()
            elif bitmap_file_path.exists():
                asset_files[frcostume.md5ext] = bitmap_file_path.read_bytes()
        
        for frsound in target.sounds:
            sound_file_path = unpacked_dir / f"{target.name}-{frsound.name}.wav"
            if sound_file_path.exists():
                asset_files[frsound.md5ext] = sound_file_path.read_bytes()
    
    frproject.asset_files = asset_files
    frproject.to_file(str(packed_file))

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Convert PM save files to a better format.")
    parser.add_argument("mode", choices=["pack", "unpack"], help="Operation mode: 'pack' or 'unpack'")
    parser.add_argument("packed_file", help="Path to the packed PM file")
    parser.add_argument("unpacked_dir", help="Path to the unpacked directory")

    args = parser.parse_args()

    if args.mode == "unpack":
        unpack_project(Path(args.packed_file), Path(args.unpacked_dir))
    else:
        pack_project(Path(args.packed_file), Path(args.unpacked_dir))


if __name__ == "__main__":
    main()
