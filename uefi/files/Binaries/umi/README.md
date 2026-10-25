## Firmware Infos

- **Device:** Xiaomi Mi 10 (umi)
- **SoC:** Qualcomm Snapdragon 865 (SM8250 / Kona)
- **Region:** China
- **Version:** MIUI based on LAHAINA bootloader

## Notes

- **Initial Binaries:** Copied from redwood (SM7325) as a starting point.
  Many Qualcomm DXE drivers are cross-SoC compatible.
- **SoC-specific drivers requiring replacement from umi XBL:**
  - DisplayDxe (panel: j2_mp_42_02_0b_dsc_cmd, 1080x2340)
  - UFSDxe (UFS 3.0 controller @ 0x1d84000)
  - ChipInfoDxe (SM8250 / Kona)
  - ClockDxe (Kona clock tree)
  - DDRInfoDxe (LPDDR5)
  - PlatformInfoDxe
  - ProjectInfoDxe
- **Extraction method:** UEFIReader required (XBL uses Qualcomm custom FV format).
  XBL source: xbl_umi.img (7,340,032 bytes, ELF/AArch64).
  FV at offset 0x828E0, vaddr=0x9FC00000, size=0x270000.

## Patches/Fixes (inherited from redwood, may need re-evaluation)

### ButtonsDxe:
- **Patch:** Qcom Key Code 0x102 changed to Enter (0xD).

### DALSYSDxe:
- **Patch:** Cache Coherence for UFS enabled.

### TzDxeLA:
- **Patch:** Global TZ Applet Variable changed to TRUE.

### UsbConfigDxe:
- **Patch:** USB Deinit removed from Exit Boot Services.

### UsbMsdDxe:
- **Patch:** Removable State changed to Non-Removable.
