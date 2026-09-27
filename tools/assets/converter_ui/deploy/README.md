# Public converter on Ubuntu

This deployment is open to anyone with the URL. There is no login or shared access
password. Each browser receives a signed, HttpOnly session cookie; uploads, jobs,
reports and ZIP downloads are restricted to that browser's workspace.

## Deploy

Use Ubuntu 24.04 on x86-64 or ARM64, with Docker Engine and the Compose plugin.
Install them using [Docker's Ubuntu instructions](https://docs.docker.com/engine/install/ubuntu/).
The default runtime budget is 4 CPUs / 4 GiB RAM; allow additional memory for image
compilation and leave space for the image, uploads, staging and ZIP archives.

1. Point a DNS hostname such as `convert.example.com` at the server. Allow inbound
   TCP 80 and 443. The included Caddy service handles HTTPS certificates and redirects.
2. Clone this repository on the server, or copy the changed repository there. Only
   the YAP and Volatility submodules are needed; the launcher initializes both.
3. From the repository root, run:

   ```bash
   bash deploy-converter.sh convert.example.com
   ```

4. Open `https://convert.example.com`. Choose files or a folder, inspect the queue,
   convert, then **Download ZIP**. The download is streamed to the browser.

The first invocation writes `tools/assets/converter_ui/deploy/.env`. Later invocations
keep it. To customize limits, copy settings from `.env.example` into that file and
run the launcher again. It rebuilds/restarts this deployment; it does not pull Git
changes or install Docker for you.

The image builds **native Linux YAP and Volatility** from the checked-out submodule
revisions. Their filenames retain `.exe` because existing converter scripts refer
to those names; they are Linux binaries. There is no Wine dependency and no need
to upload your locally built Windows tools. Volatility is published without trimming
so its reflection-based resource registrations remain available.
The Linux YAP build supplies a small Qt integer-stream adapter for LP64 type aliases;
it leaves the submodule checkout and Windows build unchanged.

## Existing reverse proxy

The supplied Caddy service owns ports 80/443. If your server already uses a proxy,
run only `converter` and expose it to the host loopback interface with this override:

```yaml
# deploy/compose.proxy.yaml
services:
  converter:
    ports:
      - "127.0.0.1:8765:8080"
```

```bash
cd tools/assets/converter_ui/deploy
docker compose --env-file .env -f compose.yaml -f compose.proxy.yaml up -d --build converter
```

Proxy your HTTPS hostname to `http://127.0.0.1:8765`, preserve `Host`, and overwrite
`X-Forwarded-For` / `X-Forwarded-Proto` with values supplied by the proxy. The app
trusts exactly one proxy hop. Set proxy body limits at least as high as
`PARADISE_FILE_MIB`, allow long uploads/downloads, and turn off request buffering.
Use a dedicated hostname at `/`; serving beneath a URL prefix is not supported.
`PARADISE_DOMAIN` must exactly match the public hostname.

## Defaults and limits

| Setting | Default | Meaning |
| --- | --- | --- |
| `PARADISE_FILE_MIB` | 512 | Maximum bytes in one upload, in MiB |
| `PARADISE_UPLOAD_GIB` | 2 | Total uploaded data per workspace |
| `PARADISE_WORKSPACE_GIB` | 8 | Workspace budget including uploads, tools, staging and downloads |
| `PARADISE_TOTAL_GIB` | 40 | Total workspace storage budget |
| `PARADISE_MAX_FILES` | 5000 | Uploaded file count per workspace |
| `PARADISE_MAX_SESSIONS` | 100 | Stored browser workspaces |
| `PARADISE_MAX_JOBS` | 2 | Concurrent runs across all visitors |
| `PARADISE_WORKERS` | 2 | Converter subprocesses per run |
| `PARADISE_RETENTION_HOURS` | 24 | Cleanup after workspace inactivity |
| `PARADISE_JOB_MINUTES` | 30 | Maximum run duration |
| `PARADISE_SESSIONS_PER_HOUR` | 10 | New workspaces per client IP per hour |

Storage is checked before accepting uploads, conversions, and archive creation.
Running jobs that exceed time/storage limits are cancelled by a five-second monitor.
Each output file also has a 2 GiB hard process limit. Docker enforces memory, CPU and
process limits. The Docker volume is not itself a disk quota: place Docker's data on
a filesystem with an appropriate quota if you require a hard total disk ceiling.
The included proxy has an additional 2 GB request ceiling; adjust it if you raise
the application per-file limit beyond that.

There is one Gunicorn process with eight request threads and a shared scheduler.
**Do not increase Gunicorn's worker count or run multiple replicas against the same
data volume.** Scaling across servers would require an external queue and session store.
If all conversion slots are busy, visitors receive a retry message; their uploads stay.

## File handling

- Conversion jobs inherit a **Landlock filesystem sandbox**. They can read installed
  tools/libraries and their own uploads, and can write only their own workspace.
  They cannot read other visitors' data or the server's cookie-signing secret.
  The kernel must support Landlock (Ubuntu 24.04's standard kernel does). Conversion
  fails with a clear log message if the kernel or container runtime blocks it; do not
  disable the sandbox to make a public deployment work.
- The converter container runs as an unprivileged user with a read-only root, no
  Linux capabilities, no Docker socket, and no external network. Only the HTTPS proxy
  is published. Mount no host home directories, game installations or server secrets.
- Uploaded content is passed only to manifest-listed converters, never executed as
  a user-supplied script. Paths supplied by visitors resolve inside their own upload
  batches. Native pickers, arbitrary server paths, tool builds, and server shutdown
  are absent from the public API.
- Every run has a separate output folder. Re-running a conversion cannot change an
  earlier ZIP. Partial successes remain downloadable if other selected files fail.
- Files are deleted automatically after inactivity. **Delete my files** removes a
  visitor's workspace immediately when no operation is active. Clearing a browser's
  cookies loses access to that workspace; it will still expire normally.
- A restart preserves completed reports, uploads and session cookies. Active jobs
  become interrupted and can be inspected/restarted. Incomplete ZIPs are rebuilt.
- No game data is included in the image. Full game folders and proprietary reference
  files must come from the visitor's own uploads. The public UI does not expose any
  game dump stored on your server.

## Converter coverage

The manifest remains the format authority. This deployment supports routes whose
dependencies are available natively on Linux. Windows `fxc.exe` shader routes are
blocked with a desktop-converter message. Native Xbox One AEMS/CSIS routes that need
a separate companion dump remain blocked in hosted mode. Other missing companion
files appear as setup errors or converter diagnostics. This is not a promise that
every manifest route is portable; the first image build must complete on the target
architecture before deployment.

## Operations

From `tools/assets/converter_ui/deploy`:

```bash
docker compose --env-file .env logs --tail=100 -f converter
docker compose --env-file .env logs --tail=100 -f proxy
docker compose --env-file .env ps
docker compose --env-file .env down
```

`down` keeps data and certificate volumes. `/healthz` is the container liveness
endpoint. The `converter_data` volume holds a signing key and temporary user data;
the two Caddy volumes hold its configuration and certificates. Keep the signing key
across restarts for existing sessions to work. Request logs are not enabled by default;
application/container errors go to Docker logs with rotation configured in Compose.

Implementation: [Flask + Gunicorn](https://flask.palletsprojects.com/en/stable/deploying/gunicorn/),
[Docker Compose](https://docs.docker.com/reference/compose-file/services/), and
[Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
The worker filesystem policy uses [Linux Landlock](https://docs.kernel.org/userspace-api/landlock.html).

### Build status

The Ubuntu 24.04 x86-64 image builds locally with native YAP and Volatility. Compose
and Caddy configuration validation pass, and the hosted page loads in a browser.
Hosted conversion jobs and the ARM64 image have not been exercised yet.
