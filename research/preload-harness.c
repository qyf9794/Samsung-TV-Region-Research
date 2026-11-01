#include <stdio.h>
#include <dlfcn.h>
extern int _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(void *, unsigned int, int *, int, int);
int main(void)
{
    if (dlopen(0, RTLD_NOW) == 0) return 2;
    int value = -1;
    int rc = _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(0, 761, &value, -40, -40);
    printf("forward_rc=%d forward_value=%d\n", rc, value);
    return (rc == 0 && value == 861) ? 0 : 1;
}
