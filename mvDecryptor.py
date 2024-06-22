#!/usr/bin/env python3
# RPG Maker MV Decryption Script
#
# Originally created by SilicaAndPina 1/12/2018

import os
import json
import struct
import tqdm

decryptedExt = {".rpgmvo": ".ogg", ".rpgmvm": ".m4a", ".rpgmvp": ".png"}
encryptedExt = {v: k for k, v in decryptedExt.items()}
good_ogg = b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x0c'"
good_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
good_webp = b'RIFF\xa2U\x00\x00WEBPVP8X'


# XOR encryption / decryption
def xor(data: bytes, key: bytes) -> bytes:
    key_len = len(key)
    return bytes((data[i] ^ key[i % key_len]) for i in range(len(data)))


def decryptFilename(encryptedFilename: str) -> str:
    filename, extension = os.path.splitext(encryptedFilename)
    if not extension:
        filename = ''
        extension = os.path.basename(encryptedFilename)
    if extension[-1] == "_":
        return encryptedFilename[:-1]
    return filename + decryptedExt[extension]


def encryptFilename(decryptedFilename: str, gameVersion: str) -> str:
    if gameVersion == "mz":
        return decryptedFilename + "_"
    else:
        filename, extension = os.path.splitext(decryptedFilename)
        return filename + encryptedExt[extension]


def isEncryptedFile(path: str) -> bool:
    file_extension = path[-7:]
    return file_extension in decryptedExt or file_extension[-1] == "_"


def isDecryptedFile(path: str) -> bool:
    file_extension = path[-4:]
    return file_extension in encryptedExt


def decryptFile(encryptedFilename: str, key: bytes) -> None:
    with open(encryptedFilename, "rb") as f:
        f.seek(16)
        cyphertext = f.read(16)
        if cyphertext == b"00000NEMLEI00000":
            # Decrypt "The Coffin of Andy and Leyley" demo
            remaining_data = ord(f.read(1))
            f.read(remaining_data)
            cyphertext = f.read(16)
        plaintext = xor(cyphertext, key)
        with open(decryptFilename(encryptedFilename), "wb") as outfile:
            outfile.write(plaintext + f.read())

def bruteforceKey(data: bytes, key: str) -> None:
    if key in ['rpgvmp', 'png_']:
        print('PNG:', xor(data, good_png).hex())
        print('WEBP:', xor(data, good_webp).hex())
    elif key in ['rpgvmo', 'ogg_']:
        print('OGG:', xor(data, good_ogg).hex())

def encryptFile(decryptedFilename: str, key: bytes, gameVersion: str) -> None:
    header = struct.pack(">5s4xH5x", b"RPG" + gameVersion.upper().encode(), 0x301)
    with open(decryptedFilename, "rb") as f:
        plaintext = f.read(16)
        cyphertext = xor(plaintext, key)
        with open(encryptFilename(decryptedFilename, gameVersion), "wb") as outfile:
            outfile.write(header + cyphertext + f.read())


def processEntireGame(gameDir: str, isEncrypt: str) -> None:
    if not args.brute:
        with open(gameDir + "/data/System.json", "rb") as f:
            SystemJson = json.load(f)

        key = bytes.fromhex(SystemJson.get("encryptionKey", ""))

    if os.path.exists(gameDir + "/js/rpg_core.js"):
        gameVersion = "mv"
    elif os.path.exists(gameDir + "/js/rmmz_core.js"):
        gameVersion = "mz"
    else:
        print("Unable to determine RPG Maker type")
        exit(1)

    for path, _, files in os.walk(gameDir):
        if args.brute:
            files = [f for f in files if isEncryptedFile(f)]
            for fn in files:
                filePath = os.path.join(path, fn)
                with open(filePath, "rb") as f:
                    f.seek(16)
                    encBytes = f.read(16)
                    bruteforceKey(encBytes, fn.split('.')[-1])
            continue


        if isEncrypt:
            files = [f for f in files if isDecryptedFile(f)]
        else:
            files = [f for f in files if isEncryptedFile(f)]

        if not files:
            continue

        for f in tqdm.tqdm(files):
            filePath = os.path.join(path, f)
            if isEncrypt:
                if not filePath.endswith(
                    ("icon/icon.png", "img/system/Loading.png", "img/system/Window.png")
                ):
                    encryptFile(filePath, key, gameVersion)
            else:
                decryptFile(filePath, key)
            os.remove(filePath)

    SystemJson["hasEncryptedImages"] = SystemJson["hasEncryptedAudio"] = isEncrypt

    with open(gameDir + "/data/System.json", "w") as f:
        json.dump(SystemJson, f, separators=(",", ":"), ensure_ascii=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Script to decrypt or encrypt the entire game"
    )
    parser.add_argument("game_path", help="Path to the game")
    parser.add_argument(
        "-e", "--encrypt", action="store_true", help="Encrypt the entire game"
    )
    parser.add_argument("-b", "--brute", action="store_true", help="Find the key from PNG")
    args = parser.parse_args()

    processEntireGame(args.game_path, args.encrypt)
