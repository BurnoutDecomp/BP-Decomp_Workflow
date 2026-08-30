"""Minimal Xenos (Xbox 360 GPU) shader-microcode disassembler.

Encoding per Xenia's xe/gpu/ucode.h (ControlFlowInstruction / AluInstruction /
TextureFetchInstruction).  Everything is decoded from big-endian dwords because
the guest image and the bundle physical blocks are stored big-endian.

Usage: python xenos.py <ucode.bin> <const_bytes> <stream_bytes> [const_base] [abs]
       (ucode.bin = the [literal float4 block][instruction stream] region of a
        shader package; the split is given by the two dwords the package
        header's +0x18 field points at: (constant_block_bytes,
        instruction_stream_bytes) -- their sum is the +0x08 size.  const_base
        defaults to 252: the literal block maps to c252..c255, pinned by the
        0x??FC0010 word in the package header.  Pass "abs" as the 5th arg to
        print the alternative absolute swizzle reading for A/B comparison.)

VALIDATED AGAINST GROUND TRUTH (2026-08-14, post-fx step 2).  SHADERS.BNDL
(X360 retail) and tools/assets/shaders/out/SHADERS_PC.BNDL contain the same
shaders -- one as Xenos microcode, one as fxc-compiled D3D9 bytecode -- under
identical resource ids.  Both sides of resource CC3B3312 were extracted with
build/tools/yap/YAP.exe, the X360 side disassembled with this tool and the PC
side with `fxc /dumpbin`, and they align instruction for instruction (including
the literal-block constant c255.x == 1.0f matching the PC's `def c5, 1, ...`).
That bundle pair is a general oracle for decoding ANY Xenos shader in this
project: pick a resource id present in both, and the PC bytecode is the answer
key.  Three encoding facts were pinned by that proof:

  * the ALU source swizzle byte is RELATIVE to the component index:
      component[i] = (((swz >> 2i) & 3) + i) & 3
    (so 0x00 = xyzw and 0x6C/0xB1/0xC6/0x1B are the four broadcasts; an
    absolute reading turns those into nonsense rotations);
  * the scalar unit reads src3 with its own component selection --
    1-component ops take ((swz >> 6) + 3) & 3, 2-component ops take that plus
    (swz + 0) & 3;
  * the microcode block layout is [64-byte literal float4 block][instruction
    stream], the literals mapping to c252..c255.

Companion: ctab.py reads the big-endian CTAB out of the same packages, giving
the register-pinned uniform names for whatever this tool disassembles.
Full worked example: the post-fx composite decode in
scratch/postfx_step2_out/shader/REPORT.md (permutation 0, all 12 CTABs).

THREE MORE DECODE FACTS (2026-08-30, found by the road-shader RE wave, which
had to hand-decode raw words to get around their absence -- see
scratch/x360_road_shaders/SUMMARY.md "Tooling debt"):

  * fetch-family instructions are NOT all tfetch: the opcode is w0 & 0x1F
    (0=vfetch, 1=tfetch, 16=getBCF, 17=getCompTexLOD, 18=getGradients,
    19=getWeights, per Xenia's FetchOpcode).  Texture fetches also carry
    signed 5-bit HALF-texel offsets in w2 bits 16-20 (x) / 21-25 (y) -- the
    road shadow filters' manual bilinear PCF is four point taps at
    (+-0.5, +-0.5) texels, invisible without them.
  * on an ALU instruction with export_data set, the SCALAR half writes the
    export named by vector_dest (fxc leaves scalar_dest at 0), and
    scalar_dest_rel selects a 0.0/1.0 constant for channels present in BOTH
    write masks.
  * the mulsc0/1, addsc0/1, subsc0/1 scalar ops read a constant AND a GPR:
    const index = src_reg[2] (src_sel[2] is a register bit here, not
    reg-vs-const), const component = ((swz>>6)+3)&3, gpr index =
    ((swz>>2)&0xF)<<2 | src_sel[2]<<1 | (opcode&1), gpr component = swz&3,
    and the src3 negate bit flips subsc operand order (set => gpr - const).
    Pinned empirically over the six road shaders' 80+ call sites (register
    families r0/r1/r2/r3 plus a bits[2:5] case resolving to r5.w = the NdotL
    interpolant), all agreeing with dataflow.
"""
import struct
import sys

