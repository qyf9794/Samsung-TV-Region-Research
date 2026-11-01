"""Verify the exact interposer's narrow target branch offline."""
import struct
import sys
from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_SP

path = sys.argv[1]
vm = Uc(UC_ARCH_ARM, UC_MODE_ARM)
vm.mem_map(0, 0x110000)
with open(path, 'rb') as f:
    elf = ELFFile(f)
    for segment in elf.iter_segments():
        if segment['p_type'] == 'PT_LOAD':
            vm.mem_write(segment['p_vaddr'], segment.data())
    symbol = next(s for s in elf.get_section_by_name('.dynsym').iter_symbols()
                  if s.name == '_ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii')
    entry = symbol['st_value']
vm.mem_map(0x200000, 0x10000)
vm.mem_map(0x300000, 0x1000)
vm.reg_write(UC_ARM_REG_SP, 0x20ff00)
vm.reg_write(UC_ARM_REG_LR, 0x70333)
vm.reg_write(UC_ARM_REG_R0, 0x300000)
vm.reg_write(UC_ARM_REG_R1, 761)
vm.reg_write(UC_ARM_REG_R2, 0x300100)
vm.reg_write(UC_ARM_REG_R3, 0xffffffd8)
vm.mem_write(0x300100, struct.pack('<I', 13))

def stop_at_return(uc, address, size, data):
    if address == 0x70332:
        uc.emu_stop()

vm.hook_add(UC_HOOK_CODE, stop_at_return)
vm.emu_start(entry, 0x70334, count=1000)
result = struct.unpack('<I', vm.mem_read(0x300100, 4))[0]
rc = vm.reg_read(UC_ARM_REG_R0)
print('target_result=%d rc=%d' % (result, rc))
assert result == 0 and rc == 0
