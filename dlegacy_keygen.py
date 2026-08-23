import random

ALPHABET = "YMKQ4T8FW6HXVE2ZJGC095PANRS73BD1"


def generate_key():
    # 8 random bytes + XOR checksum as 9th byte
    bytes_ = [random.randint(0, 255) for _ in range(8)]
    bytes_.append(0)
    for b in bytes_[:8]:
        bytes_[-1] ^= b

    # Encode to custom Base32
    bit_buffer = 0
    bits_in_buffer = 0
    chars = []

    for byte in bytes_:
        bit_buffer = (bit_buffer << 8) | byte
        bits_in_buffer += 8
        while bits_in_buffer >= 5:
            bits_in_buffer -= 5
            chars.append(ALPHABET[(bit_buffer >> bits_in_buffer) & 31])

    if bits_in_buffer > 0:
        chars.append(ALPHABET[(bit_buffer << (5 - bits_in_buffer)) & 31])

    # Format as groups of 5
    raw = "".join(chars)
    return "-".join(raw[i : i + 5] for i in range(0, len(raw), 5))


for _ in range(5):
    print(generate_key())
