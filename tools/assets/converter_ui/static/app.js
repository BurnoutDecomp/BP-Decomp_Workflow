"use strict";

const $ = id => document.getElementById(id);
const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;
const activeStates = new Set(["preparing", "running", "cancelling"]);
const readyStates = new Set(["ready", "replace"]);
const doneStates = new Set(["converted", "copied", "generated", "current"]);
const attentionStates = new Set(["blocked", "unsupported", "failed"]);
const labels = {ready:"Ready",replace:"Will replace",current:"Up to date",exists:"Output exists",unsupported:"Unsupported",blocked:"Needs setup",skipped:"Not needed",running:"Converting",queued:"Queued",converted:"Converted",copied:"Copied",generated:"Generated",failed:"Failed",cancelled:"Cancelled"};
const state = {sources:[], plan:null, selected:new Set(), filter:"all", page:0, busy:false,
  catalog:[], tools:[], job:null, cursor:0, polling:false, logs:[], options:null, dirty:false, hosted:false, limits:{}};
const fragment = location.hash.slice(1);
const suppliedToken = /^[A-Za-z0-9_-]{40,}$/.test(fragment) ? fragment : "";
let token = suppliedToken || sessionStorage.getItem("paradise-token") || "";
if (suppliedToken) {
  sessionStorage.setItem("paradise-token", token);
  history.replaceState(null, "", location.pathname);
}
let toastTimer;
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("toast").hidden = true, 6500);
}
function bytes(n) {
  if (n == null) return "—";
  if (n === 0) return "0 B";
  const i = Math.min(4, Math.floor(Math.log(n) / Math.log(1024)));
  return `${(n / 1024 ** i).toFixed(i === 0 ? 0 : 1)} ${["B","KiB","MiB","GiB","TiB"][i]}`;
}
function duration(s) {
  s = Math.max(0, Math.floor(s));
  return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${Math.floor(s / 3600)}h ${Math.floor(s % 3600 / 60)}m`;
}
function statusBadge(status) {
  const cls = attentionStates.has(status) ? status === "blocked" ? "warn" : "error" : status === "replace" ? "warn" : ["running","queued"].includes(status) ? "running" : doneStates.has(status) || status === "ready" ? "" : "neutral";
  return `<span class="status ${cls}">${esc(labels[status] || status.replaceAll("_", " "))}</span>`;
}
async function api(path, data, method = data == null ? "GET" : "POST") {
  const response = await fetch(path, {method, headers:{"X-Asset-Token":token, ...(data != null ? {"Content-Type":"application/json"} : {})}, body:data == null ? undefined : JSON.stringify(data)});
  const result = await response.json().catch(()=>({error:`Server request failed (${response.status}). Try again or contact the operator.`}));
  if (!response.ok) throw new Error(result.error || `Request failed (${response.status})`);
  return result;
}
function downloadBlob(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
async function downloadRun(id, type) {
  try {
    const response = await fetch(`/api/${type}/${id}`, {headers:{"X-Asset-Token":token}});
    if (!response.ok) throw new Error((await response.json()).error);
    downloadBlob(await response.blob(), `paradise-${type}-${id.slice(0,8)}.${type === "report" ? "json" : "log"}`);
  } catch (e) { toast(e.message); }
}
function options() {
  return {output:$("output").value.trim(), jobs:Number($("jobs").value), keep_layout:$("keepLayout").checked,
    skip_current:$("skipCurrent").checked, replace:$("replaceExisting").checked, generate:$("generate").checked,
    converter:$("converter").value, source_root:$("sourceRoot").value.trim(), xb1_root:$("xb1Root").value.trim()};
}
function applyOptions(o) {
  $("output").value = o.output || "";
  $("jobs").value = o.jobs || 2;
  $("keepLayout").checked = o.keep_layout !== false;
  $("skipCurrent").checked = o.skip_current !== false;
  $("replaceExisting").checked = Boolean(o.replace);
  $("generate").checked = o.generate !== false;
  $("converter").value = o.converter || "auto";
  $("sourceRoot").value = o.source_root || "";
  $("xb1Root").value = o.xb1_root || "";
}
function persist() {
  localStorage.setItem("paradise-preferences", JSON.stringify(options()));
  localStorage.setItem("paradise-sources", JSON.stringify(state.sources.slice(0,50)));
  if (state.catalog.length) api("/api/preferences", {options:options(), sources:state.sources,
    theme:document.documentElement.dataset.theme}).catch(e => toast("Could not save preferences: " + e.message));
}
function running() { return state.job && activeStates.has(state.job.status); }
function busy(value) {
  state.busy = value;
  updateControls();
  renderSources();
}
function dirty() {
  persist();
  state.dirty = true;
  if (state.plan) notice("Settings or sources changed. Inspect files to refresh the preview.");
  updateControls();
}
function notice(text = "", type = "") {
  $("scanNotice").textContent = text;
  $("scanNotice").className = "notice " + type;
  $("scanNotice").hidden = !text;
}
function updateControls() {
  const locked = state.busy || running();
  for (const id of ["chooseFiles","chooseFolder","uploadFiles","uploadFolder","addPaths","browseOutput","output","jobs","keepLayout","skipCurrent","replaceExisting","generate","converter","sourceRoot","xb1Root"])
    $(id).disabled = locked;
  $("inspectButton").disabled = locked || !state.sources.length;
  $("clearButton").disabled = locked || (!state.sources.length && !state.plan);
  $("convertButton").disabled = locked || state.dirty || !state.plan || !state.selected.size;
  $("exportPlan").disabled = !state.plan;
  $("inspectButton").classList.toggle("busy", state.busy);
  $("selectAll").disabled = locked;
  $("convertHint").textContent = running() ? (state.hosted ? "Your conversion is running on the server" : "Your conversion is running locally") : state.busy ? "Preparing your selection…" : state.dirty && state.plan ? "Inspect files to update the preview" : state.selected.size ? `${state.selected.size} selected · Ctrl+Enter to convert` : state.plan ? "Select ready files from the queue" : "Add files to get started";
}
function renderSources() {
  $("sourceList").innerHTML = state.sources.map((p,i) => `<div class="source-chip">${icon("file")}<span title="${esc(p)}">${esc(p)}</span><button data-remove="${i}" aria-label="Remove ${esc(p)}" ${running() || state.busy ? "disabled" : ""}>×</button></div>`).join("");
}
async function addSources(paths) {
  if (!paths.length) return;
  state.sources = [...new Set([...state.sources, ...paths])];
  renderSources();
  dirty();
  await inspect();
}
async function pick(kind, destination = false) {
  if (state.hosted) {
    if (!destination) $(kind === "files" ? "fileInput" : "folderInput").click();
    return;
  }
  busy(true);
  toast("Choose a " + (kind === "files" ? "file in the file chooser" : "folder in the folder chooser") + ".");
  try {
    const result = await api("/api/pick", {kind});
    busy(false);
    if (destination && result.paths.length) {
      $("output").value = result.paths[0];
      dirty();
    } else if (!destination) await addSources(result.paths);
  } catch (e) { toast(e.message); } finally { busy(false); }
}
async function inspect() {
  if (!state.sources.length || running()) return;
  busy(true);
  notice("Inspecting file headers and checking converters…");
  try {
    const result = await api("/api/scan", {sources:state.sources, options:options()});
    state.plan = result;
    state.selected = new Set(result.rows.filter(r => readyStates.has(r.status)).map(r => r.id));
    state.page = 0;
    state.dirty = false;
    $("freeSpace").textContent = bytes(result.free_bytes);
    const attention = result.rows.filter(r => attentionStates.has(r.status)).length;
    const messages = [];
    if (!result.rows.length) messages.push("This folder has no files to process.");
    if (attention) messages.push(`${attention} file${attention === 1 ? " needs" : "s need"} attention. Open a row for details; ready files can still be converted.`);
    if (result.warnings.length) messages.push(result.warnings.slice(0,4).join("\n") + (result.warnings.length > 4 ? `\n… and ${result.warnings.length - 4} more; see the exported plan.` : ""));
    notice(messages.join("\n"), attention ? "warn" : "");
    renderQueue();
    persist();
  } catch (e) {
    state.dirty = true;
    notice(e.message, "error");
    toast("Could not inspect the selection. See the message above the queue.");
  } finally { busy(false); }
}
function filteredRows() {
  const query = $("search").value.trim().toLowerCase();
  return (state.plan?.rows || []).filter(r => {
    const filter = state.filter;
    return (filter === "all" || filter === "ready" && readyStates.has(r.status) || filter === "attention" && attentionStates.has(r.status) || filter === "done" && doneStates.has(r.status)) && (!query || `${r.name} ${r.relative} ${r.rule} ${r.status}`.toLowerCase().includes(query));
  });
}
function renderQueue() {
  const all = state.plan?.rows || [];
  const rows = filteredRows();
  const pages = Math.max(1, Math.ceil(rows.length / 50));
  state.page = Math.max(0, Math.min(state.page, pages - 1));
  const visible = rows.slice(state.page * 50, (state.page + 1) * 50);
  $("queueCount").textContent = all.length;
  $("queueEmpty").hidden = all.length > 0;
  $("tableWrap").hidden = all.length === 0;
  $("queueBody").innerHTML = visible.map(r => `<tr>
    <td class="check-cell"><input type="checkbox" data-select="${r.id}" aria-label="Select ${esc(r.name)}" ${state.selected.has(r.id) ? "checked" : ""} ${!readyStates.has(r.status) || running() ? "disabled" : ""}></td>
    <td><div class="filename">${icon(r.kind === "generate" ? "settings" : "file")}<div><button class="file-link" data-detail="${r.id}" title="${esc(r.relative)}">${esc(r.name)}</button><small>${esc(r.rule === "catch-all" ? "No converter found" : r.rule.replaceAll("-", " "))}</small></div></div></td>
    <td class="size-cell">${bytes(r.size)}</td><td>${statusBadge(r.status)}</td>
    <td><button class="icon-button" data-detail="${r.id}" title="File details" aria-label="Details for ${esc(r.name)}">${icon("info")}</button></td></tr>`).join("") || `<tr><td colspan="5" class="quiet">No files match this filter.</td></tr>`;
  const ready = all.filter(r => readyStates.has(r.status));
  $("selectAll").checked = ready.length > 0 && ready.every(r => state.selected.has(r.id));
  $("selectAll").indeterminate = ready.some(r => state.selected.has(r.id)) && !$("selectAll").checked;
  $("selectionInfo").textContent = `${state.selected.size} selected${all.length ? ` of ${all.length} files` : ""}`;
  $("pageInfo").textContent = rows.length ? `${state.page * 50 + 1}–${Math.min((state.page + 1) * 50,rows.length)} of ${rows.length}` : "0 files";
  $("prevPage").disabled = state.page === 0;
  $("nextPage").disabled = state.page >= pages - 1;
  $("readyCount").textContent = `${state.selected.size} file${state.selected.size === 1 ? "" : "s"}`;
  $("totalSize").textContent = bytes(all.filter(r => state.selected.has(r.id)).reduce((s,r) => s + r.size, 0));
  updateControls();
}
function modal(title, html) {
  $("modalTitle").textContent = title;
  $("modalBody").innerHTML = html;
  if (!$("modal").open) $("modal").showModal();
}
function details(id) {
  const row = state.plan?.rows.find(r => r.id === id);
  if (!row) return;
  const rule = state.catalog.find(r => r.id === row.rule);
  modal(row.name, `<dl class="detail-grid"><dt>Status</dt><dd>${statusBadge(row.status)}</dd><dt>Source</dt><dd>${esc(row.source)}</dd><dt>Output</dt><dd>${esc(row.output || row.output_relative)}</dd><dt>Detected format</dt><dd>${row.platform === 2 ? "Xbox 360 / big endian" : row.platform === 4 ? "PC / platform 4 container" : row.platform == null ? "Not a bnd2 container" : `Platform ${row.platform}`}</dd><dt>Resources</dt><dd>${esc(row.resources || 0)} · ${(row.types || []).map(t => "0x" + t.toString(16).toUpperCase()).join(", ") || "—"}</dd><dt>Converter</dt><dd>${esc(row.tool || row.action)}</dd><dt>Detection</dt><dd>${esc(row.detection || "Game folder support files")}</dd></dl><div class="detail-note">${esc(row.detail || "Ready for conversion")}</div>${rule ? `<details><summary>About this format</summary><div class="detail-note">${esc(rule.description)}</div></details>` : ""}<button class="button small" id="copyDetails">Copy file details</button>`);
  $("copyDetails").onclick = () => navigator.clipboard.writeText(JSON.stringify(row, null, 2)).then(() => toast("File details copied.")).catch(() => toast("Clipboard access unavailable; use Export plan."));
}
function formatGuide() {
  modal("Supported formats", `<p class="quiet">The project manifest is the source of truth. Some files are copied as-is; unsupported families are listed explicitly.</p><input class="guide-search" id="guideSearch" type="search" placeholder="Search formats, extensions, or converters…" aria-label="Search supported formats"><div id="guideEntries"></div>`);
  const render = () => {
    const term = $("guideSearch").value.toLowerCase();
    $("guideEntries").innerHTML = state.catalog.filter(r => `${r.name} ${r.patterns.join(" ")} ${r.tool}`.toLowerCase().includes(term)).map(r => `<details class="guide-entry"><summary><span>${esc(r.name)}</span>${statusBadge(r.action === "unhandled" ? "unsupported" : r.action === "skip" ? "skipped" : r.action === "copy" ? "copied" : "ready")}</summary><code>${esc(r.patterns.join(" · ") || "Generated from the original executable")}</code><code>${esc(r.tool || r.action)}</code><p>${esc(r.description)}</p></details>`).join("");
  };
  $("guideSearch").oninput = render;
  render();
}
function toolDialog() {
  if (state.hosted) {
    modal("Server converters", state.tools.map(t => `<div class="tool-row"><span>${esc(t.name)}</span>${statusBadge(t.ready ? "ready" : "blocked")}</div>`).join("") + `<p class="setup-note">Converters are installed by the server operator. Files that need an unavailable converter or companion data show a setup message in the queue. Shader conversion using Windows fxc.exe is available in the desktop tool.</p>`);
    return;
  }
  modal("Converter tools", state.tools.map(t => `<div class="tool-row"><span>${esc(t.name)}</span>${statusBadge(t.ready ? "ready" : "blocked")}</div>`).join("") + `<p class="setup-note">The interface needs only Python 3.11+. Asset conversion uses the project’s YAP and Volatility binaries. Build them here if they are missing. The build requires Visual Studio, CMake, Qt6, and the .NET SDK, as described in BUILD.md.</p><button class="button primary" id="buildTools">Build converter tools</button><p class="setup-note">This runs the existing <code>build tools</code> command and shows its output in Run activity.</p>`);
  $("buildTools").disabled = Boolean(running());
  $("buildTools").onclick = async () => {
    $("modal").close();
    try { await beginJob(await api("/api/setup", {})); } catch(e) { toast(e.message); }
  };
}
async function start() {
  if (!state.plan || state.dirty || running() || !state.selected.size) return;
  busy(true);
  try {
    await beginJob(await api("/api/start", {plan:state.plan.id, selected:[...state.selected]}));
  } catch(e) { toast(e.message); } finally { busy(false); }
}
async function beginJob(job) {
  state.job = job;
  state.cursor = 0;
  state.logs = [];
  $("activity").textContent = "";
  $("activityCard").hidden = false;
  $("progressCard").hidden = false;
  $("liveBadge").textContent = "LIVE";
  if (job.rows?.length && state.plan) for (const row of job.rows) {
    const target = state.plan.rows.find(r => r.id === row.id);
    if (target) Object.assign(target, row);
  }
  state.selected.clear();
  renderQueue();
  renderSources();
  renderProgress();
  if (!state.polling) poll();
}
function applyJob(snapshot) {
  state.job = {...state.job, ...snapshot};
  for (const event of snapshot.events || []) {
    if (event.event === "row" && state.plan) {
      const row = state.plan.rows.find(r => r.id === event.id);
      if (row) Object.assign(row, {status:event.status, detail:event.detail});
    }
    if (event.event === "log" || event.event === "fatal") {
      const stamp = new Date(event.time * 1000).toLocaleTimeString([], {hour12:false});
      state.logs.push(`${stamp}  ${event.message}`);
    }
  }
  for (const update of snapshot.rows || []) {
    const row = state.plan?.rows.find(r => r.id === update.id);
    if (row) Object.assign(row, update);
  }
  state.logs = state.logs.slice(-400);
  const log = $("activity");
  const stick = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
  log.textContent = state.logs.join("\n");
  if (stick) log.scrollTop = log.scrollHeight;
  state.cursor = snapshot.sequence;
  renderQueue();
  renderProgress();
}
async function poll() {
  state.polling = true;
  try {
    while (running()) {
      try {
        const snapshot = await api(`/api/job/${state.job.id}?after=${state.cursor}`);
        $("connectionError").hidden = true;
        applyJob(snapshot);
        if (!activeStates.has(snapshot.status)) {
          $("liveBadge").textContent = "FINISHED";
          renderSources();
          await loadHistory();
          if (snapshot.kind === "setup") {
            const bootstrap = await api("/api/bootstrap");
            state.tools = bootstrap.tools;
            renderTools();
            if (state.sources.length) await inspect();
          }
          toast(snapshot.status === "completed" ? "Conversion complete. Your files are ready." : snapshot.status === "cancelled" ? "Run cancelled. Completed files were kept." : "Run finished with issues. Check the queue and log.");
          break;
        }
      } catch (e) {
        $("connectionError").textContent = (state.hosted ? "Connection interrupted. Reconnecting to the server… " : "Connection interrupted. Keep the launcher window open. Retrying… ") + e.message;
        $("connectionError").hidden = false;
      }
      await new Promise(resolve => setTimeout(resolve, 900));
    }
  } finally { state.polling = false; updateControls(); }
}
function renderProgress() {
  const job = state.job;
  if (!job) return;
  const counts = job.counts || {};
  const finished = Object.entries(counts).filter(([k]) => !["queued","running","ready","replace"].includes(k)).reduce((s,[,n])=>s+n,0);
  const percent = job.total ? Math.round(finished / job.total * 100) : activeStates.has(job.status) ? 0 : 100;
  $("progressBar").value = percent;
  $("progressPercent").textContent = `${percent}%`;
  $("progressTitle").textContent = ({preparing:"Preparing converters…",running:job.kind === "setup" ? "Building converter tools" : "Converting your assets",cancelling:"Cancelling…",completed:"All selected files processed",completed_with_errors:"Finished with issues",failed:"Run failed",cancelled:"Run cancelled"})[job.status] || job.status;
  $("progressCount").textContent = job.kind === "setup" ? "Converter toolchain" : `${finished} of ${job.total} files processed`;
  $("elapsed").textContent = duration((job.ended || Date.now()/1000) - job.started);
  const failed = counts.failed || 0;
  $("progressDetail").textContent = job.error || (failed ? `${failed} file${failed===1?"":"s"} failed. Open file details or save the run log for the reason.` : activeStates.has(job.status) ? "Each output is checked before being saved." : state.hosted ? "Download the converted files as a ZIP. Your originals on this device are unchanged." : "Your source files are preserved. Reports are saved beside the output.");
  $("cancelButton").hidden = !activeStates.has(job.status);
  $("cancelButton").disabled = job.status === "cancelling";
  $("openOutput").hidden = activeStates.has(job.status);
  $("downloadReport").hidden = activeStates.has(job.status);
  $("retryButton").hidden = activeStates.has(job.status) || !failed || !state.sources.length;
}
async function loadHistory() {
  try {
    const data = await api("/api/history");
    $("historyList").innerHTML = data.runs.slice(0,10).map(r => `<div class="history-entry">${icon("clock")}<div><strong>${esc(r.label)}</strong><small title="${esc(state.hosted ? "Private to this browser session" : r.output)}">${esc(new Date(r.started*1000).toLocaleString([], {dateStyle:"medium",timeStyle:"short"}))}${state.hosted ? " · Your workspace" : ` · ${esc(r.output)}`}</small></div>${statusBadge(r.status)}<div class="history-actions"><button class="text-button" data-report="${r.id}">Report</button><button class="text-button" data-open="${r.id}" ${activeStates.has(r.status)?"disabled":""}>${state.hosted ? "Download ZIP" : "Open"}</button></div></div>`).join("") || '<p class="quiet">Your conversion history will appear here.</p>';
  } catch(e) { toast(e.message); }
}
async function openOutput(id) {
  try {
    if (state.hosted) {
      toast("Preparing your download…");
      const data = await api(`/api/archive/${id}`, {});
      const link = document.createElement("a");
      link.href = data.url;
      link.download = `paradise-converted-${id.slice(0,8)}.zip`;
      link.click();
      toast("Your download is starting.");
    } else await api("/api/open-output", {id});
  } catch(e) { toast(e.message); }
}
async function retry() {
  const failedSources = new Set((state.plan?.rows || []).filter(r => r.status === "failed").map(r => r.source));
  await inspect();
  if (!state.dirty && state.plan) {
    state.selected = new Set(state.plan.rows.filter(r => failedSources.has(r.source) && readyStates.has(r.status)).map(r => r.id));
    renderQueue();
    if (state.selected.size) await start(); else toast("No failed files are ready to retry. Check their setup details.");
  }
}
async function upload(files) {
  if (!files.length || running() || state.busy) return;
  busy(true);
  $("uploadStatus").hidden = false;
  try {
    if (files.length > (state.limits.max_files || 30000)) throw new Error(`Select no more than ${state.limits.max_files || 30000} files at once.`);
    if (state.hosted && files.some(({file}) => file.size > state.limits.file_bytes)) throw new Error(`A file exceeds the ${bytes(state.limits.file_bytes)} upload limit.`);
    if (state.hosted && files.reduce((sum,{file})=>sum+file.size,0) > state.limits.upload_bytes) throw new Error(`This selection exceeds the ${bytes(state.limits.upload_bytes)} upload allowance.`);
    const batch = await api("/api/upload-batch", {});
    let total = 0;
    for (let i=0; i<files.length; i++) {
      const {file,path} = files[i];
      $("uploadStatus").textContent = `Adding ${i+1} of ${files.length}: ${path} (${bytes(total)} ${state.hosted ? "uploaded" : "staged locally"})`;
      const response = await fetch(`/api/upload?batch=${batch.batch}&path=${encodeURIComponent(path)}`, {method:"PUT",headers:{"X-Asset-Token":token},body:file});
      if (!response.ok) throw new Error((await response.json().catch(()=>({error:`Upload failed (${response.status}). The server or proxy may have rejected the file.`}))).error);
      total += file.size;
    }
    busy(false);
    $("uploadStatus").textContent = state.hosted ? `${files.length} file(s) uploaded to your workspace. Ready to inspect.` : `${files.length} file(s) added. Browser drops use a temporary local copy. Choose files / Choose folder reads local paths directly.`;
    await addSources([batch.root]);
  } catch(e) { $("uploadStatus").textContent = e.message; toast(e.message); } finally { busy(false); }
}
async function droppedEntries(entries, fallback) {
  const result = [];
  async function walk(entry, prefix="") {
    if (result.length >= 30000) throw new Error("Too many files. Choose a smaller folder.");
    if (entry.isFile) {
      const file = await new Promise((resolve,reject)=>entry.file(resolve,reject));
      result.push({file,path:prefix+entry.name});
    } else if (entry.isDirectory) {
      const reader = entry.createReader();
      while (true) {
        const batch = await new Promise((resolve,reject)=>reader.readEntries(resolve,reject));
        if (!batch.length) break;
        for (const child of batch) await walk(child, prefix+entry.name+"/");
      }
    }
  }
  if (entries.length) for (const entry of entries) await walk(entry);
  else for (const file of fallback) result.push({file,path:file.webkitRelativePath || file.name});
  return result;
}
function renderTools() {
  const missing = state.tools.filter(t => !t.ready).length;
  $("toolStatus").textContent = missing ? `${missing} tool${missing === 1 ? "" : "s"} need setup` : "Toolchain ready";
}
function theme(value) {
  document.documentElement.dataset.theme = value;
  $("themeButton").querySelector("span").textContent = value === "dark" ? "Switch to light" : "Switch to dark";
  $("themeButton").setAttribute("aria-label", value === "dark" ? "Switch to light theme" : "Switch to dark theme");
  localStorage.setItem("paradise-theme", value);
  if (state.catalog.length) persist();
}

$("chooseFiles").onclick = () => pick("files");
$("chooseFolder").onclick = () => pick("folder");
$("browseOutput").onclick = () => pick("folder", true);
$("pasteToggle").onclick = () => { $("pathPanel").hidden = !$("pathPanel").hidden; if (!$("pathPanel").hidden) $("paths").focus(); };
$("addPaths").onclick = async () => { const paths = $("paths").value.split(/\r?\n/).map(p=>p.trim().replace(/^"|"$/g,"")).filter(Boolean); $("paths").value=""; await addSources(paths); };
$("sourceList").onclick = e => { const b=e.target.closest("[data-remove]"); if(b && !running() && !state.busy){state.sources.splice(Number(b.dataset.remove),1);renderSources();dirty();} };
$("inspectButton").onclick = inspect;
$("convertButton").onclick = start;
$("clearButton").onclick = () => { state.sources=[];state.plan=null;state.selected.clear();state.dirty=false;notice();renderSources();renderQueue();persist(); };
$("search").oninput = () => { state.page=0;renderQueue(); };
document.querySelectorAll("[data-filter]").forEach(b=>b.onclick=()=>{state.filter=b.dataset.filter;state.page=0;document.querySelectorAll("[data-filter]").forEach(x=>x.classList.toggle("active",x===b));renderQueue();});
$("prevPage").onclick=()=>{state.page--;renderQueue();};
$("nextPage").onclick=()=>{state.page++;renderQueue();};
$("selectAll").onchange=()=>{for(const r of state.plan?.rows || [])if(readyStates.has(r.status))$("selectAll").checked?state.selected.add(r.id):state.selected.delete(r.id);renderQueue();};
$("queueBody").onchange=e=>{if(e.target.dataset.select){e.target.checked?state.selected.add(e.target.dataset.select):state.selected.delete(e.target.dataset.select);renderQueue();}};
$("queueBody").onclick=e=>{const b=e.target.closest("[data-detail]");if(b)details(b.dataset.detail);};
$("exportPlan").onclick=()=>downloadBlob(new Blob([JSON.stringify(state.plan,null,2)],{type:"application/json"}),"paradise-conversion-plan.json");
for(const id of ["output","jobs","keepLayout","skipCurrent","replaceExisting","generate","converter","sourceRoot","xb1Root"])$(id).onchange=dirty;
$("closeModal").onclick=()=>$("modal").close();
$("modal").onclick=e=>{if(e.target===$("modal")){const r=$("modal").getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)$("modal").close();}};
$("guideButton").onclick=$("tipGuide").onclick=formatGuide;
$("toolsButton").onclick=toolDialog;
$("themeButton").onclick=()=>theme(document.documentElement.dataset.theme==="dark"?"light":"dark");
$("quitButton").onclick=()=>{
  if (state.hosted) {
    modal("Delete my files", `<p>Delete all uploads, converted files, and reports in this browser's server workspace? Download any results you want to keep first.</p><button id="deleteWorkspace" class="button danger" ${running()?"disabled":""}>Delete my files</button>${running()?"<p>Cancel the active run first.</p>":""}`);
    $("deleteWorkspace").onclick=async()=>{try{await api("/api/delete-workspace",{});location.reload();}catch(e){toast(e.message);}};
    return;
  }
  modal("Quit converter", `<p>Stop the local server${running() ? " and cancel the active run" : ""}? Completed output files and saved reports are kept.</p><button id="stopServer" class="button danger">Stop server</button>`);
  $("stopServer").onclick=async()=>{
    try{
      await api("/api/shutdown",{});
      if(state.job)state.job.status="cancelled";
      $("modal").close();
      busy(true);
      $("connectionError").textContent="Server stopped. Launch convert-assets.cmd to start a new session.";
      $("connectionError").hidden=false;
    }catch(e){toast(e.message);}
  };
};
$("refreshHistory").onclick=loadHistory;
$("historyList").onclick=e=>{const b=e.target.closest("button");if(b?.dataset.report)downloadRun(b.dataset.report,"report");if(b?.dataset.open)openOutput(b.dataset.open);};
$("downloadReport").onclick=()=>downloadRun(state.job.id,"report");
$("downloadLog").onclick=()=>downloadRun(state.job.id,"log");
$("openOutput").onclick=()=>openOutput(state.job.id);
$("retryButton").onclick=retry;
$("cancelButton").onclick=async()=>{try{await api("/api/cancel",{id:state.job.id});state.job.status="cancelling";renderProgress();}catch(e){toast(e.message);}};
$("uploadFiles").onclick=()=>$("fileInput").click();
$("uploadFolder").onclick=()=>$("folderInput").click();
for(const id of ["fileInput","folderInput"])$(id).onchange=async e=>{await upload([...e.target.files].map(file=>({file,path:file.webkitRelativePath||file.name})));e.target.value="";};
let dragDepth=0;
document.addEventListener("dragenter",e=>{if([...e.dataTransfer.types].includes("Files")){e.preventDefault();dragDepth++;if(!running()&&!state.busy)$("dropOverlay").hidden=false;}});
document.addEventListener("dragover",e=>{if([...e.dataTransfer.types].includes("Files"))e.preventDefault();});
document.addEventListener("dragleave",()=>{dragDepth=Math.max(0,dragDepth-1);if(!dragDepth)$("dropOverlay").hidden=true;});
document.addEventListener("drop",async e=>{e.preventDefault();dragDepth=0;$("dropOverlay").hidden=true;if(running()||state.busy)return;const entries=[...e.dataTransfer.items].filter(i=>i.kind==="file").map(i=>i.webkitGetAsEntry?.()).filter(Boolean);const fallback=[...e.dataTransfer.files];try{await upload(await droppedEntries(entries,fallback));}catch(err){toast(err.message);}});
document.addEventListener("keydown",e=>{if(e.key==="/"&&!/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)&&!$("modal").open){e.preventDefault();$("search").focus();}if((e.ctrlKey||e.metaKey)&&e.key==="Enter"&&!$("convertButton").disabled){e.preventDefault();start();}});
window.addEventListener("beforeunload",e=>{if(running()){e.preventDefault();e.returnValue="";}});
setInterval(()=>{if(running())renderProgress();},1000);

