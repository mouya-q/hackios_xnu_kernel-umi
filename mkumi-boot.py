#!/usr/bin/env python3
"""
Pack the umi UEFI (with the XNU loader payload) into an Android boot image
formatted for Xiaomi Mi 10 (umi / SM8250 / Kona).

Mi 10 stock boot image format:
  - header_version = 2
  - page_size = 4096
  - base = 0x0
  - kernel_addr = 0x00008000
  - ramdisk_addr = 0x01000000
  - tags_addr = 0x00000100
  - dtb_addr = 0x01f00000
  - DTB as separate section (v2 requirement)
  - Kernel = gzip(BootShim + UEFI_FD + XNUP_payload)

The BootShim copies the FD to FD_BASE and the payload to PAYLOAD_BASE.
"""
import argparse, gzip, os, struct, subprocess, sys
from hashlib import sha1

HERE = os.path.dirname(os.path.abspath(__file__))
PREBUILT = os.path.join(HERE, 'prebuilt', 'uefi')

# Mi 10 stock boot image parameters (extracted from device)
PAGE_SIZE = 4096
HEADER_VERSION = 2
BASE = 0x0
KERNEL_OFFSET = 0x00008000
RAMDISK_OFFSET = 0x01000000
SECOND_OFFSET = 0x00f00000
TAGS_OFFSET = 0x00000100
DTB_OFFSET = 0x01f00000
OS_VERSION = 0x1a  # Android 10 (Q), matching stock
OS_PATCH_LEVEL = 0x183  # August 2020, matching stock

# Boot image header constants (from AOSP bootimg.h)
BOOT_MAGIC = b'ANDROID!'
BOOT_MAGIC_SIZE = 8
BOOT_NAME_SIZE = 16
BOOT_ARGS_SIZE = 512
BOOT_EXTRA_ARGS_SIZE = 1024
BOOT_IMAGE_HEADER_V2_SIZE = 1660

def env_int(name, default):
    v = os.environ.get(name, '')
    return int(v, 0) if v else default

FD_BASE = env_int('FD_BASE', 0x9FC00000)
FD_SIZE = env_int('FD_SIZE', 0x300000)
PAYLOAD_BASE = env_int('PAYLOAD_BASE', 0xF0000000)

def pad_file(data, page_size):
    """Pad data to page_size boundary."""
    pad = (page_size - (len(data) % page_size)) % page_size
    return data + b'\x00' * pad

