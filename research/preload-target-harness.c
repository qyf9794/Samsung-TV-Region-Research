#include <stdio.h>
#include <dlfcn.h>

extern int exact_call(void *, unsigned int, int *, int, int);
extern int _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(void *, unsigned int, int *, int, int);

int main(void)
{
    int target = -1, other_uid = -1, other_caller = -1;
    if (!dlopen(0, RTLD_NOW)) return 2;
    int a = exact_call(0, 761, &target, -40, -40);
    int b = exact_call(0, 760, &other_uid, -40, -40);
    int c = _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(0, 761, &other_caller, -40, -40);
    printf("target=%d/%d other_uid=%d/%d other_caller=%d/%d\n",
           a, target, b, other_uid, c, other_caller);
    return 0;
}