function hostedMode(data) {
  state.hosted = data.mode === "hosted";
  if (!state.hosted) return;
  token = data.token;
  state.limits = data.limits;
  document.documentElement.dataset.mode = "hosted";
  document.querySelectorAll("[data-local-only]").forEach(el=>el.hidden=true);
  $("sidebarNote").innerHTML = `<span class="local-dot"></span> Your browser's workspace<p>Upload, convert, and download.<br>Files expire after ${data.limits.retention_hours} hours of inactivity.</p>`;
  $("sessionLabel").textContent = "Hosted session";
  $("quitButton").setAttribute("aria-label", "Delete my server files");
  $("quitButton").innerHTML = `${icon("close")}<span>Delete my files</span>`;
  $("openOutput").innerHTML = `${icon("download")}Download ZIP`;
  $("hostedNotice").hidden = false;
  $("hostedNotice").textContent = `Files are uploaded to this server. Up to ${bytes(data.limits.file_bytes)} per file, ${bytes(data.limits.upload_bytes)} of uploads per workspace, and ${data.limits.max_files.toLocaleString()} files. Download your results within ${data.limits.retention_hours} hours of inactivity. No account needed.`;
  $("hostedOutput").hidden = false;
  $("spaceLabel").textContent = "Workspace space";
  for (const option of [...$("jobs").options]) if (Number(option.value) > data.limits.workers) option.remove();
}
(async function boot(){
  theme(localStorage.getItem("paradise-theme") || "light");
  try {
    const data=await api("/api/bootstrap");
    hostedMode(data);
    state.catalog=data.catalog;state.tools=data.tools;
    $("formatCount").textContent=data.catalog.filter(r=>r.action==="convert").length;
    $("converter").insertAdjacentHTML("beforeend",data.catalog.filter(r=>r.action==="convert").map(r=>`<option value="${esc(r.id)}">${esc(r.name)}</option>`).join(""));
    let saved=data.preferences?.options || {};state.sources=data.preferences?.sources || [];
    applyOptions({...data.defaults,...saved});
    theme(data.preferences?.theme || localStorage.getItem("paradise-theme") || "light");
    renderSources();renderTools();renderQueue();await loadHistory();
    if(data.active){
      const job=await api(`/api/job/${data.active}?after=0`);
      state.plan={id:null,rows:job.rows||[]};
      state.dirty=true;
      await beginJob(job);
    }else if(state.sources.length){toast("Your last source selection is restored. Inspect files when you’re ready.");}
  }catch(e){$("connectionError").textContent=e.message+" Reload the page to reconnect. Desktop users can reopen convert-assets.cmd.";$("connectionError").hidden=false;}
})();
