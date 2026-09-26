/* nanoPick — the page. No framework, no build step; fetch and innerHTML. */
"use strict";

const $ = (id) => document.getElementById(id);
const KIND_ICONS = {
  pictures: "🖼️", documents: "📄", music: "🎵", video: "🎬",
  archives: "🗜️", other: "📄",
};

let chosen = new Set();       // paths ticked for packing
let currentFile = null;       // the file being previewed
let searchTimer = null;

// ---------------------------------------------------------------- helpers
async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json().catch(() => ({ error: "The answer was not understandable." }));
  if (!response.ok) throw new Error(body.error || "Something went wrong.");
  return body;
}

function post(path, payload) {
  return api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
}

function toast(message, mood) {
  const box = document.createElement("div");
  box.className = "toast" + (mood ? " " + mood : "");
  box.innerHTML = '<button class="x">✕</button> ' + message;
  box.querySelector(".x").onclick = () => box.remove();
  $("toasts").appendChild(box);
  setTimeout(() => box.remove(), 7000);
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------------------------------------------------------------- search
async function runSearch() {
  const q = $("q").value.trim();
  const kind = $("kind").value;
  const when = $("when").value;
  const sort = $("sort").value;
  $("resultsHint").textContent = "Looking…";
  try {
    const data = await api("/api/search?q=" + encodeURIComponent(q) +
      "&kind=" + encodeURIComponent(kind) + "&when=" + encodeURIComponent(when) +
      "&sort=" + encodeURIComponent(sort));
    renderResults(data);
  } catch (err) {
    $("resultsHint").textContent = "";
    toast(String(err.message || err), "bad");
  }
}

function renderResults(data) {
  const box = $("results");
  box.innerHTML = "";
  $("emptyState").hidden = data.total > 0;
  $("resultsHint").textContent = data.total === 0 ? "" :
    data.total + " found — showing " + data.shown + " (looked at " + data.scanned +
    " files in " + data.took_text + ")";
  $("resultsTitle").textContent = data.total === 0 ? "What I found" :
    "What I found" + (data.total > data.shown ? " (the best " + data.shown + ")" : "");

  for (const file of data.results) {
    const row = document.createElement("div");
    row.className = "result" + (chosen.has(file.path) ? " chosen" : "");
    row.dataset.path = file.path;
    row.innerHTML =
      '<div class="icon">' + (KIND_ICONS[file.kind] || "📄") + "</div>" +
      '<div class="main"><div class="name">' + escapeHtml(file.name) + "</div>" +
      '<div class="facts">' + escapeHtml(file.what) + " · " + escapeHtml(file.when) +
      " · " + escapeHtml(file.size_text) + " · " + escapeHtml(file.folder) + "</div></div>" +
      '<div class="acts"><div class="tick" title="choose for packing">✓</div></div>';
    row.onclick = (event) => {
      if (event.target.classList.contains("tick")) return;
      showPreview(file.path);
    };
    row.querySelector(".tick").onclick = () => toggleChosen(file, row);
    box.appendChild(row);
  }
}

function toggleChosen(file, row) {
  if (chosen.has(file.path)) {
    chosen.delete(file.path);
    row.classList.remove("chosen");
  } else {
    chosen.add(file.path);
    row.classList.add("chosen");
  }
  const count = chosen.size;
  $("packPanel").hidden = count === 0;
  $("packTitle").textContent = "You have chosen " + count + " file" + (count === 1 ? "" : "s");
}

// ---------------------------------------------------------------- preview
async function showPreview(path) {
  try {
    const data = await api("/api/one?path=" + encodeURIComponent(path));
    currentFile = data.file;
    $("previewPanel").hidden = false;
    $("previewTitle").textContent = data.file.name;
    $("previewFacts").textContent =
      data.file.what + " · " + data.file.size_text + " · changed " + data.file.when +
      " · lives in " + data.file.folder;
    $("previewSaid").textContent = "";
    const body = $("previewBody");
    body.innerHTML = "";
    if (data.previewable) {
      if (/\.(png|jpe?g|gif|bmp|webp|svg|tiff?)$/i.test(data.file.name)) {
        const img = document.createElement("img");
        img.src = "/api/preview?path=" + encodeURIComponent(path);
        img.alt = data.file.name;
        body.appendChild(img);
      } else if (/\.(mp3|wav|ogg|m4a|flac|aac)$/i.test(data.file.name)) {
        const audio = document.createElement("audio");
        audio.controls = true;
        audio.src = "/api/preview?path=" + encodeURIComponent(path);
        body.appendChild(audio);
      } else if (/\.(mp4|mov|webm|mkv)$/i.test(data.file.name)) {
        const video = document.createElement("video");
        video.controls = true;
        video.src = "/api/preview?path=" + encodeURIComponent(path);
        body.appendChild(video);
      } else {
        const text = await fetch("/api/preview?path=" + encodeURIComponent(path)).then((r) => r.text());
        const pre = document.createElement("pre");
        pre.textContent = text;
        body.appendChild(pre);
      }
    } else {
      body.innerHTML = '<div class="nopreview">No preview for this kind of file.<br>Press “Open it” or “Show me the folder”.</div>';
    }
    $("previewPanel").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (err) {
    toast(String(err.message || err), "bad");
  }
}

// ---------------------------------------------------------------- actions
async function act(kind, payload) {
  try {
    const data = await post("/api/" + kind, payload);
    toast(data.said || "Done.", data.ok === false ? "bad" : "good");
    if (currentFile && kind !== "open") $("previewSaid").textContent = data.said || "";
  } catch (err) {
    toast(String(err.message || err), "bad");
  }
}

// ---------------------------------------------------------------- where modal
async function refreshWhere() {
  try {
    const data = await api("/api/settings");
    $("destInput").value = data.destination || "";
    $("packWhere").textContent = data.destination ?
      "The zip will be put in " + data.destination : "";
  } catch (err) { /* the page still works without it */ }
}

// ---------------------------------------------------------------- wiring
$("goBtn").onclick = runSearch;
$("q").addEventListener("keydown", (e) => { if (e.key === "Enter") runSearch(); });
$("kind").onchange = runSearch;
$("when").onchange = runSearch;
$("sort").onchange = runSearch;
$("q").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(runSearch, 350);
});

