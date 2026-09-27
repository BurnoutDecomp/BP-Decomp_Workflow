# syntax=docker/dockerfile:1
# The existing Python converters expect .exe names. These are native Linux ELF
# apphosts with those names, not Windows binaries or Wine shims.
FROM ubuntu:24.04 AS yap
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake ninja-build g++ qt6-base-dev ca-certificates && rm -rf /var/lib/apt/lists/*
COPY tools/yap /src/tools/yap
COPY tools/assets/converter_ui/deploy/native_yap /src/native_yap
RUN cmake -S /src/native_yap -B /obj -G Ninja -DCMAKE_BUILD_TYPE=Release \
    && cmake --build /obj --parallel 2

FROM mcr.microsoft.com/dotnet/sdk:9.0-noble AS volatility
ARG TARGETARCH
COPY tools/volatility /src/volatility
RUN case "$TARGETARCH" in amd64) rid=linux-x64 ;; arm64) rid=linux-arm64 ;; *) exit 1 ;; esac \
    && dotnet publish /src/volatility/src/Volatility.Cli/Volatility.Cli.csproj \
       -c Release -r "$rid" --self-contained true -o /out --nologo \
       -p:PublishSingleFile=false -p:PublishTrimmed=false \
    && mv /out/Volatility.Cli /out/Volatility.Cli.exe

FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PYTHONIOENCODING=utf-8 PATH=/opt/venv/bin:$PATH \
    PARADISE_DATA_DIR=/data PARADISE_WORK_DIR=/data/runtime PARADISE_SANDBOX=1 \
    HOME=/tmp DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv libqt6core6t64 libicu74 libssl3t64 libstdc++6 zlib1g ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv \
    && groupadd --gid 10001 converter \
    && useradd --uid 10001 --gid 10001 --no-create-home converter
COPY tools/assets/converter_ui/deploy/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
WORKDIR /app
COPY tools/assets /app/tools/assets
COPY tools/build/build_config.py /app/tools/build/build_config.py
COPY --from=yap /obj/YAP /app/build/tools/yap/YAP.exe
COPY --from=volatility /out /app/build/tools/volatility
RUN mkdir -p /data && chown converter:converter /data
USER 10001:10001
EXPOSE 8080
WORKDIR /app/tools/assets/converter_ui
# One process owns scheduling/session state. Concurrency comes from threads and
# isolated conversion subprocesses, not additional Gunicorn workers.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--worker-class", "gthread", "--threads", "8", "--timeout", "120", "--graceful-timeout", "30", "--worker-tmp-dir", "/tmp", "--error-logfile", "-", "hosted:create_app()"]
