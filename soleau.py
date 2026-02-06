from sys import argv


def encode(s: str, step=55) -> bytes:
    """
    Encodes a string by shifting each character based on its position.
    Shift amount = 55 + position (1-indexed)
    """
    d = s.encode()
    return bytes(c + step + i for i, c in enumerate(d, start=1))
    return "".join(chr(ord(c) + step + i) for i, c in enumerate(s, start=1))


def decode(s: str, step=55) -> str:
    """
    Decodes a string by reversing the position-based character shift.
    Subtracts the same shift amount used during encoding.
    """
    return "".join(chr(ord(c) - step - i) for i, c in enumerate(s, start=1))


# Example usage
if __name__ == "__main__":
    original = argv[1]
    step = int(argv[2])
    operation = argv[3] if len(argv) == 4 else None
    encoded = encode(original, step)
    try:
        decoded = decode(original, step)
    except ValueError:
        decoded = ""

    print(f"Original:  {original}")
    if operation == "e" or None:
        print(f"Encoded:   {encoded.hex()}")
    if operation == "d" or None:
        print(f"Decoded:   {decoded!r}")
    print()
