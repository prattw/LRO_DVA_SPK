/**
 * Army Vantage preprocess — minimal client for the FastAPI backend.
 *
 * Same-origin: open http://127.0.0.1:8000/ui/ while the API is running (StaticFiles).
 * Cross-origin: set API_BASE to the API origin, e.g. `const API_BASE = "http://127.0.0.1:8000";`
 */
const API_BASE = "";

const UPLOAD_URL = `${API_BASE}/upload-and-process`;
const statusUrl = (jobId) => `${API_BASE}/status/${jobId}`;
const downloadUrl = (jobId) => `${API_BASE}/download/${jobId}`;

const POLL_MS = 600;
const MAX_POLL_ATTEMPTS = 600;

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const btnProcess = document.getElementById("btn-process");
const btnClear = document.getElementById("btn-clear");
const btnDownload = document.getElementById("btn-download");
const statusPhase = document.getElementById("status-phase");
const fieldJobId = document.getElementById("field-job-id");
const fieldFiles = document.getElementById("field-files");
const fieldChunks = document.getElementById("field-chunks");
const qualityBlock = document.getElementById("quality-block");
const errorBox = document.getElementById("error-box");

/** @type {File[]} */
let selectedFiles = [];
let pollTimer = null;
let pollAttempts = 0;

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
}

function clearError() {
  errorBox.hidden = true;
  errorBox.textContent = "";
}

function setPhase(state, text) {
  statusPhase.dataset.state = state;
  statusPhase.textContent = text;
}

function renderFileList() {
  fileList.innerHTML = "";
  selectedFiles.forEach((f) => {
    const li = document.createElement("li");
    li.textContent = `${f.name} (${formatBytes(f.size)})`;
    fileList.appendChild(li);
  });
  const has = selectedFiles.length > 0;
  btnProcess.disabled = !has;
  btnClear.disabled = !has;
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function addFiles(fileListLike) {
  const next = [...selectedFiles];
  for (const f of fileListLike) {
    const lower = f.name.toLowerCase();
    if (!/\.(pdf|docx|txt)$/.test(lower)) continue;
    next.push(f);
  }
  selectedFiles = next;
  renderFileList();
}

dropzone.addEventListener("click", () => fileInput.click());

dropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener("change", () => {
  addFiles(fileInput.files || []);
  fileInput.value = "";
});

["dragenter", "dragover"].forEach((ev) => {
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.add("dropzone--drag");
  });
});

["dragleave", "drop"].forEach((ev) => {
  dropzone.addEventListener(ev, (e) => {
    e.preventDefault();
    e.stopPropagation();
    dropzone.classList.remove("dropzone--drag");
  });
});

dropzone.addEventListener("drop", (e) => {
  const dt = e.dataTransfer;
  if (dt?.files?.length) addFiles(dt.files);
});

btnClear.addEventListener("click", () => {
  stopPolling();
  selectedFiles = [];
  renderFileList();
  resetDownload();
  fieldJobId.textContent = "—";
  fieldFiles.textContent = "—";
  fieldChunks.textContent = "—";
  qualityBlock.hidden = true;
  setPhase("idle", "Ready — add files above.");
  clearError();
});

function resetDownload() {
  btnDownload.hidden = true;
  btnDownload.removeAttribute("href");
}

/**
 * POST multipart: field name "files" for each file (FastAPI expects repeated "files").
 * @returns {Promise<{ job_id: string }>}
 */
async function startJob() {
  const formData = new FormData();
  selectedFiles.forEach((f) => formData.append("files", f, f.name));

  const res = await fetch(UPLOAD_URL, {
    method: "POST",
    body: formData,
  });

  if (res.status !== 202) {
    const text = await res.text();
    let detail = text;
    try {
      const j = JSON.parse(text);
      detail = j.detail != null ? JSON.stringify(j.detail) : text;
    } catch {
      /* use raw */
    }
    throw new Error(`Upload failed (${res.status}): ${detail}`);
  }

  return res.json();
}

/**
 * GET /status/{job_id}
 * @returns {Promise<object>}
 */
async function fetchStatus(jobId) {
  const res = await fetch(statusUrl(jobId));
  if (!res.ok) {
    const t = await res.text();
    throw new Error(`Status ${res.status}: ${t}`);
  }
  return res.json();
}