$("previewClose").onclick = () => { $("previewPanel").hidden = true; currentFile = null; };
$("previewOpen").onclick = () => currentFile && act("open", { path: currentFile.path });
$("previewReveal").onclick = () => currentFile && act("reveal", { path: currentFile.path });
$("previewCopy").onclick = () => currentFile && act("copy", { path: currentFile.path });

$("packBtn").onclick = () => {
  if (!chosen.size) return;
  act("pack", { paths: [...chosen] });
  chosen.clear();
  document.querySelectorAll(".result.chosen").forEach((r) => r.classList.remove("chosen"));
  $("packPanel").hidden = true;
};
$("packClear").onclick = () => {
  chosen.clear();
  document.querySelectorAll(".result.chosen").forEach((r) => r.classList.remove("chosen"));
  $("packPanel").hidden = true;
};

$("whereBtn").onclick = () => { refreshWhere(); $("whereModal").hidden = false; };
$("browseBtn").onclick = async () => {
  $("whereSaid").textContent = "A folder window is opening…";
  try {
    const data = await post("/api/pick-folder");
    if (data.ok) {
      $("destInput").value = data.path;
      await post("/api/destination", { destination: data.path });
      $("whereSaid").textContent = "Copies will go to " + data.path;
      refreshWhere();
    } else {
      $("whereSaid").textContent = data.why || "No folder was chosen.";
    }
  } catch (err) {
    $("whereSaid").textContent = String(err.message || err);
  }
};
$("destInput").addEventListener("change", async () => {
  try {
    await post("/api/destination", { destination: $("destInput").value.trim() });
    $("whereSaid").textContent = "Saved.";
    refreshWhere();
  } catch (err) {
    $("whereSaid").textContent = String(err.message || err);
  }
});

document.querySelectorAll("[data-close]").forEach((btn) => {
  btn.onclick = () => btn.closest(".backdrop").hidden = true;
});
$("helpBtn").onclick = () => { $("helpModal").hidden = false; };
document.querySelectorAll(".backdrop").forEach((backdrop) => {
  backdrop.onclick = (event) => { if (event.target === backdrop) backdrop.hidden = true; };
});

// ---------------------------------------------------------------- start
refreshWhere().then(() => runSearch());