CF_OPCODE = {
    0: "nop", 1: "exec", 2: "exec_end", 3: "cond_exec", 4: "cond_exec_end",
    5: "cond_exec_pred", 6: "cond_exec_pred_end", 7: "loop_start",
    8: "loop_end", 9: "cond_call", 10: "return", 11: "cond_jmp", 12: "alloc",
    13: "cond_exec_pred_clean", 14: "cond_exec_pred_clean_end",
    15: "mark_vs_fetch_done",
}

VOP = {
    0: "add", 1: "mul", 2: "max", 3: "min", 4: "seq", 5: "sgt", 6: "sge",
    7: "sne", 8: "frc", 9: "trunc", 10: "floor", 11: "mad", 12: "cndeq",
    13: "cndge", 14: "cndgt", 15: "dp4", 16: "dp3", 17: "dp2add", 18: "cube",
    19: "max4", 20: "setp_eq_push", 21: "setp_ne_push", 22: "setp_gt_push",
    23: "setp_ge_push", 24: "kill_eq", 25: "kill_gt", 26: "kill_ge",
    27: "kill_ne", 28: "dst", 29: "maxa",
}

SOP = {
    0: "adds", 1: "adds_prev", 2: "muls", 3: "muls_prev", 4: "muls_prev2",
    5: "maxs", 6: "mins", 7: "seqs", 8: "sgts", 9: "sges", 10: "snes",
    11: "frcs", 12: "truncs", 13: "floors", 14: "exp", 15: "logc", 16: "log",
    17: "rcpc", 18: "rcpf", 19: "rcp", 20: "rsqc", 21: "rsqf", 22: "rsq",
    23: "maxas", 24: "maxasf", 25: "subs", 26: "subs_prev", 27: "setp_eq",
    28: "setp_ne", 29: "setp_gt", 30: "setp_ge", 31: "setp_inv",
    32: "setp_pop", 33: "setp_clr", 34: "setp_rstr", 35: "kills_eq",
    36: "kills_gt", 37: "kills_ge", 38: "kills_ne", 39: "kills_one",
    40: "sqrt", 42: "mulsc0", 43: "mulsc1", 44: "addsc0", 45: "addsc1",
    46: "subsc0", 47: "subsc1", 48: "sin", 49: "cos", 50: "retain_prev",
}

CH = "xyzw"


def be(b, o):
    return struct.unpack_from(">I", b, o)[0]


def mask_str(m):
    return "".join(CH[i] if (m >> i) & 1 else "_" for i in range(4))


def swz(byte, n=4):
    """ALU source swizzle: 2 bits/component, RELATIVE to the component index."""
    out = ""
    for i in range(n):
        out += CH[(((byte >> (2 * i)) & 3) + i) & 3]
    return out


def swz_abs(byte, n=4):
    """Alternative reading kept for the A/B comparison: absolute 2-bit select."""
    return "".join(CH[(byte >> (2 * i)) & 3] for i in range(n))


def fetch_dst_swz(v):
    o = ""
    for i in range(4):
        c = (v >> (3 * i)) & 7
        o += {0: "x", 1: "y", 2: "z", 3: "w", 4: "0", 5: "1", 6: "?",
              7: "_"}[c]
    return o


