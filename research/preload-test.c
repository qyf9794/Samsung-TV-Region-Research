// Diagnostic: proves whether an isolated stock process loads an unsigned library.
// It does not access factory settings, devices, or persistent storage.
extern long write(int, const void *, unsigned long);
__attribute__((constructor)) static void marker(void) {
    static const char message[] = "TV_PRELOAD_TEST_LOADED\n";
    write(2, message, sizeof(message) - 1);
}
