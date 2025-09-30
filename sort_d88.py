from struct import pack, unpack

f = open("Kyoto Touryuuden [Original-looking disk].d88", "rb")
# Skip header and total size
f.seek(0x20)
track_offsets_offset = f.tell()
starting_offset = unpack("<I", f.read(4))[0]
max_num_tracks = (starting_offset - track_offsets_offset) // 4
f.seek(-4, 1)
track_offsets = [unpack("<I", f.read(4))[0] for _ in range(max_num_tracks)]
sectors = {}
for i, offset in enumerate(track_offsets):
    if not offset:
        continue
    f.seek(offset)
    while f.tell() < track_offsets[i + 1]:
        c, h, s, l = unpack("<BBBB", f.read(4))
        len_data = 2 ** (7 + l)
        sectors[(c, h, s, l)] = (f.read(12), f.read(len_data))

l = list(sectors.keys())
l.sort()
with open("Kyoto Touryuuden [Original-looking disk]_sort.d88", "wb") as out:
    for k in l:
        out.write(pack("<BBBB", *k) + sectors[k][0] + sectors[k][1])