class Alu(object):
    def __init__(self, w0, w1, w2):
        self.w0, self.w1, self.w2 = w0, w1, w2
        self.vector_dest = w0 & 0x3F
        self.vector_dest_rel = (w0 >> 6) & 1
        self.abs_constants = (w0 >> 7) & 1
        self.scalar_dest = (w0 >> 8) & 0x3F
        self.scalar_dest_rel = (w0 >> 14) & 1
        self.export_data = (w0 >> 15) & 1
        self.vector_write_mask = (w0 >> 16) & 0xF
        self.scalar_write_mask = (w0 >> 20) & 0xF
        self.vector_clamp = (w0 >> 24) & 1
        self.scalar_clamp = (w0 >> 25) & 1
        self.scalar_opc = (w0 >> 26) & 0x3F
        self.src_swiz = [(w1 >> 16) & 0xFF, (w1 >> 8) & 0xFF, w1 & 0xFF]
        self.src_neg = [(w1 >> 26) & 1, (w1 >> 25) & 1, (w1 >> 24) & 1]
        self.pred_condition = (w1 >> 27) & 1
        self.is_predicated = (w1 >> 28) & 1
        self.src_reg = [(w2 >> 16) & 0xFF, (w2 >> 8) & 0xFF, w2 & 0xFF]
        self.vector_opc = (w2 >> 24) & 0x1F
        self.src_sel = [(w2 >> 31) & 1, (w2 >> 30) & 1, (w2 >> 29) & 1]

    def operand(self, i, n=4, absolute=False):
        reg, sel, s = self.src_reg[i], self.src_sel[i], self.src_swiz[i]
        neg = "-" if self.src_neg[i] else ""
        f = swz_abs if absolute else swz
        name = ("r%d" % (reg & 0x3F)) if sel else ("c%d" % reg)
        flag = "'" if (sel and (reg & 0x80)) else ""
        return "%s%s%s.%s" % (neg, name, flag, f(s, n))

    # The scalar unit reads src3 with its own component selection:
    #   1 component : a = ((swz >> 6) + 3) & 3
    #   2 components: a = ((swz >> 6) + 3) & 3, b = (swz + 0) & 3
    def scalar_operand(self, ncomp):
        reg, sel, s = self.src_reg[2], self.src_sel[2], self.src_swiz[2]
        neg = "-" if self.src_neg[2] else ""
        name = ("r%d" % (reg & 0x3F)) if sel else ("c%d" % reg)
        flag = "'" if (sel and (reg & 0x80)) else ""
        comps = CH[((s >> 6) + 3) & 3]
        if ncomp == 2:
            comps += CH[s & 3]
        return "%s%s%s.%s" % (neg, name, flag, comps)

    # The "…sc0/sc1" scalar ops (42-47: mulsc0/1, addsc0/1, subsc0/1) read TWO
    # operands: a CONSTANT and a GPR.  Until 2026-08-30 this tool printed only
    # the constant (and mislabelled it rN when src_sel was set), silently
    # dropping the register operand from every listing this project ever made.
    # Encoding, pinned empirically across the six road shaders' 80+ call sites
    # (every case with a dataflow-known register agrees, including the
    # four-family split r0/r1/r2/r3 and a bits[2:5] case resolving to r5.w =
    # the NdotL interpolant of Tunnel_Lightmapped_Road..2's PS slot 55):
    #   const index     = src_reg[2] (full 8 bits; src_sel[2] does NOT make it
    #                     a GPR here -- it is a register-index bit instead)
    #   const component = ((swz >> 6) + 3) & 3      (the standard scalar rule)
    #   gpr index       = ((swz >> 2) & 0xF) << 2 | src_sel[2] << 1 | (opcode & 1)
    #   gpr component   = swz & 3
    #   subsc order     = src3 negate set => gpr - const ; clear => const - gpr
    def scalar_const_op_operands(self):
        s = self.src_swiz[2]
        const = "c%d.%s" % (self.src_reg[2], CH[((s >> 6) + 3) & 3])
        gpr_index = (((s >> 2) & 0xF) << 2) | (self.src_sel[2] << 1) \
            | (self.scalar_opc & 1)
        gpr = "r%d.%s" % (gpr_index, CH[s & 3])
        return const, gpr

    def text(self, absolute=False):
        out = []
        if self.vector_write_mask or self.export_data:
            vo = VOP.get(self.vector_opc, "vop%d" % self.vector_opc)
            n = {"dp2add": 2, "dp3": 3, "dp4": 4}.get(vo, 4)
            srcs = [self.operand(0, 4, absolute), self.operand(1, 4, absolute)]
            if vo in ("mad", "cndeq", "cndge", "cndgt", "dp2add"):
                srcs.append(self.operand(2, 4, absolute))
            dst = ("export%d" % self.vector_dest if self.export_data
                   else "r%d" % self.vector_dest)
            out.append("%-7s %s.%s, %s%s" % (
                vo, dst, mask_str(self.vector_write_mask), ", ".join(srcs),
                " [clamp]" if self.vector_clamp else ""))
        if self.scalar_opc != 50 or self.scalar_write_mask:
            so = SOP.get(self.scalar_opc, "sop%d" % self.scalar_opc)
            # ⚠ ON AN EXPORT INSTRUCTION THE SCALAR HALF WRITES THE VECTOR
            # DESTINATION.  fxc leaves scalar_dest at 0 for exports, so until
            # 2026-08-30 this printed "export0" for every scalar export write --
            # the road-shader VS listings showed three different values landing
            # in export0.w while the interpolator channels they really fed
            # (export1.z line-U, export3.w eyeZ, export5.w fog) looked
            # unwritten.  scalar_dest_rel is repurposed on exports: channels in
            # BOTH write masks receive a constant selected by it (0.0 or 1.0)
            # rather than either unit's result.
            if self.export_data:
                dst = "export%d" % self.vector_dest
            else:
                dst = "r%d" % self.scalar_dest
            two = so in ("adds", "muls", "maxs", "mins", "subs", "seqs",
                         "sgts", "sges", "snes", "setp_eq", "setp_ne",
                         "setp_gt", "setp_ge")
            # ⚠ THE SCALAR CLAMP MUST BE PRINTED TOO.  w0 bit 25 is the SCALAR unit's
            # saturate; bit 24 is the vector unit's.  Until 2026-08-23 this method
            # printed "[clamp]" for the vector half ONLY, so every scalar saturate in
            # every package this project has ever disassembled was INVISIBLE -- and one
            # of them was dropped from an authored PC shader as a result (the sun-flare
            # falloff, brn_suncorona.fx instruction 5, w0=0xBA200000).  A listing that
            # silently omits a semantic bit is worse than no listing.
            clamp = " [clamp]" if self.scalar_clamp else ""
            if 42 <= self.scalar_opc <= 47:
                const, gpr = self.scalar_const_op_operands()
                if so.startswith("subsc"):
                    ops = ("%s - %s" % (gpr, const)) if self.src_neg[2] \
                        else ("%s - %s" % (const, gpr))
                else:
                    neg = "-" if self.src_neg[2] else ""
                    op = "*" if so.startswith("mulsc") else "+"
                    ops = "%s%s %s %s" % (neg, const, op, gpr)
                note = "" if self.scalar_write_mask else "   (no write: sets PS only)"
                out.append("%-9s %s.%s, %s%s%s" % (
                    so, dst, mask_str(self.scalar_write_mask), ops, clamp, note))
            elif so == "retain_prev":
                out.append("%-7s %s.%s   [= PS]%s" % (so, dst,
                                                      mask_str(self.scalar_write_mask),
                                                      clamp))
            else:
                note = "" if self.scalar_write_mask else "   (no write: sets PS only)"
                out.append("%-9s %s.%s, %s%s%s" % (
                    so, dst, mask_str(self.scalar_write_mask),
                    self.scalar_operand(2 if two else 1), clamp, note))
        if self.export_data and (self.vector_write_mask & self.scalar_write_mask):
            out.append("   (export overlap %s = const %.1f, per scalar_dest_rel)"
                       % (mask_str(self.vector_write_mask & self.scalar_write_mask),
                          1.0 if self.scalar_dest_rel else 0.0))
        if self.is_predicated:
            out.append("   (predicated, cond=%d)" % self.pred_condition)
        return out


