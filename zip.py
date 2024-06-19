#!/usr/bin/env python3

import io
import struct
import zipfile
import requests
import chardet
import argparse

EOCD_RECORD_SIZE = 22
ZIP64_EOCD_RECORD_SIZE = 56
ZIP64_EOCD_LOCATOR_SIZE = 20

MAX_STANDARD_ZIP_SIZE = 4_294_967_295

def main(args):
    zip_file = get_zip_file(args.url)
    print_zip_content(zip_file)

def get_zip_file(url):
    file_size = get_file_size(url)
    eocd_record = fetch(url, file_size - EOCD_RECORD_SIZE, EOCD_RECORD_SIZE)
    if file_size <= MAX_STANDARD_ZIP_SIZE:
        cd_start, cd_size = get_central_directory_metadata_from_eocd(eocd_record)
    else:
        zip64_eocd_record = fetch(url, file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE + ZIP64_EOCD_RECORD_SIZE), ZIP64_EOCD_RECORD_SIZE)
        zip64_eocd_locator = fetch(url, file_size - (EOCD_RECORD_SIZE + ZIP64_EOCD_LOCATOR_SIZE), ZIP64_EOCD_LOCATOR_SIZE)
        cd_start, cd_size = get_central_directory_metadata_from_eocd64(zip64_eocd_record)
        eocd_record = zip64_eocd_record + zip64_eocd_locator + eocd_record
    central_directory = fetch(url, cd_start, cd_size)
    return zipfile.ZipFile(io.BytesIO(central_directory + eocd_record))

def get_file_size(url):
    return int(requests.head(url).headers.get('content-length'))

def fetch(url, start, length):
    headers = {'Range': f'bytes={start}-{start + length - 1}'}
    return requests.get(url, headers=headers).content

def get_central_directory_metadata_from_eocd(eocd):
    return parse_little_endian_to_int(eocd[16:20]), parse_little_endian_to_int(eocd[12:16])

def get_central_directory_metadata_from_eocd64(eocd64):
    return parse_little_endian_to_int(eocd64[48:56]), parse_little_endian_to_int(eocd64[40:48])

def parse_little_endian_to_int(little_endian_bytes):
    return struct.unpack("<i" if len(little_endian_bytes) == 4 else "<q", little_endian_bytes)[0]

def print_zip_content(zip_file):
    """
    try:
        encodings = [chardet.detect(zi.filename.encode('cp437'))['encoding'] for zi in zip_file.filelist]
        encoding = max(set(encodings), key=encodings.count)
        if not encoding or encoding.startswith('Windows-12') or encoding == 'SHIFT_JIS':
            encoding = 'cp932'
    except UnicodeEncodeError:
        encoding = 'utf-8'
    print(f'Detected encoding: {encoding}')
    for zi in zip_file.filelist:
        try:
            print(zi.filename.encode('cp437').decode(encoding))
        except (UnicodeEncodeError, UnicodeDecodeError):
            print(zi.filename)
    """
    tmp_l = b'\n'.join([i.filename.encode('cp437') for i in zip_file.filelist])
    encoding = chardet.detect(tmp_l)['encoding']
    print(f'Detected encoding: {encoding}')
    if not encoding:
        encoding = 'cp932'
    # print(chardet.detect_all(tmp_l))
    # print(repr(tmp_l))
    for zi in zip_file.filelist:
        print(zi.filename.encode('cp437').decode(encoding))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', help='URL of the zip file')
    args = parser.parse_args()
    main(args)