def build_boot_image(shim_path, fd_path, dtb_path, payload_path, ramdisk_path, output_path, no_gzip=False):
    """Build a v2 Android boot image matching Mi 10 stock format."""

    # Read components
    shim = open(shim_path, 'rb').read()
    fd = open(fd_path, 'rb').read()
    assert len(fd) == FD_SIZE, f'FD size mismatch: {len(fd)} != {FD_SIZE:#x}'

    # Build kernel blob: BootShim + UEFI_FD + optional XNUP payload
    blob = shim + fd
    if payload_path:
        payload = open(payload_path, 'rb').read()
        assert payload[:4] == b'XNUP', 'Payload must be XNUP container'
        assert len(payload) <= 0x04000000 - 0x1000, 'Payload too large'
        blob += payload
        blob += b'\x00' * (-len(blob) % 16)  # Align to 16 bytes
        print(f'payload: {len(payload)} bytes')

    # Gzip compress the kernel blob (NO DTB appended - DTB is separate in v2)
    if no_gzip:
        kernel_data = blob
        print(f'kernel (uncompressed): {len(kernel_data)} bytes')
    else:
        kernel_data = gzip.compress(blob, 6)
        print(f'kernel (gzip): {len(kernel_data)} bytes (uncompressed: {len(blob)})')

    # Read ramdisk and DTB
    ramdisk_data = open(ramdisk_path, 'rb').read() if ramdisk_path else b''
    dtb_data = open(dtb_path, 'rb').read() if dtb_path else b''
    assert len(dtb_data) > 0, 'DTB must not be empty for v2 header'

    # Calculate SHA1 for image ID
    sha = sha1()
    sha.update(kernel_data)
    sha.update(struct.pack('I', len(kernel_data)))
    sha.update(ramdisk_data)
    sha.update(struct.pack('I', len(ramdisk_data)))
    sha.update(b'')  # second bootloader (empty)
    sha.update(struct.pack('I', 0))
    # recovery_dtbo (empty for v2)
    sha.update(struct.pack('I', 0))
    # dtb
    sha.update(dtb_data)
    sha.update(struct.pack('I', len(dtb_data)))
    img_id = sha.digest()

    # Build header
    header = bytearray()
    # Magic
    header += BOOT_MAGIC
    # kernel_size
    header += struct.pack('I', len(kernel_data))
    # kernel_addr = base + kernel_offset
    header += struct.pack('I', BASE + KERNEL_OFFSET)
    # ramdisk_size
    header += struct.pack('I', len(ramdisk_data))
    # ramdisk_addr = base + ramdisk_offset
    header += struct.pack('I', BASE + RAMDISK_OFFSET if len(ramdisk_data) > 0 else 0)
    # second_size
    header += struct.pack('I', 0)
    # second_addr
    header += struct.pack('I', 0)
    # tags_addr = base + tags_offset
    header += struct.pack('I', BASE + TAGS_OFFSET)
    # page_size
    header += struct.pack('I', PAGE_SIZE)
    # header_version
    header += struct.pack('I', HEADER_VERSION)
    # os_version and patch level
    header += struct.pack('I', (OS_VERSION << 11) | OS_PATCH_LEVEL)
    # name (board name, 16 bytes)
    header += b'\x00' * BOOT_NAME_SIZE
    # cmdline (512 bytes)
    cmdline = b'console=ttyMSM0,115200n8 androidboot.hardware=qcom'
    header += cmdline + b'\x00' * (BOOT_ARGS_SIZE - len(cmdline))
    # id (32 bytes = sha1 hash)
    header += img_id + b'\x00' * (32 - len(img_id))
    # extra_cmdline (1024 bytes)
    header += b'\x00' * BOOT_EXTRA_ARGS_SIZE

    # v1+ fields: recovery_dtbo_size (4) + recovery_dtbo_offset (8)
    header += struct.pack('I', 0)  # recovery_dtbo_size
    header += struct.pack('Q', 0)  # recovery_dtbo_offset

    # v2: header_size
    header += struct.pack('I', BOOT_IMAGE_HEADER_V2_SIZE)

    # v2: dtb_size (4) + dtb_addr (8)
    header += struct.pack('I', len(dtb_data))
    header += struct.pack('Q', BASE + DTB_OFFSET)

    assert len(header) == BOOT_IMAGE_HEADER_V2_SIZE, f'Header size: {len(header)} != {BOOT_IMAGE_HEADER_V2_SIZE}'

    # Pad header to page_size
    header = bytes(header) + b'\x00' * (PAGE_SIZE - len(header))

    # Assemble boot image: header | kernel | ramdisk | dtb (each page-aligned)
    image = bytearray()
    image += header
    image += kernel_data + b'\x00' * ((PAGE_SIZE - len(kernel_data) % PAGE_SIZE) % PAGE_SIZE)
    image += ramdisk_data + b'\x00' * ((PAGE_SIZE - len(ramdisk_data) % PAGE_SIZE) % PAGE_SIZE)
    # recovery_dtbo section (empty, but needs a page for v1+)
    # Actually for v2 with recovery_dtbo_size=0, no data is written
    # dtb section
    image += dtb_data + b'\x00' * ((PAGE_SIZE - len(dtb_data) % PAGE_SIZE) % PAGE_SIZE)

    with open(output_path, 'wb') as f:
        f.write(image)

    print(f'{output_path}: {len(image)} bytes')
    print(f'  header: {len(header)} bytes (v{HEADER_VERSION}, page={PAGE_SIZE})')
    print(f'  kernel: {len(kernel_data)} bytes (uncompressed {len(blob)})')
    print(f'  ramdisk: {len(ramdisk_data)} bytes')
    print(f'  dtb: {len(dtb_data)} bytes')
    print(f'  kernel_addr: {BASE + KERNEL_OFFSET:#010x}')
    print(f'  ramdisk_addr: {BASE + RAMDISK_OFFSET:#010x}')
    print(f'  tags_addr: {BASE + TAGS_OFFSET:#010x}')
    print(f'  dtb_addr: {BASE + DTB_OFFSET:#010x}')

    return image

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-p', '--payload', help='XNUP payload file (USB loader)')
    ap.add_argument('-o', '--output', default='out/umi-boot.img')
    ap.add_argument('--shim', default=os.path.join(PREBUILT, 'BootShim.bin'))
    ap.add_argument('--fd', default=os.environ.get('UEFI_FD', os.path.join(PREBUILT, 'SILICIUM_UEFI.fd')))
    ap.add_argument('--dtb', default=os.environ.get('DTB', os.path.join(HERE, 'uefi/files/Resources/DTBs/umi.dtb')))
    ap.add_argument('--ramdisk', default=os.path.join(PREBUILT, 'ramdisk'))
    ap.add_argument('--no-gzip', action='store_true', help='Do not gzip-compress kernel (uncompressed ARM64 Image)')
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    build_boot_image(args.shim, args.fd, args.dtb, args.payload, args.ramdisk, args.output, args.no_gzip)

if __name__ == '__main__':
    main()