# Fetch-family opcodes (w0 & 0x1F), per Xenia's xe/gpu/ucode.h FetchOpcode.
# Until 2026-08-30 this tool printed EVERY fetch-family instruction as "tfetch",
# which made the X360 road shaders' shadow filters unreadable (their
# getGradients/getWeights ops looked like extra texture samples) -- the whole
# road-shader RE wave had to re-decode the raw words by hand.
FETCH_OP = {
    0: "vfetch", 1: "tfetch", 16: "getBCF", 17: "getCompTexLOD",
    18: "getGradients", 19: "getWeights",
}


def _signed5(v):
    return v - 32 if v >= 16 else v


class Fetch(object):
    def __init__(self, w0, w1, w2):
        self.w0, self.w1, self.w2 = w0, w1, w2
        self.opcode = w0 & 0x1F
        self.src_reg = (w0 >> 5) & 0x3F
        self.dst_reg = (w0 >> 12) & 0x3F
        self.fetch_valid_only = (w0 >> 19) & 1
        self.const_index = (w0 >> 20) & 0x1F
        self.src_swiz = (w0 >> 26) & 0x3F
        self.dst_swiz = w1 & 0xFFF
        self.use_reg_lod = (w1 >> 30) & 1
        self.use_comp_lod = (w1 >> 29) & 1
        # Texel offsets (texture fetches): w2 bits 16-20 / 21-25, signed 5-bit,
        # in HALF-texel units.  The road shaders' manual bilinear PCF is four
        # point fetches at (+-0.5, +-0.5) texels -- invisible without these.
        self.offset_x = _signed5((w2 >> 16) & 0x1F)
        self.offset_y = _signed5((w2 >> 21) & 0x1F)

    def text(self):
        op = FETCH_OP.get(self.opcode, "fetch_op%d" % self.opcode)
        c = "".join(CH[(self.src_swiz >> (2 * i)) & 3] for i in range(3))
        off = ""
        if self.opcode == 1 and (self.offset_x or self.offset_y):
            off = " off=(%+g,%+g)" % (self.offset_x * 0.5, self.offset_y * 0.5)
        return ["%-7s r%d.%s, r%d.%s, %s%d%s%s" % (
            op, self.dst_reg, fetch_dst_swz(self.dst_swiz), self.src_reg, c,
            "vf" if self.opcode == 0 else "tf", self.const_index, off,
            " [lod-from-reg]" if self.use_reg_lod else "")]


