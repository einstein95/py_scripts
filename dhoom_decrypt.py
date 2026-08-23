#!/usr/bin/env python3
"""
Decryptor for two related but distinct RPG Maker MV Dhoom plugins that both
produce ".soldata" files:

  1. Dhoom_DataEncryption  -> encrypts /data/*.json files
  2. Dhoom_ImageEncryption (internally named Dhoom.Live2DContacts in the
     source, unrelated to its actual purpose) -> encrypts image files
     (img/pictures, img/characters, img/faces, etc. and Live2D assets)

Both use AES-256-CBC + PKCS#7, with a fixed key baked into the plugin and a
per-file IV derived from the filename (no random IV, nothing extra stored
in the .soldata file). But the two plugins differ in three important ways:

  - They use DIFFERENT fixed AES keys (each imported as its own Web Crypto
    JWK "oct" key).
  - The DATA plugin writes .soldata files under their original name, so the
    IV is derived directly from the on-disk filename.
  - The IMAGE plugin instead LZString-compresses the basename (via
    LZString.compressToBase64) before writing it to disk -- see $.save() /
    $.getFiles() in DhoomImageEncryption.js.
    Critically, the IV for the image plugin is derived from the ORIGINAL,
    uncompressed basename (see $.getIv(), called with the plain logical
    path in $.openAndDecrypt before it gets LZString-compressed for the
    actual HTTP fetch) -- so you must LZString-decompress the on-disk name
    first to recover the string used for IV derivation.

IV derivation (both plugins, once you have the right "name" string):
    name = name.replace(<finExtension .soldata>, <real extension>)
    base = basename(name) without extension
    iv   = first 16 chars of base as raw char codes, zero-padded to 16 bytes

Padding: standard PKCS#7 (Web Crypto's AES-CBC default).
"""

import base64
import sys
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

try:
    from lzstring import LZString
except ImportError:
    LZString = None

# --- Dhoom_DataEncryption: JWK key for /data/*.json -> *.soldata ---
_DATA_KEY_B64URL = "XXXXmae0qBokfe91IvZZZZQBWDAnoDV8QQQQ938XXXX"

# --- Dhoom_ImageEncryption: JWK key for images/Live2D -> *.soldata ---
_IMAGE_KEY_B64URL = "HARDmae0qBokfe91IvTiTSQBWDAnoPOEPmr5938C0RE"

DATA_EXT = ".json"
IMAGE_EXT = ".png"
FIN_EXT = ".soldata"


def _b64url_to_key(s: str) -> bytes:
    s += "=" * (-len(s) % 4)  # restore base64 padding
    return base64.urlsafe_b64decode(s)


def load_data_key() -> bytes:
    return _b64url_to_key(_DATA_KEY_B64URL)


def load_image_key() -> bytes:
    return _b64url_to_key(_IMAGE_KEY_B64URL)


def _iv_from_name(base_no_ext: str) -> bytes:
    iv = bytearray(16)
    for i, ch in enumerate(base_no_ext[:16]):
        iv[i] = ord(ch) & 0xFF
    return bytes(iv)


def derive_iv_data(filename: str) -> bytes:
    """Dhoom.DataEncryption.$.getIv(): on-disk filename is the real name."""
    name = filename.lower().replace(FIN_EXT, DATA_EXT)
    base = Path(name).name
    if "." in base:
        base = base[: base.rfind(".")]
    return _iv_from_name(base)


def derive_iv_image(on_disk_stem: str) -> bytes:
    """
    Dhoom.ImageEncryption.$.getIv(): IV comes from the ORIGINAL basename,
    but the on-disk filename stem is LZString.compressToBase64(original
    basename). Restore '=' padding (games replace it with '_' on disk),
    then LZString-decompress to recover the real name before hashing it
    into the IV.
    """
    if LZString is None:
        raise RuntimeError("pip install lzstring --break-system-packages")
    lz = LZString()
    original_name = lz.decompressFromBase64(on_disk_stem)
    if original_name is None:
        raise ValueError(
            f"Failed to LZString-decompress filename stem: {on_disk_stem!r}"
        )
    return _iv_from_name(original_name)


def decrypt_bytes(data: bytes, iv: bytes, key: bytes) -> bytes:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(data), AES.block_size)


def decrypt_data_file(path: Path, key: bytes) -> bytes:
    iv = derive_iv_data(path.name)
    plaintext = decrypt_bytes(path.read_bytes(), iv, key)
    return plaintext


def decrypt_image_file(path: Path, key: bytes) -> bytes:
    iv = derive_iv_image(path.stem)
    return decrypt_bytes(path.read_bytes(), iv, key)


def decrypt_folder(in_dir: str, out_dir: str):
    data_key = load_data_key()
    image_key = load_image_key()
    in_path = Path(in_dir)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    files = sorted(in_path.glob("*.soldata"))
    if not files:
        print(f"No .soldata files found in {in_path}")
        return

    for f in files:
        try:
            out_fn = LZString.decompressFromBase64(f.stem)
            png_bytes = decrypt_image_file(f, image_key)
            dest = out_path / (out_fn + ".png")
            dest.write_bytes(png_bytes)
            print(f"[+] {f.name} -> {dest.name} (image)")
            continue
        except Exception as e:
            pass

        try:
            obj = decrypt_data_file(f, data_key)
            dest = out_path / (f.stem + ".json")
            dest.write_bytes(obj)
            print(f"[+] {f.name} -> {dest.name} (data)")
            continue
        except Exception:
            pass


if __name__ == "__main__":
    if len(sys.argv) == 3:
        decrypt_folder(sys.argv[1], sys.argv[2])
    else:
        print(
            "Usage: python dhoom_decrypt.py <folder_with_.soldata_files> <output_folder>"
        )
        sys.exit(1)
