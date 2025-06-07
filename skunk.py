#!/usr/bin/env python3
from sys import argv


def EncryptString(msg: str, key: str) -> str:
    """
    Encrypt a message using a repeating key with specific character transformation rules.

    Args:
        msg (str): The message to encrypt
        key (str): The encryption key

    Returns:
        str: The encrypted message
    """
    # Short, optimised but hardly readable version
    # return "".join(
    #     [
    #         (
    #             chr((ord(msg[i % len(msg)]) ^ ord(key[i % len(key)])) & 0xDF)
    #             if 0x61 <= (t := ord(msg[i % len(msg)]) ^ ord(key[i % len(key)])) <= 0x7A
    #             else chr(min(65 + ((i + 1) % len(key)) + ((i + 1) % len(msg)), 90))
    #         )
    #         for i in range(16)
    #     ]
    # )

    # Precompute message and key lengths
    msg_len, key_len = len(msg), len(key)

    # Use list comprehension for more efficient iteration
    encrypted = [
        # Apply XOR and character transformation in a single pass
        _transform_char(
            ord(msg[i % msg_len]), ord(key[i % key_len]), i + 1, msg_len, key_len
        )
        for i in range(16)
    ]

    return "".join(encrypted)


def _transform_char(
    msg_char: int, key_char: int, iteration: int, msg_len: int, key_len: int
) -> str:
    """
    Apply encryption transformation to a single character.

    Args:
        msg_char (int): ASCII value of message character
        key_char (int): ASCII value of key character
        iteration (int): Current iteration number
        msg_len (int): Length of the message
        key_len (int): Length of the key

    Returns:
        str: Transformed character
    """
    # XOR operation
    transformed_bit = msg_char ^ key_char

    # Uppercase transformation logic
    if 97 <= transformed_bit <= 122:  # lowercase letters
        return chr(transformed_bit - 32)  # convert to uppercase

    # Alternative character generation
    return chr(min(65 + (iteration % key_len) + (iteration % msg_len), 90))


def CheckKey(wName: str, wKey: str, wInts: list[int]) -> None:
    for n in wInts:
        print(wName, wKey, n)
        if makeKeyName(wName, str(n)) == wKey:
            print(wName, wKey, n)


def makeKeyName(wName: str, wCode: str) -> str:
    wName = wName.replace(" ", "").upper()
    if not wName:
        return "NOMATCH"
    wName = (wName * (16 // len(wName) + 1))[:16]
    return EncryptString(wName, wCode)


# assert makeKeyName(
#     "Macintosh_Garden", # User name, custom
#     "9183624617257869"  # Code, hardcoded in game
# ) == "TPGZXFOEYHUTEZSW"
print(makeKeyName(argv[1], "9183624617257869"))
