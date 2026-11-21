# The byte-match measurer for Linux: the XDK's 32-bit Windows compiler and a Windows name
# decoder under Wine, plus Python for tools/bytematch. The image holds no XDK file, no game
# code and no tool code: those are mounted read-only at run time (tools/bytematch/wine.py).
#
#   docker build -t bp-bytematch tools/bytematch/docker

FROM ubuntu:24.04 AS helper
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc-mingw-w64-i686 \
 && rm -rf /var/lib/apt/lists/*
COPY undname.c /src/undname.c
RUN i686-w64-mingw32-gcc -O2 -s -static-libgcc -o /src/undname.exe /src/undname.c

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive \
    WINEDEBUG=-all \
    WINEARCH=win32 \
    WINEPREFIX=/home/build/.wine \
    WINEDLLOVERRIDES="mscoree,mshtml=" \
    PYTHONDONTWRITEBYTECODE=1
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends wine wine32:i386 python3 \
 && rm -rf /var/lib/apt/lists/*
COPY --from=helper /src/undname.exe /opt/bytematch/undname.exe
RUN useradd --create-home --uid 1500 build
USER build
# Wine answers the VC8 runtime and ATL (msvcr80, msvcp80, atl80) with its own rewrites
# through these side-by-side entries. Without them the XDK's own Microsoft copies beside
# cl.exe are used. Mono and Gecko stay uninstalled; c1xx.dll only needs mscoree to import.
RUN wineboot --init && wineserver --wait \
 && rm -rf "$WINEPREFIX"/drive_c/windows/winsxs/*vc80.crt* \
           "$WINEPREFIX"/drive_c/windows/winsxs/*vc80.atl* \
           "$WINEPREFIX"/drive_c/windows/winsxs/manifests/*vc80.crt* \
           "$WINEPREFIX"/drive_c/windows/winsxs/manifests/*vc80.atl*
ENV WINEDLLOVERRIDES="msvcr80,msvcp80,atl80=n;mshtml="
WORKDIR /work
