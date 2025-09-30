import os
import re
from glob import glob
from pathlib import Path

search_paths = [
    Path(os.getcwd()),
    Path(
        "/Users/pc/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV"
    ),
    *[
        Path(i)
        for i in glob(
            "/Users/pc/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV/*dlc/*/"
        )
    ],
]


def check_exists(path) -> tuple[bool, Path | None]:
    file_name = path.name
    for base_folder in search_paths:
        folder = base_folder / path.parent
        if not folder.exists():
            continue

        if file_name in os.listdir(folder):
            return True, path

        extensions = [".png", ".dds", ".tga"]
        for ext in extensions:
            p = (folder / file_name).with_suffix(ext)
            # print(p)
            if p.name in os.listdir(folder):
                return False, p.relative_to(base_folder)

        if (folder / file_name).exists():
            for i in os.listdir(folder):
                if i.lower() == file_name.lower():
                    return False, (folder / i).relative_to(base_folder)
            return False, path

    return False, None


# This script checks for texture files that are referenced in .gfx files but do not exist in the same directory.
files = glob("./interface/**/*.gfx", recursive=True)
for file in files:
    f = open(file).read()
    texfiles = re.findall(r'^\s+textureFile = "([^"]+)', f, re.I | re.M)
    for t in texfiles:
        p = Path(t)
        exists, path = check_exists(p)
        if not exists and path is not None:
            print(f"{file}: {p} -> {path}")
        elif not exists:
            print(f"{file} Missing texture: {p}")
        # else:
        #     print(f"Texture exists: {p} -> {path}")
