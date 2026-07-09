"""Operand-aware AS2 disassembler for GuiApt bundles — BOTH the native-8
(Apt Data:1:7:8, x64 widened) and the original 32-bit (Apt Data:1:7:4) forms.

Decodes every frame action stream (tag 1/2 DoAction + tag 8 InitAction) and
every inline DefineFunction2/DefineFunction body across ALL type-0x1E resources
of a bundle, with operands resolved exactly the way the engine's
AptActionInterpreter::_parseStream does
(b5-decomp/src/SDKs/EATech/include/Apt/AptActionInterpreterParseStream.cpp,
the XB1 sub_14084A920 shapes; the 1:7:4 shapes are the same tree with 4-byte
slots and 4-alignment):

  * inline 4-byte unaligned: 0x77 TraceStart, 0xB4 PushFloat, 0xB7 PushDWord
  * inline 4-byte aligned:   0x81/0x87/0x99/0x9D/0x9F/0xB8
  * inline byte:  0xA2 0xAE 0xAF 0xB0 0xB1 0xB2 0xB3 0xB5 (dict index / byte)
  * inline word:  0xA3 0xB6
  * aligned records: 0x83(2 str) 0x8B/0x8C/0xA1/0xA4..0xA7(1 str)
    0x94 With 0x8F Try 0x8E/0x9B DefineFunction2/1 (header + inline body)
    0x88/0x96 DefineDictionary/Push ({count, table}; entries = serialized
    indices into the CONST chunk's records {u32 type, payload}:
    1=string(const-chunk-rel) 6=float 7=int 8=Lookup[dict] 5=bool 4=Register
    3=undefined)
  * string operands in the STREAM are apt-chunk-relative offsets

DF2 header:  1:7:8 (48B): name u64@0, nargs i32@8, regs u16@0xC, preload
u16@0xE, argtab u64@0x10 (16B recs {reg u32, name u64@+8}), bodyLen u32@0x18,
sig1/sig2 @0x20/0x28, body @0x30.
             1:7:4 (28B): name u32@0, nargs i32@4, regs u16@8, preload u16@0xA,
argtab u32@0xC (8B recs {reg u32, name u32}), bodyLen u32@0x10, sig1/sig2
@0x14/0x18, body @0x1C.

Dictionary-byte operands (0xA2/0xAE/0xAF/0xB0..0xB3) are annotated against the
most recent 0x88 DefineDictionary seen in the linear walk (the engine installs
a function's captured pool at call time; linear order matches define order).

Usage: python apt8_disasm.py <bundle> [--grep NAME] [--movie NAME]
  --grep  only print streams/functions whose text mentions NAME
  --movie only walk resources whose header name matches
"""
import struct
import sys

