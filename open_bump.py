#!/usr/bin/env python

#
# Copyright (C) 2014  Anthony King
# Copyright (C) 2014  CyboLabs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import print_function

import binascii
import os
import struct
import sys

# Proof of Concept
POC = False


usage = """\
Usage: open_bump.py [-ha] "<image_file>" "<output_image>"
  image_file        - <required> path to the image file to bump
  output_image      - <optional> path to output the bumped file to (defaults to <image_file>_bumped.img
  -a/--apend image_file  - <required> if in append mode, the <image_file> is appended rather than <output_file> being generated\
"""

lg_magic = "41a9e467744d1d1ba429f2ecea655279"


def get_kernel_size(image_name):
    page_size = get_page_size(image_name)
    f_image = open(image_name, 'a+b')
    paged_kernel_size = get_size_from_kernel(f_image, page_size, 8)
    paged_ramdisk_size = get_size_from_kernel(f_image, page_size, 16)
    paged_second_size = get_size_from_kernel(f_image, page_size, 24)
    if paged_second_size <= 0:
        paged_second_size = 0
    paged_dt_size = get_size_from_kernel(f_image, page_size, 40)
    if paged_dt_size <= 0:
        paged_dt_size = 0
    f_image.close()
    return page_size + paged_kernel_size + paged_ramdisk_size + paged_second_size + paged_dt_size


def bumped(image_data):
    d = binascii.hexlify(image_data[-1024:])
    return d.endswith(lg_magic) or d.startswith(lg_magic)


def pair_reverse(s):
    n = len(s) / 2
    fmt = '%dh' % n
    return struct.pack(fmt, *reversed(struct.unpack(fmt, s)))


def get_page_size(image_name):
    with open(image_name, 'rb') as f_img:
        f_img.seek(36, 0)
        return int(pair_reverse(binascii.hexlify(f_img.read(4))), 16)


def get_size_from_kernel(f_image, page_size, seek_size):
    f_image.seek(seek_size, 0)
    return (int(pair_reverse(binascii.hexlify(f_image.read(4))), 16) / page_size) * page_size


def pad_image(image_name):
    page_size = get_page_size(image_name)
    image_size = os.path.getsize(image_name)
    num_pages = image_size / page_size

    calculated_size = get_kernel_size(image_name)

    f_image = open(image_name, 'a+b')

    if calculated_size > image_size:
        print("Invalid image: %s: calculated size greater than actual size" % image_name)
        f_image.close()
        sys.exit(1)
    if image_size > calculated_size:
        difference = image_size - calculated_size
        if difference not in [page_size, page_size*2]:
            if difference not in [1024, page_size + 1024, 2 * page_size + 1024, 
                                  16, page_size + 16, 2 * page_size + 16]:
                print("Image already padded. Attempting to remove padding...")
                print("Beware: this may invalidate your image.")
                i = num_pages - 1
                f_image.seek(0, 0)
                while i >= 0:
                    f_image.seek(page_size * i, 0)
                    data = f_image.read(page_size)
                    data = data.split('\x00')[0]
                    if not data:
                        f_image.truncate(page_size * i)
                        i -= 1
                    else:
                        break
            else:
                print("%s: Image already patched. Bailing out" % image_name)
                sys.exit(1)
    f_image.close()


def get_sha1(image_name):
    return hashlib.sha1(open(image_name, 'rb').read()).hexdigest()
    

def finish(out_image):
    print("bumped image: %s" % out_image)
    sys.exit(0)


def main(in_image, out_image):
    d_in_image = open(in_image, 'rb').read()
    open(out_image, 'wb').write(d_in_image)
    if bumped(d_in_image):
        print("Image already bumped")
        finish(out_image)
    pad_image(out_image)
    magic = binascii.unhexlify(lg_magic)
    with open(out_image, 'a+b') as f_out_image:
        f_out_image.write(magic)
    finish(out_image)


def cli():
    if len(sys.argv) < 2:
        print(usage)
        sys.exit(1)
    if sys.argv[1] in ["-h", "--help"]:
        print(usage)
        sys.exit(0)
    if sys.argv[1] in ["-a", "--append"]:
        if len(sys.argv) < 3:
            print(usage)
            sys.exit(1)
        image_name = out_image = sys.argv[2]
    else:
        image_name = sys.argv[1]
        if len(sys.argv) >= 3:
            out_image = sys.argv[2]
        else:
            out_split = os.path.splitext(image_name)
            out_image = out_split[0] + "_bumped" + out_split[1]
    if not os.path.isfile(image_name):
        print("file not found: %s" % image_name)
        sys.exit(1)
    main(image_name, out_image)


if __name__ == '__main__':
    cli()