def disasm(ucode, const_bytes, stream_bytes, const_base=252, absolute=False):
    lines = []
    for i in range(const_bytes // 16):
        v = struct.unpack_from(">4f", ucode, 16 * i)
        lines.append("; literal c%-3d = {%g, %g, %g, %g}"
                     % (const_base + i, v[0], v[1], v[2], v[3]))
    base = const_bytes
    n = stream_bytes // 12
    words = [be(ucode, base + 4 * k) for k in range(n * 3)]

    # Pass 1: the control-flow instructions at the head of the stream.
    cfs = []
    slot = 0
    done = False
    while not done and slot < n:
        d0, d1, d2 = words[slot * 3:slot * 3 + 3]
        a = (d0, d1 & 0xFFFF)
        b = ((d1 >> 16) | ((d2 << 16) & 0xFFFFFFFF), d2 >> 16)
        for cf in (a, b):
            op = (cf[1] >> 12) & 0xF
            cfs.append((slot, cf, op))
            if op in (2, 4, 6, 14):
                done = True
        slot += 1
    n_cf_slots = slot

    kinds = {}
    for _s, cf, op in cfs:
        name = CF_OPCODE[op]
        if op in (1, 2, 3, 4, 5, 6, 13, 14):
            addr = cf[0] & 0xFFF
            cnt = (cf[0] >> 12) & 7
            seq = (cf[0] >> 16) & 0xFFF
            lines.append("; %-8s addr=%d count=%d seq=0x%03X" % (name, addr, cnt, seq))
            for k in range(cnt):
                kinds[addr + k] = "fetch" if ((seq >> (2 * k)) & 1) else "alu"
        elif op == 12:
            atype = {0: "none", 1: "position", 2: "interp/colors",
                     3: "memory"}[(cf[1] >> 9) & 3]
            lines.append("; alloc    %s size=%d" % (atype, cf[0] & 7))
        elif op == 0:
            pass
        else:
            lines.append("; %-8s raw=%08X %04X" % (name, cf[0], cf[1]))

    for idx in range(n_cf_slots, n):
        w = words[idx * 3:idx * 3 + 3]
        kind = kinds.get(idx, "alu")
        if all(x == 0 for x in w):
            continue
        if kind == "fetch":
            body = Fetch(*w).text()
        else:
            body = Alu(*w).text(absolute)
        for j, t in enumerate(body):
            lines.append("%3d %s %s" % (idx, "  " if j else ": ", t))
    return lines


if __name__ == "__main__":
    fn = sys.argv[1]
    cb = int(sys.argv[2])
    sb = int(sys.argv[3])
    base = int(sys.argv[4]) if len(sys.argv) > 4 else 252
    absolute = len(sys.argv) > 5 and sys.argv[5] == "abs"
    blob = open(fn, "rb").read()
    print("\n".join(disasm(blob, cb, sb, base, absolute)))
