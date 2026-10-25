/*
 * umi: Xiaomi Mi 10 / SM8250 / Kona.
 * Paste into xnuloader/loader.c next to platform_redwood and add &platform_umi to platforms[].
 * Every value is explained in docs/PORTING.md ("The loader").
 */
static const struct platform platform_umi = {
	/* io_base must be non-zero: XNU treats a zero SoC base as "no SoC" and skips clock setup. */
	.name = "umi", .io_base = 0x00100000, .io_size = 0x3FF00000,
	.gic_dist = 0x17A00000, .gic_redist = 0x17A60000, .uart = 0, .log_other_cpu = 1,
	.cores = 8, .core_shift = 8,
	/* Kona: 1 prime (0x000) + 3 gold (0x100,0x200,0x300) + 4 silver (0x400..0x700).
	 * Silver cluster = capacity-dmips-mhz lowest; bits 4-7. */
	.small_cores = 0xF0,
	/* The framebuffer base the UEFI GOP reports. Display Reserved = 0x9C000000 in Kona memmap. */
	.fb_base = 0x9C000000,
};