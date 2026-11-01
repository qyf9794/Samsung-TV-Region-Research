"""Emulate the factory daemon's local-set filter entirely on the Mac.

The firmware's GetFactoryUID call is replaced by a controlled test value.
This script never connects to or modifies the television.
"""
import argparse
import struct

from elftools.elf.elffile import ELFFile
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_SP

FUNC = 0x70304
GET_FACTORY_UID_PLT = 0x2d7b4
RETURN = 0x400000


def run(path, preventing_import, region_enum, trace=False, patch_compare=False):
    vm = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    vm.mem_map(0x10000, 0x100000)
    with open(path, 'rb') as f:
        elf = ELFFile(f)
        for seg in elf.iter_segments():
            if seg['p_type'] == 'PT_LOAD':
                vm.mem_write(seg['p_vaddr'], seg.data())
    if patch_compare:
        if bytes(vm.mem_read(0x703a8, 2)) != bytes.fromhex('0d2b'):
            raise RuntimeError('unexpected compare instruction')
        vm.mem_write(0x703a8, bytes.fromhex('ff2b'))
    vm.mem_map(0x200000, 0x10000)
    vm.mem_map(0x300000, 0x10000)
    vm.mem_map(RETURN, 0x1000)
    vm.mem_write(0x300008, struct.pack('<I', 0x300200))
    vm.reg_write(UC_ARM_REG_SP, 0x20ff00)
    vm.reg_write(UC_ARM_REG_LR, RETURN | 1)
    vm.reg_write(UC_ARM_REG_R0, 0x300000)
    vm.reg_write(UC_ARM_REG_R1, region_enum)
    vm.reg_write(UC_ARM_REG_R2, 0x300100)
    observed = []

    def code_hook(uc, addr, size, data):
        if trace and FUNC <= addr < FUNC + 0x140:
            from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
            for ins in Cs(CS_ARCH_ARM, CS_MODE_THUMB).disasm(bytes(uc.mem_read(addr, size)), addr):
                print('0x%x: %s %s' % (addr, ins.mnemonic, ins.op_str))
        if addr == RETURN:
            uc.emu_stop()
        elif addr == GET_FACTORY_UID_PLT:
            uid = uc.reg_read(UC_ARM_REG_R1)
            if uid != 761:
                raise RuntimeError('unexpected UID ' + str(uid))
            observed.append(uid)
            uc.mem_write(uc.reg_read(UC_ARM_REG_R2), struct.pack('<I', preventing_import))
            uc.reg_write(UC_ARM_REG_R0, 0)
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    vm.hook_add(UC_HOOK_CODE, code_hook)
    vm.emu_start(FUNC | 1, RETURN + 2, count=10000)
    if observed != [761]:
        raise RuntimeError('expected UID lookup was not executed')
    return struct.unpack('<I', vm.mem_read(0x300100, 4))[0]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('daemon')
    parser.add_argument('--trace-us', action='store_true')
    args = parser.parse_args()
    if args.trace_us:
        print('skip=%d' % run(args.daemon, 13, 23, trace=True))
        raise SystemExit(0)
    for lock in (13, 0):
        for label, value in (('US_AD_AU2', 23), ('CHINA', 65), ('NONE', 0)):
            print('PreventingImport=%d %s enum=%d skip=%d' % (lock, label, value, run(args.daemon, lock, value)))
