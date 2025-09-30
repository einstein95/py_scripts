import struct
import sys

from PIL import Image

# cg00.pic (640x480)
# 50494300 0000 00000000 36040000 28000000 80020000 E0010000 01000800 00000000 00000000 00000000 00000000 00010000 00000000
# cg06.pic (644x480)
# 50494300 0000 00000000 E6030000 28000000 83020000 E0010000 01000800 00000000 80B70400 00000000 00000000 EC000000 00000000


fn = sys.argv[1]
f = open(fn, "rb")
assert f.read(4) == b"PIC\0", f"{fn}: Not a PIC file"
(
    version,
    palette_offset,
    data_offset,
    unknown1,
    width,
    height,
    unknown2,
    unknown3,
    unknown4,
    unknown5,
    unknown6,
    num_palette_entries,
    unknown7,
) = struct.unpack("<HIIIIIIIIIIII", f.read(0x32))
print(
    f"{fn},{palette_offset=},{data_offset=},{unknown1=},{width=},{height=},{unknown2=},{unknown3=},{unknown4=},{unknown5=},{num_palette_entries=},{unknown6=}"
)
# unknown1 = always 40?
# unknown2 = always 0x80001?
# unknown3 = always 0?
assert (
    num_palette_entries > 16
), f"{fn}: Number of palette entries must be greater than 16"
f.seek(palette_offset, 1)
palette = []
for i in range(num_palette_entries):
    b, g, r, a = struct.unpack("<BBBB", f.read(4))
    palette.extend([r, g, b])  # PIL expects RGB triplets

f.seek(data_offset)
data = f.read(width * height)
leftover = f.read()
if leftover:
    print(
        f"{fn}: Warning: {len(leftover)} bytes of leftover data after image data - {leftover.hex()}"
    )
img = Image.frombytes("P", (width, height), data)
img.putpalette(palette)
# Flip image vertically to match the original orientation
img = img.transpose(Image.FLIP_TOP_BOTTOM)  # type: ignore
img.save(fn.replace(".PIC", ".png"), "PNG")