OP_NAMES = {
    0x00: 'End', 0x04: 'NextFrame', 0x05: 'PrevFrame', 0x06: 'Play', 0x07: 'Stop',
    0x0A: 'Add', 0x0B: 'Subtract', 0x0C: 'Multiply', 0x0D: 'Divide',
    0x0E: 'Equals', 0x0F: 'LessThan', 0x10: 'And', 0x11: 'Or', 0x12: 'Not',
    0x13: 'StringEquals', 0x14: 'StringLength', 0x15: 'SubString', 0x17: 'Pop',
    0x18: 'ToInteger', 0x1C: 'GetVariable', 0x1D: 'SetVariable',
    0x20: 'SetTarget2', 0x21: 'StringAdd', 0x22: 'GetProperty', 0x23: 'SetProperty',
    0x24: 'CloneSprite', 0x25: 'RemoveSprite', 0x26: 'Trace', 0x27: 'StartDragMovie',
    0x28: 'StopDragMovie', 0x2A: 'Throw', 0x2B: 'CastOp', 0x2C: 'ImplementsOp',
    0x30: 'Random', 0x33: 'AsciiToChar', 0x34: 'GetTimer', 0x3A: 'Delete',
    0x3B: 'Delete2', 0x3C: 'DefineLocal', 0x3D: 'CallFunction', 0x3E: 'Return',
    0x3F: 'Modulo', 0x40: 'NewObject', 0x41: 'DefineLocal2', 0x42: 'InitArray',
    0x43: 'InitObject', 0x44: 'TypeOf', 0x45: 'TargetPath', 0x46: 'Enumerate',
    0x47: 'Add2', 0x48: 'LessThan2', 0x49: 'Equals2', 0x4A: 'ToNumber',
    0x4B: 'ToString', 0x4C: 'PushDuplicate', 0x4D: 'StackSwap', 0x4E: 'GetMember',
    0x4F: 'SetMember', 0x50: 'Increment', 0x51: 'Decrement', 0x52: 'CallMethod',
    0x53: 'NewMethod', 0x55: 'Enumerate2', 0x56: 'PushThis', 0x58: 'PushGlobal',
    0x59: 'Push0', 0x5A: 'Push1', 0x5B: 'CallFuncAndPop', 0x5C: 'CallFuncSetVar',
    0x5D: 'CallMethodPop', 0x5E: 'CallMethodSetVar', 0x60: 'BitAnd', 0x61: 'BitOr',
    0x62: 'BitXor', 0x63: 'BitLShift', 0x64: 'BitRShift', 0x67: 'Greater',
    0x69: 'Extends', 0x70: 'PushThisVariable', 0x71: 'PushGlobalVariable',
    0x72: 'PushZeroSetVar', 0x73: 'PushTrue', 0x74: 'PushFalse',
    0x75: 'PushUndefined', 0x76: 'PushNULL', 0x77: 'TraceStart',
    0x81: 'GotoFrame', 0x83: 'GetUrl', 0x87: 'StoreRegister',
    0x88: 'DefineDictionary', 0x8B: 'SetTarget', 0x8C: 'GotoLabel',
    0x8E: 'DefineFunction2', 0x8F: 'Try', 0x94: 'With', 0x96: 'Push',
    0x99: 'BranchAlways', 0x9A: 'GetUrl2', 0x9B: 'DefineFunction',
    0x9D: 'BranchIfTrue', 0x9E: 'CallFrame', 0x9F: 'GotoFrame2',
    0xA1: 'PushString', 0xA2: 'PushStringDictByte', 0xA3: 'PushStringDictWord',
    0xA4: 'PushStringGetVar', 0xA5: 'PushStringGetMember',
    0xA6: 'PushStringSetVar', 0xA7: 'PushStringSetMember',
    0xAE: 'StringDictByteGetVar', 0xAF: 'StringDictByteGetMember',
    0xB0: 'DictCallFuncPop', 0xB1: 'DictCallFuncSetVar',
    0xB2: 'DictCallMethodPop', 0xB3: 'DictCallMethodSetVar',
    0xB4: 'PushFloat', 0xB5: 'PushByte', 0xB6: 'PushWord', 0xB7: 'PushDWord',
    0xB8: 'BranchIfFalse',
}

PRELOAD_BITS = [(0x01, 'this'), (0x02, 'noThis'), (0x04, 'args'),
                (0x08, 'noArgs'), (0x10, 'super'), (0x20, 'noSuper'),
                (0x40, '_root'), (0x80, '_parent'), (0x100, '_global')]


def rd16(b, o): return struct.unpack_from('<H', b, o)[0]
def rd32(b, o): return struct.unpack_from('<I', b, o)[0]
def rds32(b, o): return struct.unpack_from('<i', b, o)[0]
def rd64(b, o): return struct.unpack_from('<Q', b, o)[0]
def rdf32(b, o): return struct.unpack_from('<f', b, o)[0]


