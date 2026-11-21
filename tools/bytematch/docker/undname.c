/* Decode MSVC decorated names the way tools/bytematch/artist.py does on Windows:
 * UnDecorateSymbolName(name, out, 8192, UNDNAME_NAME_ONLY), or a CRT's __unDName with the
 * same buffer and flags. One name per line on stdin, one line per name on stdout: the
 * decoded name, or the input unchanged when it does not decode (as artist.demangle does).
 *
 * Built with mingw-w64 into the byte-match container and run under Wine.
 * usage: undname.exe [library [assembly.manifest]]
 *   library   dbghelp.dll (the default) or a CRT such as msvcr80.dll
 *   manifest  an assembly manifest to activate first: a VC8 CRT refuses to load
 *             (DllMain fails, error 1114) unless an activation context names it
 */
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef DWORD (WINAPI *undecorate_fn)(PCSTR, PSTR, DWORD, DWORD);
typedef char *(__cdecl *undname_fn)(char *, const char *, int,
                                    void *(__cdecl *)(size_t), void (__cdecl *)(void *),
                                    unsigned short);

#define NAME_ONLY 0x1000
#define OUT_SIZE 8192 /* artist.demangle's buffer */

static char line[1 << 17];
static char out[OUT_SIZE];

static void *__cdecl get(size_t size) { return malloc(size); }
static void __cdecl put(void *block) { free(block); }

int main(int argc, char **argv)
{
    const char *library = argc > 1 ? argv[1] : "dbghelp.dll";
    HMODULE module;
    undecorate_fn undecorate;
    undname_fn undname = NULL;

    if (argc > 2) {
        ACTCTXA actctx;
        HANDLE context;
        ULONG_PTR cookie;
        memset(&actctx, 0, sizeof actctx);
        actctx.cbSize = sizeof actctx;
        actctx.lpSource = argv[2];
        context = CreateActCtxA(&actctx);
        if (context == INVALID_HANDLE_VALUE || !ActivateActCtx(context, &cookie)) {
            fprintf(stderr, "undname: cannot activate %s (error %lu)\n", argv[2], GetLastError());
            return 2;
        }
    }
    module = LoadLibraryA(library);
    if (!module) {
        fprintf(stderr, "undname: cannot load %s (error %lu)\n", library, GetLastError());
        return 2;
    }
    undecorate = (undecorate_fn)GetProcAddress(module, "UnDecorateSymbolName");
    if (!undecorate)
        undname = (undname_fn)GetProcAddress(module, "__unDName");
    if (!undecorate && !undname) {
        fprintf(stderr, "undname: %s exports neither UnDecorateSymbolName nor __unDName\n", library);
        return 2;
    }
    setvbuf(stdout, NULL, _IOFBF, 1 << 16);
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);
        const char *text = line;
        while (n && (line[n - 1] == '\n' || line[n - 1] == '\r'))
            line[--n] = 0;
        if (line[0] == '?') {
            out[0] = 0;
            if (undecorate ? undecorate(line, out, OUT_SIZE, NAME_ONLY) != 0
                           : undname(out, line, OUT_SIZE, get, put, NAME_ONLY) != NULL)
                text = out;
        }
        fputs(text, stdout);
        fputc('\n', stdout);
    }
    fflush(stdout);
    return 0;
}
