import json
import platform
from hashlib import md5
from itertools import cycle
from pathlib import Path
from sys import argv

KEY = b"23f986b23f98623bf923786rfb23976fb"


def decrypt_file(input: Path | bytes) -> bytes:
    if isinstance(input, Path):
        data = open(input, "rb").read()
    else:
        data = input
    decrypted = bytes(b ^ k for b, k in zip(data, cycle(KEY)))
    return decrypted


def get_file_path() -> Path:
    # Automatically find the file path based on the operating system
    # Windows: %APPDATA%\FINDR-Windows\Local Store\padding.blob
    # macOS: $HOME/Application Support/FINDR-Windows/Local Store/padding.blob
    # Linux: $HOME/.local/share/FINDR-Windows/Local Store/padding.blob
    system = platform.system()
    if system == "Windows":
        return Path(
            Path.home() / "AppData" / "Local",  # Roaming?
            "FINDR-Windows",
            "Local Store",
            "padding.blob",
        )
    elif system == "Darwin":  # macOS
        return Path(
            Path.home(),
            "Library",
            "Application Support",
            "FINDR-Windows",
            "Local Store",
            "padding.blob",
        )
    elif system == "Linux":
        return Path(
            Path.home(),
            ".local",
            "share",
            "FINDR-Windows",
            "Local Store",
            "padding.blob",
        )
    else:
        raise Exception("Unsupported operating system")


if __name__ == "__main__":
    operation = argv[2] if len(argv) > 2 else "decrypt"
    if operation not in ["decrypt", "encrypt"]:
        print("Usage: python decrypt_fairyfinder_paddingblob.py [decrypt|encrypt]")
        exit(1)
    file_path = get_file_path()
    save_file = file_path.parent / "#SharedObjects" / "666169727946494E4452_1.sol"
    decrypted_path = Path("phonebook.json")
    if file_path.exists():
        if decrypted_path.exists():
            data = decrypt_file(
                json.dumps(
                    json.loads(decrypted_path.read_bytes()), separators=(",", ":")
                ).encode()
            )
            file_path.write_bytes(data)
            print(f"Encrypted file saved as {file_path}")
            print(
                f'Make sure to update "{save_file}" with chkfc: {md5(data).hexdigest()}'
            )
        else:
            print(f"chkfc: {md5(file_path.read_bytes()).hexdigest()}")
            data = decrypt_file(file_path)
            decrypted_path.write_bytes(data)
            print(f"Decrypted file saved as phonebook.json")
    else:
        print(f"File not found: {file_path}")