class Resource(object):
    def __init__(self, data, res_base, res_size):
        self.data = data
        self.res_base = res_base
        self.res_size = res_size
        # width probe: the 1:7:8 header is 6 u64 fields, the 1:7:4 header 6 u32
        magic8 = res_base + rd64(data, res_base + 0x10) if res_base + 0x18 <= len(data) else 0
        self.w8 = (0 < rd64(data, res_base + 0x10) < res_size
                   and bytes(data[magic8:magic8 + 14]) == b'Apt Data:1:7:8')
        if self.w8:
            hdr = [rd64(data, res_base + 8 * i) for i in range(6)]
        else:
            hdr = [rd32(data, res_base + 4 * i) for i in range(6)]
        self.name = self.cstr_at(res_base + hdr[0]) if hdr[0] else '?'
        self.apt_base = res_base + hdr[2]
        self.apt_size = res_size - hdr[2]
        self.const_base = res_base + hdr[3] if hdr[3] else 0
        self.const_count = 0
        self.const_table = 0
        if self.const_base and bytes(data[self.const_base:self.const_base + 12]) == b'Apt constant':
            if self.w8:
                self.const_count = rd64(data, self.const_base + 0x20)
                self.const_table = self.const_base + rd64(data, self.const_base + 0x28)
                self.const_stride = 16
            else:
                self.const_count = rd32(data, self.const_base + 0x18)
                self.const_table = self.const_base + rd32(data, self.const_base + 0x1C)
                self.const_stride = 8
        # width-dependent readers
        self.psz = 8 if self.w8 else 4
        self.rdp = (lambda o: rd64(self.data, o)) if self.w8 else (lambda o: rd32(self.data, o))

    def align(self, x):
        m = self.psz - 1
        return (x + m) & ~m

    def cstr_at(self, absoff, maxlen=256):
        d = self.data
        end = d.find(b'\0', absoff, absoff + maxlen)
        if end < 0:
            end = absoff + maxlen
        try:
            return d[absoff:end].decode('latin1')
        except Exception:
            return '<badstr>'

    def apt_str(self, chunkrel):
        if 0 < chunkrel < self.apt_size:
            return self.cstr_at(self.apt_base + chunkrel)
        return '<off %#x OOB>' % chunkrel

    def const_str(self, chunkrel):
        return self.cstr_at(self.const_base + chunkrel)

    def const_record(self, idx):
        """-> printable repr of const record idx (the _parseStream resolution)."""
        if not self.const_table or idx < 0 or idx >= self.const_count:
            return '<const[%d] OOB>' % idx
        rec = self.const_table + self.const_stride * idx
        t = rd32(self.data, rec)
        payoff = 8 if self.w8 else 4
        if t == 1:
            return "'%s'" % self.const_str(self.rdp(rec + payoff))
        if t == 7:
            return 'int %d' % rds32(self.data, rec + payoff)
        if t == 6:
            return 'float %g' % rdf32(self.data, rec + payoff)
        if t == 5:
            return 'bool %d' % rd32(self.data, rec + payoff)
        if t == 3:
            return 'undefined'
        if t == 8:
            return ('LOOKUP', rds32(self.data, rec + payoff))   # dict[idx] at runtime
        if t == 4:
            return 'REG(%d)' % rds32(self.data, rec + payoff)
        return '<type %d payload %#x>' % (t, self.rdp(rec + payoff))


