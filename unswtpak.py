import datetime
import os
import struct
import sys


def dos_to_unix_time(dos_date, dos_time):
    """
    Convert MS-DOS date and time to Unix timestamp.

    Args:
        dos_date: MS-DOS date (16-bit value)
        dos_time: MS-DOS time (16-bit value)

    Returns:
        Unix timestamp (seconds since 1970-01-01 00:00:00 UTC)
    """
    day = dos_date & 0x1F
    month = (dos_date >> 5) & 0x0F
    year = ((dos_date >> 9) & 0x7F) + 1980

    seconds = (dos_time & 0x1F) * 2
    minutes = (dos_time >> 5) & 0x3F
    hours = (dos_time >> 11) & 0x1F

    dt = datetime.datetime(
        year, month, day, hours, minutes, seconds, tzinfo=datetime.timezone.utc
    )

    unix_timestamp = dt.timestamp()

    return int(unix_timestamp)


class SWTHead:
    def __init__(self, data):
        self.signature = data[:40].decode("ascii", errors="ignore")
        self.disksize = struct.unpack("<I", data[40:44])[0]


class DOSFind:
    def __init__(self, data):
        self.reserved = data[:21]
        self.dos_attr = data[21]
        self.dos_time, self.dos_date = struct.unpack("<HH", data[22:26])
        self.filesize = struct.unpack("<I", data[26:30])[0]
        self.filename = data[30:43].split(b"\x00")[0].decode("ascii")


class SWTItem:
    def __init__(self, data):
        self.dirlevel = struct.unpack("<h", data[:2])[0]
        self.fileinfo = DOSFind(data[2:45])
        self.padding = data[45]


def main():
    print("SelectWare Technologies demo file extractor\n")
    if len(sys.argv) != 3:
        print("Usage: unswtpak <filename.swt> <directory>\n")
        return 1

    try:
        with open(sys.argv[1], "rb") as fl:
            sh_data = fl.read(44)
            sh = SWTHead(sh_data)

            # TODO: check minimum free disk space before extracting
            dold = 0
            path = sys.argv[2]
            os.makedirs(path, exist_ok=True)

            while True:
                si_data = fl.read(46)
                if len(si_data) < 46:
                    break
                si = SWTItem(si_data)

                # No more records
                if not si.fileinfo.filename:
                    break

                # Going up
                while si.dirlevel <= dold:
                    # In this level can go up only for directory (will replace current)
                    if si.dirlevel == dold and not (si.fileinfo.dos_attr & 0x10):
                        break
                    # Cut last directory
                    path = os.path.dirname(path)
                    dold -= 1

                # Update current location
                dold = si.dirlevel

                # It's a directory
                if si.fileinfo.dos_attr & 0x10:
                    # Going down
                    path = os.path.join(path, si.fileinfo.filename)
                    os.makedirs(path, exist_ok=True)
                else:
                    # It's a file
                    try:
                        file_data = fl.read(si.fileinfo.filesize)
                        # Build path
                        file_path = os.path.join(path, si.fileinfo.filename)
                        print(file_path, end=": ")
                        print(f"{si.fileinfo.dos_attr:08b}")
                        timestamp = dos_to_unix_time(
                            si.fileinfo.dos_date, si.fileinfo.dos_time
                        )
                        # Dump file to disk
                        with open(file_path, "wb") as f:
                            f.write(file_data)
                        # TODO: set file date, time, and attributes
                        # Set file modification time
                        os.utime(file_path, (timestamp, timestamp))
                        # Convert DOS attributes to Unix permissions
                        # if si.fileinfo.dos_attr & 0x01:  # Read-only
                        #     si.fileinfo.dos_attr &= ~0x02  # Clear hidden attribute
                        # if si.fileinfo.dos_attr & 0x02:  # Hidden
                        #     si.fileinfo.dos_attr &= ~0x01  # Clear read-only attribute
                        # if si.fileinfo.dos_attr & 0x04:  # System
                        #     si.fileinfo.dos_attr &= ~0x08  # Clear archive attribute
                        # if si.fileinfo.dos_attr & 0x08:  # Archive
                        #     si.fileinfo.dos_attr &= ~0x04  # Clear system attribute
                        # Set file permissions
                        if os.name == "nt":
                            # On Windows, use the DOS attributes directly
                            os.chmod(file_path, si.fileinfo.dos_attr & 0xFF)
                        else:
                            # On Unix-like systems, convert DOS attributes to permissions
                            permissions = 0o644
                            if si.fileinfo.dos_attr & 0x01:  # Read-only
                                permissions = 0o444
                            elif si.fileinfo.dos_attr & 0x02:  # Hidden
                                permissions = 0o600
                            elif si.fileinfo.dos_attr & 0x04:  # System
                                permissions = 0o400
                            elif si.fileinfo.dos_attr & 0x08:  # Archive
                                permissions = 0o644
                            os.chmod(file_path, permissions)
                    except MemoryError:
                        # Not enough memory - skip file
                        fl.seek(si.fileinfo.filesize, os.SEEK_CUR)
                        print("Error: not enough memory for output file.")
    except FileNotFoundError:
        print("Error: can't open input file.\n")
        return 2

    print("\ndone\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