function stopPolling() {
  if (pollTimer != null) {
    clearTimeout(pollTimer);
    pollTimer = null;
  }
  pollAttempts = 0;
}

/**
 * Poll until status is complete or failed, or max attempts.
 * @param {string} jobId
 */
function schedulePoll(jobId) {
  stopPolling();

  const tick = async () => {
    pollAttempts += 1;
    if (pollAttempts > MAX_POLL_ATTEMPTS) {
      showError("Polling timed out. Check the server and job ID.");
      setPhase("error", "Timed out.");
      return;
    }

    try {
      const data = await fetchStatus(jobId);
      const st = data.status;
      const prog = data.progress || {};
      fieldJobId.textContent = jobId;
      fieldFiles.textContent =
        prog.files_total != null
          ? `${prog.files_processed ?? 0} / ${prog.files_total}`
          : "—";
      fieldChunks.textContent =
        data.chunks_created != null ? String(data.chunks_created) : "—";

      if (st === "processing" || st === "pending") {
        setPhase(
          "processing",
          `Processing… files ${prog.files_processed ?? 0}/${prog.files_total ?? "?"} · chunks ${data.chunks_created ?? 0}`,
        );
        pollTimer = setTimeout(tick, POLL_MS);
        return;
      }

      if (st === "complete") {
        setPhase("complete", "Complete — download the ZIP below.");
        if (data.quality_summary) {
          qualityBlock.textContent = JSON.stringify(data.quality_summary, null, 2);
          qualityBlock.hidden = false;
        } else {
          qualityBlock.hidden = true;
        }
        setupDownload(jobId);
        clearError();
        return;
      }

      if (st === "failed") {
        const msg = data.message || "Job failed.";
        const extra =
          data.errors?.length > 0 ? `\n\n${JSON.stringify(data.errors, null, 2)}` : "";
        setPhase("failed", `Failed: ${msg}`);
        showError(msg + extra);
        return;
      }

      setPhase("error", `Unknown status: ${st}`);
      showError(`Unknown status: ${st}`);
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      showError(msg);
      setPhase("error", "Error while polling.");
    }
  };

  pollTimer = setTimeout(tick, POLL_MS);
}

/**
 * GET /download/{job_id} as blob; wire anchor for Save As.
 * @param {string} jobId
 */
async function setupDownload(jobId) {
  resetDownload();
  try {
    const res = await fetch(downloadUrl(jobId));
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`Download failed (${res.status}): ${t}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    btnDownload.href = url;
    btnDownload.download = `vantage-job-${jobId}.zip`;
    btnDownload.hidden = false;
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showError(msg);
    btnDownload.hidden = true;
  }
}

btnProcess.addEventListener("click", async () => {
  clearError();
  resetDownload();
  qualityBlock.hidden = true;
  stopPolling();

  if (selectedFiles.length === 0) {
    showError("Add at least one file.");
    return;
  }

  btnProcess.disabled = true;
  setPhase("uploading", "Uploading and starting job…");

  try {
    const { job_id: jobId } = await startJob();
    fieldJobId.textContent = jobId;
    setPhase("processing", "Job started — waiting for progress…");
    clearError();

    const first = await fetchStatus(jobId);
    const prog = first.progress || {};
    fieldFiles.textContent =
      prog.files_total != null
        ? `${prog.files_processed ?? 0} / ${prog.files_total}`
        : "—";
    fieldChunks.textContent =
      first.chunks_created != null ? String(first.chunks_created) : "—";

    if (first.status === "complete") {
      setPhase("complete", "Complete — download the ZIP below.");
      if (first.quality_summary) {
        qualityBlock.textContent = JSON.stringify(first.quality_summary, null, 2);
        qualityBlock.hidden = false;
      }
      await setupDownload(jobId);
    } else if (first.status === "failed") {
      setPhase("failed", first.message || "Failed.");
      showError(first.message || "Job failed.");
    } else {
      schedulePoll(jobId);
    }
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    showError(msg);
    setPhase("error", "Upload or start failed.");
  } finally {
    btnProcess.disabled = selectedFiles.length === 0;
  }
});

renderFileList();
