/* Diagnostic-only interposition for the exact firmware build inspected offline.
 * It changes the UID 761 result only for the known filter call site. It does
 * not write factory data or alter the return values of other callers.
 */
typedef unsigned int uint32_t;
typedef unsigned long uintptr_t;
extern void *dlsym(void *, const char *);
typedef int (*get_uid_fn)(void *, uint32_t, int *, int, int);

__attribute__((visibility("default")))
int _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(
    void *self, uint32_t uid, int *out, int source, int resolution)
{
    uintptr_t caller = (uintptr_t)__builtin_return_address(0) & ~(uintptr_t)1;
    if (caller == 0x70332 && uid == 761 && out != 0) {
        *out = 0;
        return 0;
    }
    get_uid_fn original = (get_uid_fn)dlsym((void *)-1,
        "_ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii");
    if (original == 0) return -1;
    return original(self, uid, out, source, resolution);
}