def disasm_stream(res, stream_rel, out, label, dict_state):
    """Linear walk from apt-chunk-relative offset; nested DF bodies inline.
    dict_state = [list-of-entries or None]  (mutable: the active 0x88 pool)."""
    d = res.data
    base = res.apt_base
    P = res.psz
    pc = base + stream_rel
    end_hard = res.apt_base + res.apt_size
    fn_stack = []   # (end_abs, name) for open DefineFunction bodies

    def dict_entry(i):
        pool = dict_state[0]
        if pool is None:
            return '<no dict>'
        if 0 <= i < len(pool):
            return pool[i]
        return '<dict[%d] OOB>' % i

    out.append('--- %s @+%#x ---' % (label, stream_rel))
    last_pushed_strings = []
    while pc < end_hard:
        while fn_stack and pc >= fn_stack[-1][0]:
            out.append('%*s} // end function %s' % (4 + 2 * (len(fn_stack) - 1), '', fn_stack[-1][1]))
            fn_stack.pop()
        off = pc - base
        op = d[pc]
        pc += 1
        ind = '    ' + '  ' * len(fn_stack)
        name = OP_NAMES.get(op, 'op_%02X' % op)
        if op == 0x00:
            out.append('%s%06x  End' % (ind, off))
            if fn_stack:
                continue
            break
        elif op in (0x77, 0xB4, 0xB7):
            v = rdf32(d, pc) if op == 0xB4 else rd32(d, pc)
            out.append('%s%06x  %s %s' % (ind, off, name, v))
            pc += 4
        elif op in (0x81, 0x87, 0x99, 0x9D, 0x9F, 0xB8):
            pc = res.align(pc)
            v = rds32(d, pc)
            extra = ''
            if op in (0x99, 0x9D, 0xB8):
                extra = ' -> +%#x' % ((pc + 4 + v) - base)
            out.append('%s%06x  %s %d%s' % (ind, off, name, v, extra))
            pc += 4
        elif op in (0xA2, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB5):
            v = d[pc]
            pc += 1
            if op == 0xB5:
                out.append('%s%06x  %s %d' % (ind, off, name, v))
            else:
                out.append('%s%06x  %s dict[%d] = %s' % (ind, off, name, v, dict_entry(v)))
                if op == 0xA2 and isinstance(dict_entry(v), str):
                    last_pushed_strings.append(dict_entry(v))
        elif op in (0xA3, 0xB6):
            v = rd16(d, pc)
            pc += 2
            if op == 0xB6:
                out.append('%s%06x  %s %d' % (ind, off, name, v))
            else:
                out.append('%s%06x  %s dict[%d] = %s' % (ind, off, name, v, dict_entry(v)))
        elif op == 0x83:
            rec = res.align(pc)
            pc = rec + 2 * P
            out.append("%s%06x  GetUrl '%s' '%s'" % (ind, off,
                       res.apt_str(res.rdp(rec)), res.apt_str(res.rdp(rec + P))))
        elif op in (0x8B, 0x8C, 0xA1, 0xA4, 0xA5, 0xA6, 0xA7):
            rec = res.align(pc)
            pc = rec + P
            s = res.apt_str(res.rdp(rec))
            out.append("%s%06x  %s '%s'" % (ind, off, name, s))
            last_pushed_strings.append(s)
        elif op == 0x94:
            rec = res.align(pc)
            pc = rec + P
            out.append('%s%06x  With end=+%#x' % (ind, off, res.rdp(rec) + (pc - base)))
        elif op == 0x8F:
            rec = res.align(pc)
            pc = rec + (24 if res.w8 else 16)
            out.append('%s%06x  Try (record skipped)' % (ind, off))
        elif op in (0x8E, 0x9B):
            rec = res.align(pc)
            if res.w8:
                fn_name_off = rd64(d, rec)
                nargs = rds32(d, rec + 8)
                nregs = rd16(d, rec + 0x0C)
                preload = rd16(d, rec + 0x0E)
                argtab = rd64(d, rec + 0x10)
                blen = rd32(d, rec + 0x18)
                body = rec + 0x30
                astride, anameoff = (16, 8) if op == 0x8E else (8, 0)
            else:
                fn_name_off = rd32(d, rec)
                nargs = rds32(d, rec + 4)
                nregs = rd16(d, rec + 8)
                preload = rd16(d, rec + 0x0A)
                argtab = rd32(d, rec + 0x0C)
                blen = rd32(d, rec + 0x10)
                body = rec + 0x1C
                astride, anameoff = (8, 4) if op == 0x8E else (4, 0)
            fn_name = res.apt_str(fn_name_off) if fn_name_off else ''
            guessed = ''
            if not fn_name and last_pushed_strings:
                guessed = ' /* likely "%s" */' % last_pushed_strings[-1]
            bits = '+'.join(n for m, n in PRELOAD_BITS if preload & m) or '0'
            args = []
            if 0 < nargs <= 64 and 0 < argtab < res.apt_size:
                for i in range(nargs):
                    a = base + argtab + astride * i
                    if op == 0x8E:
                        args.append('r%d=%s' % (rd32(d, a), res.apt_str(res.rdp(a + anameoff))))
                    else:
                        args.append(res.apt_str(res.rdp(a)))
            out.append('%s%06x  %s name="%s"%s nargs=%d regs=%d preload=%s(%#x) bodyLen=%d {'
                       % (ind, off, name, fn_name, guessed, nargs, nregs, bits, preload, blen))
            if args:
                out.append('%s        args: %s' % (ind, ', '.join(args)))
            fn_stack.append((body + blen, fn_name or (guessed.strip(' /*"') or '<anon>')))
            pc = body
        elif op in (0x88, 0x96):
            rec = res.align(pc)
            pc = rec + 2 * P
            cnt = rds32(d, rec)
            tab = res.rdp(rec + P)
            vals = []
            raws = []
            if 0 <= cnt <= 4096 and 0 < tab < res.apt_size:
                for i in range(cnt):
                    idx = res.rdp(base + tab + P * i)
                    raws.append(idx)
                    if idx > 0xFFFF and (idx & 0xFFFFFFFF) == 0 and (idx >> 32) <= 0xFFFF:
                        idx >>= 32    # the packed high-dword form
                    r = res.const_record(idx if idx <= 0xFFFF else -1)
                    if isinstance(r, tuple):     # LOOKUP -> the active dictionary
                        r = 'Lookup dict[%d]=%s' % (r[1], dict_entry(r[1]))
                    vals.append(r)
            if op == 0x88:
                dict_state[0] = vals
                out.append('%s%06x  DefineDictionary count=%d' % (ind, off, cnt))
                for i, v in enumerate(vals):
                    out.append('%s          [%d] %s' % (ind, i, v))
            else:
                out.append('%s%06x  Push %s' % (ind, off,
                           ', '.join('%s <i%d>' % (v, r) for v, r in zip(vals, raws))))
                for v in vals:
                    if isinstance(v, str) and v.startswith("'"):
                        last_pushed_strings.append(v.strip("'"))
        else:
            out.append('%s%06x  %s' % (ind, off, name))
    return out


