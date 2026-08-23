import json
import sys


def reformat(path):
    with open(path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        output = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    else:
        lines = [
            json.dumps(item, separators=(",", ":"), ensure_ascii=False) for item in data
        ]
        output = "[\n" + ",\n".join(lines) + "\n]"

    with open(path, "w") as f:
        f.write(output)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reformat_json.py <path_to_json>", file=sys.stderr)
        sys.exit(1)
    reformat(sys.argv[1])
