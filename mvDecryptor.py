#!/usr/bin/env python3
# RPG Maker MV Decryption Script
#
# Originally created by SilicaAndPina 1/12/2018

import json
import os

import tqdm

DECRYPTED_EXTENSIONS = {".rpgmvo": ".ogg", ".rpgmvm": ".m4a", ".rpgmvp": ".png"}
ENCRYPTED_EXTENSIONS = {v: k for k, v in DECRYPTED_EXTENSIONS.items()}
# GOOD_OGG = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x0c'"
GOOD_PNG = b"\x89PNG\r\n\x1a\x0a\x00\x00\x00\x0dIHDR"
# GOOD_WEBP = b'RIFF\xa2U\x00\x00WEBPVP8X'


# XOR encryption / decryption
def xor(data: bytes, key: bytes) -> bytes:
    return bytes(byte ^ key[i % len(key)] for i, byte in enumerate(data))


def decrypt_filename(encrypted_filename: str) -> str:
    filename, extension = os.path.splitext(encrypted_filename)
    extension = extension or os.path.basename(encrypted_filename)
    return (
        encrypted_filename[:-1]
        if extension.endswith("_")
        else filename + DECRYPTED_EXTENSIONS.get(extension, "")
    )


def encrypt_filename(decrypted_filename: str, game_version: str) -> str:
    filename, extension = os.path.splitext(decrypted_filename)
    return (
        decrypted_filename + "_"
        if game_version == "mz"
        else filename + ENCRYPTED_EXTENSIONS.get(extension, "")
    )


def is_encrypted_file(path: str) -> bool:
    return any(path.endswith(ext) for ext in DECRYPTED_EXTENSIONS) or path.endswith("_")


def is_decrypted_file(path: str) -> bool:
    return any(path.endswith(ext) for ext in ENCRYPTED_EXTENSIONS)


def decrypt_file(encrypted_filename: str, key: bytes, game_version: str) -> None:
    with open(encrypted_filename, "rb") as decryptfile:
        decryptfile.seek(16)
        ciphertext = decryptfile.read(16)

        # Special case for "The Coffin of Andy and Leyley" demo
        if ciphertext == b"00000NEMLEI00000":
            decryptfile.seek(
                17 + ord(decryptfile.read(1))
            )  # Skip the remaining data and adjust position
            ciphertext = decryptfile.read(16)

        plaintext = xor(ciphertext, key)
        with open(decrypt_filename(encrypted_filename), "wb") as outfile:
            outfile.write(plaintext + decryptfile.read())


def bruteforce_key(data: bytes, extension: str) -> None:
    if extension in ENCRYPTED_EXTENSIONS.values():
        known_headers = {"rpgmvp": GOOD_PNG}  # Add more headers if needed
        if extension in known_headers:
            print(f"{extension.upper()}:", xor(data, known_headers[extension]).hex())


def encrypt_file(decrypted_filename: str, key: bytes, game_version: str) -> None:
    header = (
        b"RPG"
        + game_version.upper().encode()
        + b"\x00\x00\x00\x00\x03\x01\x00\x00\x00\x00\x00"
    )
    with open(decrypted_filename, "rb") as infile, open(
        encrypt_filename(decrypted_filename, game_version), "wb"
    ) as outfile:
        plaintext = infile.read(16)
        outfile.write(header + xor(plaintext, key) + infile.read())


def process_entire_game(
    game_directory: str, encrypt: bool, use_bruteforce: bool
) -> None:
    encryption_key = b""
    system_json = {}

    if not use_bruteforce:
        try:
            with open(
                os.path.join(game_directory, "data", "System.json"), "rb"
            ) as systemjson:
                system_json = json.load(systemjson)
                encryption_key = bytes.fromhex(system_json.get("encryptionKey", ""))
        except FileNotFoundError:
            print("System.json not found. Ensure the game directory is correct.")
            exit(1)

    game_version = (
        "mv"
        if os.path.exists(os.path.join(game_directory, "js", "rpg_core.js"))
        else (
            "mz"
            if os.path.exists(os.path.join(game_directory, "js", "rmmz_core.js"))
            else None
        )
    )

    if not game_version:
        print("Unable to determine RPG Maker type")
        exit(1)

    if not use_bruteforce:
        print(f"Encryption Key: {encryption_key.hex()}")

    for path, _, files in os.walk(game_directory):
        if use_bruteforce:
            for filename in filter(is_encrypted_file, files):
                file_path = os.path.join(path, filename)
                with open(file_path, "rb") as brutefile:
                    brutefile.seek(16)
                    encrypted_bytes = brutefile.read(16)
                    bruteforce_key(encrypted_bytes, os.path.splitext(filename)[1][1:])
                return
            continue

        target_files = filter(
            is_decrypted_file if encrypt else is_encrypted_file, files
        )

        for file in tqdm.tqdm(target_files, desc="Processing files"):
            file_path = os.path.join(path, file)
            if encrypt and file_path.endswith(
                ("icon/icon.png", "img/system/Loading.png", "img/system/Window.png")
            ):
                continue

            (encrypt_file if encrypt else decrypt_file)(
                file_path, encryption_key, game_version
            )
            os.remove(file_path)

    if not use_bruteforce:
        system_json["hasEncryptedImages"] = system_json["hasEncryptedAudio"] = encrypt
        with open(os.path.join(game_directory, "data", "System.json"), "w") as new_file:
            json.dump(system_json, new_file, separators=(",", ":"), ensure_ascii=False)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Script to decrypt or encrypt the entire game"
    )
    parser.add_argument("game_path", help="Path to the game")
    parser.add_argument(
        "-e", "--encrypt", action="store_true", help="Encrypt the entire game"
    )
    parser.add_argument(
        "-b", "--brute", action="store_true", help="Find the key from PNG"
    )
    args = parser.parse_args()

    process_entire_game(args.game_path, args.encrypt, args.brute)


if __name__ == "__main__":
    main()