def walk_resource(res, grep=None):
    d = res.data
    base = res.apt_base
    P = res.psz
    out = []
    magic = b'Apt Data:1:7:8' if res.w8 else b'Apt Data:1:7:4'
    if not bytes(d[base:base + 14]).startswith(magic):
        return ['(unexpected apt magic, skipped)']
    # movie-def struct offsets (w8 / w4)
    if res.w8:
        O_SIG, O_FC, O_FRO, O_CC, O_CT = 8, 0x20, 0x28, 0x38, 0x40
    else:
        O_SIG, O_FC, O_FRO, O_CC, O_CT = 4, 0x10, 0x14, 0x1C, 0x20
    # find the type-9 root
    root = None
    pos = base - 1
    sig4 = struct.pack('<I', 0x09876543)
    hard_end = res.res_base + res.res_size
    while True:
        pos = d.find(sig4, pos + 1, hard_end)
        if pos < 0:
            break
        if pos - O_SIG >= base and res.rdp(pos - O_SIG) == 9:
            root = pos - O_SIG - base
            break
    if root is None:
        return ['(no root movie)']
    movies = [('root', root)]
    cc = res.rdp(base + root + O_CC)
    ct = res.rdp(base + root + O_CT)
    if 0 < cc <= 4096 and 0 < ct < res.apt_size:
        for i in range(cc):
            v = res.rdp(base + ct + P * i)
            if not v or v >= res.apt_size:
                continue
            if res.rdp(base + v) in (5, 9) and rd32(d, base + v + O_SIG) == 0x09876543:
                movies.append(('char[%d]' % i, v))
    dict_state = [None]
    seen_streams = set()
    for mname, ch in movies:
        fc = res.rdp(base + ch + O_FC)
        fro = res.rdp(base + ch + O_FRO)
        if not (0 < fc <= 4096 and 0 < fro < res.apt_size):
            continue
        for f in range(fc):
            rec = fro + 2 * P * f
            cnt = rd32(d, base + rec)
            cmds = res.rdp(base + rec + P)
            if not (0 < cnt <= 512 and 0 < cmds < res.apt_size):
                continue
            for ci in range(cnt):
                cmd = res.rdp(base + cmds + P * ci)
                if not cmd or cmd >= res.apt_size:
                    continue
                tag = rd32(d, base + cmd)
                aligned = (base + cmd) % 8 == 0
                extra = ''
                if tag in (1, 2):
                    # action: {tag, stream@+P}; w8 packed form: stream @ align8(cmd+4)
                    if res.w8:
                        stream = rd64(d, base + cmd + 8) if aligned \
                            else rd64(d, (base + cmd + 4 + 7) & ~7)
                    else:
                        stream = rd32(d, base + cmd + 4)
                elif tag == 8:
                    # init-action: {tag, charId@+P, stream@+2P};
                    # w8 packed: charId@+4, stream @ align8(cmd+8)
                    if res.w8:
                        if aligned:
                            cid = rd64(d, base + cmd + 8)
                            stream = rd64(d, base + cmd + 16)
                        else:
                            cid = rd32(d, base + cmd + 4)
                            stream = rd64(d, (base + cmd + 8 + 7) & ~7)
                    else:
                        cid = rd32(d, base + cmd + 4)
                        stream = rd32(d, base + cmd + 8)
                    extra = ' char=%d' % cid
                elif tag == 3 and res.w8:
                    # PLACE: clipActions block @body+0x40 (body = align8(cmd+4));
                    # block {i32 count; recArray@+8}; records stride 16 with
                    # {u64 eventMask@0, stream@+8}. Disassemble each stream.
                    body = (base + cmd + 4 + 7) & ~7
                    nameoff = rd64(d, body + 0x30)
                    iname = res.apt_str(nameoff) if 0 < nameoff < res.apt_size else ''
                    clip = rd64(d, body + 0x40)
                    if not (0 < clip < res.apt_size):
                        continue
                    ccount = rds32(d, base + clip)
                    ctab = rd64(d, base + clip + 8)
                    if not (0 < ccount <= 64 and 0 < ctab < res.apt_size):
                        continue
                    for ri in range(ccount):
                        rmask = rd64(d, base + ctab + 16 * ri)
                        rstream = rd64(d, base + ctab + 16 * ri + 8)
                        if not (0 < rstream < res.apt_size) or rstream in seen_streams:
                            continue
                        seen_streams.add(rstream)
                        chunk = []
                        try:
                            disasm_stream(res, rstream, chunk,
                                          '%s %s f%d cmd%d PLACE "%s" clipAction[%d] mask=%#x'
                                          % (res.name, mname, f, ci, iname, ri, rmask),
                                          dict_state)
                        except Exception as ex:
                            chunk.append('  !! decode error: %s' % ex)
                        text = '\n'.join(chunk)
                        if grep is None or grep.lower() in text.lower():
                            out.append(text)
                    continue
                else:
                    continue
                if not (0 < stream < res.apt_size):
                    continue
                if stream in seen_streams:
                    continue
                seen_streams.add(stream)
                chunk = []
                try:
                    disasm_stream(res, stream, chunk,
                                  '%s %s f%d cmd%d tag%d%s' % (res.name, mname, f, ci, tag, extra),
                                  dict_state)
                except Exception as ex:
                    chunk.append('  !! decode error: %s' % ex)
                text = '\n'.join(chunk)
                if grep is None or grep.lower() in text.lower():
                    out.append(text)
    return out


def main():
    path = sys.argv[1]
    grep = None
    movie_filter = None
    args = sys.argv[2:]
    while args:
        a = args.pop(0)
        if a == '--grep':
            grep = args.pop(0)
        elif a == '--movie':
            movie_filter = args.pop(0)
    data = open(path, 'rb').read()
    assert data[:4] == b'bnd2'
    n_ent = rd32(data, 0x10)
    ent_off = rd32(data, 0x14)
    d0 = rd32(data, 0x18)
    for e in range(n_ent):
        b = ent_off + 0x40 * e
        if rd32(data, b + 0x38) != 0x1E:
            continue
        res = Resource(data, d0 + rd32(data, b + 0x28), rd32(data, b + 0x10) & 0x0FFFFFFF)
        if movie_filter and movie_filter.lower() not in res.name.lower():
            continue
        chunks = walk_resource(res, grep)
        if chunks:
            print('===== resource "%s" (entry %d, %s) =====' % (res.name, e, '1:7:8' if res.w8 else '1:7:4'))
            for c in chunks:
                print(c)
                print()


if __name__ == '__main__':
    main()
