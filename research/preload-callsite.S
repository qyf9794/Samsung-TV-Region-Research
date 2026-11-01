.syntax unified
.thumb
.section .tv_test_callsite,"ax",%progbits
.org 0x2c
.global exact_call
.type exact_call,%function
.thumb_func
exact_call:
    push {r4, lr}
    bl _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii
    pop {r4, pc}
.size exact_call, .-exact_call
