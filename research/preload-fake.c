__attribute__((visibility("default")))
int _ZN19FCStorageBaseCommon13GetFactoryUIDEjPiii(void *self, unsigned int uid, int *out, int source, int resolution)
{
    (void)self; (void)source; (void)resolution;
    *out = (int)uid + 100;
    return 0;
}
