def deobfuscate_ini_string(text: str) -> str:
    """
    Uppercase: ROT15
    Lowercase: ROT7
    """
    result = []
    for char in text.encode("ascii"):
        if 65 <= char <= 90:
            # Shift by 15
            char = (char - 65 + 15) % 26 + 65
        elif 97 <= char <= 122:
            # Shift by 7
            char = (char - 97 + 7) % 26 + 97
        result.append(char)
    return bytes(result).decode()


def deobfuscate_ini_dir(text: str) -> str:
    """
    Deobfuscates Dir INI value
    Uppercase: ROT17
    Lowercase: ROT7
    """
    result = []
    for char in text.encode("ascii"):
        if 65 <= char <= 90:
            char = (char + 4) % 26 + 65
        elif 97 <= char <= 122:
            char = (char + 14) % 26 + 97
        result.append(char)
    return bytes(result).decode()


print(deobfuscate_ini_string(open("MGP2.INI").read()))
