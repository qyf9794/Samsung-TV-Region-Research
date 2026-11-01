import sys
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_ARM, CS_MODE_LITTLE_ENDIAN
from capstone.arm import ARM_OP_IMM

path, name = sys.argv[1:3]
with open(path, 'rb') as f:
    elf = ELFFile(f)
    syms = elf.get_section_by_name('.dynsym')
    symbol = next(s for s in syms.iter_symbols() if s.name == name)
    addr = symbol['st_value'] & ~1
    section = elf.get_section(symbol['st_shndx'])
    off = addr - section['sh_addr']
    data = section.data()[off:off + symbol['st_size']]
    md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
    plt = elf.get_section_by_name('.plt')
    rel = elf.get_section_by_name('.rel.plt')
    calls = {}
    if plt and rel:
        by_got = {item['r_offset']: syms.get_symbol(item['r_info_sym']).name for item in rel.iter_relocations()}
        arm = Cs(CS_ARCH_ARM, CS_MODE_ARM | CS_MODE_LITTLE_ENDIAN)
        arm.detail = True
        arm.skipdata = True
        instrs = list(arm.disasm(plt.data(), plt['sh_addr']))
        for n in range(len(instrs) - 2):
            a, b, c = instrs[n:n+3]
            if a.mnemonic == 'add' and a.op_str == 'ip, pc, #0, #12' and b.mnemonic == 'add' and c.mnemonic == 'ldr' and '[ip, #' in c.op_str:
                addend = b.operands[2].imm if b.operands[2].type == ARM_OP_IMM else 0
                if len(b.operands) == 4 and b.operands[3].type == ARM_OP_IMM:
                    rotation = b.operands[3].imm % 32
                    if rotation:
                        addend = ((addend >> rotation) | (addend << (32 - rotation))) & 0xffffffff
                got = a.address + 8 + addend + c.operands[1].mem.disp
                if got in by_got:
                    calls[a.address] = by_got[got]
    def read_at(addr, n=100):
        for s in elf.iter_sections():
            if s['sh_addr'] <= addr < s['sh_addr'] + s['sh_size']:
                return s.data()[addr - s['sh_addr']:addr - s['sh_addr'] + n]
        return b''
    import struct
    literals = {}
    for i in md.disasm(data, addr):
        note = ''
        if i.mnemonic.startswith('bl') and i.op_str.startswith('#0x'):
            note = calls.get(int(i.op_str[1:], 16), '')
        if i.mnemonic == 'ldr' and '[pc, #' in i.op_str:
            reg = i.op_str.split(',')[0]
            offset = int(i.op_str.split('#')[1].rstrip(']'), 0)
            raw = read_at(((i.address + 4) & ~3) + offset, 4)
            if len(raw) == 4:
                literals[reg] = struct.unpack('<I', raw)[0]
                note = f'literal=0x{literals[reg]:x}'
        if i.mnemonic == 'add' and i.op_str.endswith(', pc'):
            reg = i.op_str.split(',')[0]
            if reg in literals:
                target = (i.address + 4 + literals[reg]) & 0xffffffff
                content = read_at(target, 100).split(b'\x00', 1)[0]
                note = f'addr=0x{target:x} {content!r}'
        print(f'{i.address:08x}: {i.mnemonic:9} {i.op_str:25} {note}')
