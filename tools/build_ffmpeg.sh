#!/usr/bin/env bash
# Build a minimal SHARED FFmpeg with the MSVC toolchain for the movie player.
# Components: VP6 (vp6/vp6a/vp6f) + MP4 (h264/aac) + common EA movie audio, mov/ea demuxers.
# Invoked by build_ffmpeg.bat, which puts cl/link (vcvars), nasm (Strawberry) and MSYS2 make/bash
# on PATH. $1 = repo root (Windows path; converted with cygpath). Installs to vendor/ffmpeg-build/.
set -e

ROOT="$(cygpath -u "$1")"
FF="$ROOT/b5-decomp/vendor/ffmpeg"
PREFIX="$ROOT/b5-decomp/vendor/ffmpeg-build"

cd "$FF"

if [ ! -f ffbuild/config.mak ]; then
    echo "==== configuring FFmpeg (msvc, minimal) ===="
    ./configure \
        --toolchain=msvc \
        --prefix="$PREFIX" \
        --disable-x86asm \
        --enable-shared --disable-static \
        --disable-programs --disable-doc --disable-network --disable-autodetect --disable-debug \
        --disable-everything \
        --enable-decoder=vp6,vp6a,vp6f,h264,aac,aac_latm,mp3,mp3float,pcm_s16le,pcm_s16be,adpcm_ea,adpcm_ea_r1,adpcm_ea_r2,adpcm_ea_r3,adpcm_ea_xas,adpcm_ea_maxis_xa \
        --enable-demuxer=mov,ea,ea_cdata,avi,h264,aac,mp3,wav \
        --enable-parser=vp6,h264,aac,mpegaudio \
        --enable-bsf=h264_mp4toannexb,aac_adtstoasc,extract_extradata \
        --enable-protocol=file
fi

echo "==== building FFmpeg ===="
make -j"$(nproc)"

echo "==== installing to $PREFIX ===="
make install

echo "==== FFmpeg build COMPLETE ===="
