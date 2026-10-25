# UEFI for umi

A port of [Project Silicium / Mu-Silicium](https://github.com/Project-Silicium/Mu-Silicium) to the Xiaomi Mi 10
(umi). The device is not upstream; the port follows `KonaPkg` (the SoC package for SM8250 / Snapdragon 865).

You do not need to rebuild the UEFI to run HackiOS -- a ready image is in `prebuilt/uefi`, and `mkxnuimg.py`
takes it by itself.

What is here:

- `BASE` -- the Mu-Silicium commit the port is made on;
- `mu-silicium.patch` -- changes to existing files:
  `BootShim/BootShim.S` (copies our "XNUP" container, which follows the UEFI image, to 0xF0000000),
  `BootManagerLib` (starts the XNU loader from the container instead of the boot menu);
- `files/` -- new files: `Platforms/Xiaomi/umiPkg` (memory map, driver list),
  `Silicium-ACPI/Platforms/Xiaomi/umi/AcpiTables.inf` (ACPI tables referencing `Kona/` AML files),
  `Silicon/.../BootManagerLib/XnuLoader.[ch]`, `Resources/Configs/umi.toml`, `Resources/DTBs/umi.dtb`
  (the device tree from the phone's `/sys/firmware/fdt`), `Binaries/umi` (UEFI drivers -- initially copied
  from redwood as a cross-SoC starting point; SoC-specific drivers from the umi XBL need replacement,
  see `files/Binaries/umi/README.md`).

## Building

Packages as in Mu-Silicium's `setup_env.sh` (on Arch: `git base-devel lld nasm clang llvm aarch64-linux-gnu-gcc
python python-pip python-virtualenv`).

```sh
uefi/apply.sh                                   # clones Mu-Silicium (with submodules, ~3 GB) and applies the port
python3 -m venv venv && venv/bin/pip install -r Mu-Silicium/pip-requirements.txt
cd Mu-Silicium
source ../venv/bin/activate
python3 build_uefi.py -d umi -r RELEASE          # -> Build/umiPkg/RELEASE_CLANGPDB/FV/SILICIUM_UEFI.fd
```

A pitfall: the `mu_nasm` dependency is installed through NuGet and needs Mono. To do without Mono, put the
system nasm in its place:

```sh
D=Mu_Basecore/BaseTools/Bin/mu_nasm_extdep
mkdir -p $D/Linux-x86-64
echo 'version: 20016.1.1' > $D/extdep_state.yaml
ln -sf /usr/bin/nasm    $D/Linux-x86-64/nasm
ln -sf /usr/bin/ndisasm $D/Linux-x86-64/ndisasm
```

After a build, `mkxnuimg.py` (called by `./xl enter` and `common/build.sh`) takes the UEFI from `Mu-Silicium/`,
and `tools/update-prebuilt.sh` refreshes `prebuilt/uefi`.

`uefi/export.sh` is the reverse: save the changes made in `Mu-Silicium/` back here.

## Device parameters (from umi.dtb)

| Parameter | Value | Source |
|---|---|---|
| SoC | SM8250 / Kona | KonaPkg.dsc.inc |
| GIC | 0x17A00000 / 0x17A60000 | DTB `arm,gic-v3` |
| Cores | 8 (1 prime + 3 gold + 4 silver) | DTB `cpu@` nodes |
| Core shift | 8 (MPIDR second affinity) | DTB `reg` |
| Display | 1080 x 2340, DSC | DTB panel node |
| Storage | UFS 3.0 | DTB `ufs@1d84000` |
| PSCI | SMC | DTB `psci` method |
| FD_BASE | 0x9FC00000 | Kona memory map |
| FD_SIZE | 0x300000 (3 MB) | Kona FV layout |
| PAYLOAD_BASE | 0xF0000000 | BootShim config |
| FB_BASE | 0x9C000000 | Display Reserved region |