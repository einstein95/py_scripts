import argparse

PRESETS = {
    "A": "GAGEAA",  # o1_loadTot(avt002.tot);                   level 3
    "B": "BULBEB",  # var32_1488 = 3; o1_loadTot(avt007.tot);   level 7
    "C": "CANONC",  # o1_loadTot(avt004.tot);                   level 4
    "D": "TOTODD",  # o1_loadTot(avt00.tot);                    level 2
    "E": "DRUIDE",  # o1_loadTot(avt005.tot);                   level 5
    "F": "FOUDRF",  # var32_1488 = 1; o1_loadTot(avt001.tot);   level 6
    "G": "GATEAG",  # o1_loadTot(avt009.tot);                   level 9
    "H": "HAHAHH",  # o1_loadTot(avt006.tot);                   level 8
    "I": "HIHIHI",  # o1_loadTot(avt009.tot);                   level 9 again???
    "J": "JONASJ",  # o1_loadTot(avt008.tot);                   level 10
    "K": "FLUTEK",  # o1_loadTot(avt010.tot);                   level 11
    "L": "DROITL",  # o1_loadTot(avt011.tot);                   level 12
    "M": "BANJOM",  # var32_1488 = 8; o1_loadTot(avt012.tot);   level 13
    "N": "CUBENN",  # var32_1488 = 8; o1_loadTot(avt014.tot);   level 14
    "O": "RALERO",  # var32_1488 = 8; o1_loadTot(avt015.tot);   level 15
    "P": "RATOPP",  # var32_1488 = 8; o1_loadTot(avt016.tot);   level 16
    "Q": "GOBLIQ",  # var32_1488 = 8; o1_loadTot(avt017.tot);   level 17
    "R": "IIINSR",  # var32_1488 = 8; o1_loadTot(avt018.tot);   level 18
    "S": "LEMEIS",  # o1_loadTot(avt019.tot);                   level 19
    "T": "LLEURT",  # o1_loadTot(avt020.tot);                   level 20
    "U": "JEUDEU",  # o1_loadTot(avt021.tot);                   level 21
    "V": "ROLEDV",  # o1_loadTot(avt022.tot);                   level 22
    "W": "ETOUTW",  # o1_loadTot(final.tot);                    level 1???
    "X": "LESTPX",  # quits game
}
PRESETS_CD = {
    **PRESETS,
    # changed due to an unintentional "KKKPURE" code being generated for preset R with energy 10
    "R": "ABCNSR",  # level 18
}


def make_code(preset_key: str, energy: int, presets: dict = PRESETS) -> str:
    """
    Generate a valid code for a given preset key and energy.
    Energy is distributed evenly across the 5 payload characters,
    with any remainder added to the first characters.
    """
    preset_key = preset_key.upper()
    if preset_key not in presets:
        raise ValueError(
            f"Invalid preset key '{preset_key}'. Choose from: {', '.join(presets)}"
        )

    preset = presets[preset_key]

    # Distribute energy across 5 payload characters
    base, remainder = divmod(energy, 5)
    offsets = [base + (1 if i < remainder else 0) for i in range(5)]

    # Build first 5 chars by shifting preset
    payload = []
    for i in range(5):
        c = ord(preset[i]) + offsets[i]
        # Wrap within A-Z
        c = (c - ord("A")) % 26 + ord("A")
        payload.append(chr(c))

    # 6th character is the preset key itself
    payload.append(preset_key)

    # 7th character is the checksum: sum of first 6, mod 26, + 'A'
    checksum = sum(ord(c) for c in payload) % 26 + ord("A")
    payload.append(chr(checksum))

    return "".join(payload)


def verify_code(
    code: str, presets: dict = PRESETS
) -> tuple[bool | None, str | None, int | None]:
    """Verify a code and return (valid_checksum, preset_key, energy)."""
    code = code.upper().strip()
    if len(code) != 7:
        return None, None, None

    preset_key = code[5]
    if preset_key not in presets:
        return False, preset_key, None

    # Verify checksum
    expected_checksum = sum(ord(c) for c in code[:6]) % 26 + ord("A")
    valid = ord(code[6]) == expected_checksum

    # Calculate energy
    preset = presets[preset_key]
    energy = sum(ord(code[i]) - ord(preset[i]) for i in range(5))

    return valid, preset_key, energy


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="=== Code Generator ===",
        epilog=f"Available presets: {', '.join(PRESETS.keys())} (use --cd for PRESETS_CD)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--cd", action="store_true", help="Use PRESETS_CD instead of PRESETS"
    )
    parser.add_argument("preset_key", type=str, help="Preset key (A-X)")
    parser.add_argument(
        "energy",
        type=int,
        choices=range(11),
        metavar="ENERGY",
        help="Desired energy level (0-10)",
    )

    args = parser.parse_args()

    # Select the appropriate presets dictionary
    presets = PRESETS_CD if args.cd else PRESETS

    # Validate preset_key
    preset_key_upper = args.preset_key.upper()
    if preset_key_upper not in presets:
        parser.error(
            f"Invalid preset '{args.preset_key}'. Available presets: {', '.join(presets.keys())}"
        )

    code = make_code(preset_key_upper, args.energy, presets)
    valid, key, actual_energy = verify_code(code, presets)

    print(f"\nGenerated code : {code}")
    print(f"Checksum valid : {valid}")
    print(f"Preset key     : {key} ({presets.get(key or '', 'Unknown')})")
    print(f"Energy         : {actual_energy}")

    if valid and key:
        levelNum = ord(key) - ord("A")
        var32_1144 = levelNum + 100
        if levelNum == 22:
            var32_1144 = 200

        if var32_1144 >= 100:
            var32_1144 -= 100

        match var32_1144:
            case 100:
                print("avt003.tot")
            case -1:
                print("sub_2279()")
            case 0:
                print("avt002.tot")
            case 1:
                print("var32_1488 = 3; avt007.tot")
            case 2:
                print("avt004.tot")
            case 3:
                print("avt00.tot")
            case 4:
                print("avt005.tot")
            case 5:
                print("var32_1488 = 1; avt001.tot")
            case 6:
                print("avt009.tot")
            case 7:
                print("avt006.tot")
            case 8:
                print("avt009.tot")
            case 9:
                print("avt008.tot")
            case 10:
                print("avt010.tot")
            case 11:
                print("avt011.tot")
            case 12:
                print("var32_1488 = 8; avt012.tot")
            case 13:
                print("var32_1488 = 8; avt014.tot")
            case 14:
                print("var32_1488 = 8; avt015.tot")
            case 15:
                print("var32_1488 = 8; avt016.tot")
            case 16:
                print("var32_1488 = 8; avt017.tot")
            case 17:
                print("var32_1488 = 8; avt018.tot")
            case 18:
                print("avt019.tot")
            case 19:
                print("avt020.tot")
            case 20:
                print("avt021.tot")
            case 21:
                print("avt022.tot")
            case 22:
                print("final.tot")
            case _:
                print("Unknown level")
