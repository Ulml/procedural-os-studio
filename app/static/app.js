const $ = (id) => document.getElementById(id);
let current = null;
let agents = [];

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.tab === name));
  $("tab-chat").style.display = name === "chat" ? "grid" : "none";
  $("tab-instruction").classList.toggle("on", name === "instruction");
  $("tab-memory").classList.toggle("on", name === "memory");
}

function bubble(role, text, meta) {
  const el = document.createElement("div");
  el.className = "bubble " + role;
  el.innerHTML = (meta ? `<div class="meta">${meta}</div>` : "") + `<div>${escapeHtml(text)}</div>`;
  $("chat").appendChild(el);
  $("chat").scrollTop = $("chat").scrollHeight;
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&")
    .replaceAll("<", "<")
    .replaceAll(">", ">")
    .replaceAll("\n", "<br>");
}

async function refreshAgents() {
  const data = await api("/api/agents");
  agents = data.agents;
  $("agent-list").innerHTML = "";
  agents.forEach((a) => {
    const el = document.createElement("div");
    el.className = "agent" + (current === a.slug ? " active" : "");
    el.innerHTML = `<div class="name">${a.name}</div><div class="desc">${a.description.slice(0, 90)}</div>`;
    el.onclick = () => selectAgent(a.slug);
    $("agent-list").appendChild(el);
  });
}

async function selectAgent(slug) {
  current = slug;
  const a = await api("/api/agents/" + slug);
  $("title").textContent = a.name;
  $("desc").value = a.description;
  $("body").value = a.body;
  $("files").textContent = "Fichiers : " + (a.files || []).join(" · ");
  $("l3path").value = (a.files || []).find((f) => f.startsWith("scripts/")) || "scripts/run.py";
  $("l3content").value = "";
  $("chat").innerHTML = "";
  bubble("assistant", a.description, "L1 · " + a.slug);
  await refreshMemory();
  refreshAgents();
}

async function refreshMemory() {
  if (!current) return;
  const data = await api("/api/agents/" + current + "/memory");
  $("memory-list").innerHTML = "";
  data.items.forEach((item) => {
    const row = document.createElement("label");
    row.className = "memory-item" + (item.applied ? " applied" : "");
    row.innerHTML = `<input type="checkbox" data-id="${item.id}" ${item.selected && !item.applied ? "checked" : ""} ${item.applied ? "disabled" : ""}/>
      <div><strong>${item.applied ? "intégrée" : "en attente"}</strong> · ${escapeHtml(item.created_at)}<div>${escapeHtml(item.text)}</div></div>`;
    row.querySelector("input").onchange = async (ev) => {
      await api("/api/memory/select", { method: "POST", body: { ids: [item.id], selected: ev.target.checked } });
    };
    $("memory-list").appendChild(row);
  });
}

document.querySelectorAll(".tab").forEach((t) => (t.onclick = () => showTab(t.dataset.tab)));
$("new-agent").onclick = () => $("modal").classList.add("on");
$("cancel-create").onclick = () => $("modal").classList.remove("on");

$("create-form").onsubmit = async (ev) => {
  ev.preventDefault();
  const f = ev.target;
  const created = await api("/api/agents", {
    method: "POST",
    body: {
      name: f.name.value,
      natural_language: f.nl.value,
      use_llm: true,
      example: {
        input_kind: f.in_kind.value,
        output_kind: f.out_kind.value,
        input_text: f.in_kind.value === "prompt" ? f.in_val.value : "",
        output_text: f.out_kind.value === "prompt" ? f.out_val.value : "",
        input_ref: f.in_kind.value !== "prompt" ? f.in_val.value : "",
        output_ref: f.out_kind.value !== "prompt" ? f.out_val.value : "",
      },
    },
  });
  $("modal").classList.remove("on");
  f.reset();
  await refreshAgents();
  await selectAgent(created.slug);
  showTab("instruction");
};

$("save-instruction").onclick = async () => {
  if (!current) return;
  await api("/api/agents/" + current + "/instruction", {
    method: "POST",
    body: {
      description: $("desc").value,
      body: $("body").value,
      l3_path: $("l3path").value,
      l3_content: $("l3content").value,
    },
  });
  await selectAgent(current);
};

$("apply-memory").onclick = async () => {
  if (!current) return;
  const res = await api("/api/agents/" + current + "/memory/apply", { method: "POST", body: {} });
  $("body").value = res.body || $("body").value;
  await refreshMemory();
  showTab("instruction");
};

$("apply-push").onclick = async () => {
  if (!current) return;
  const res = await api("/api/agents/" + current + "/memory/apply", { method: "POST", body: { push_github: true } });
  bubble("assistant", JSON.stringify(res.github || res, null, 2), "github");
  await refreshMemory();
};

$("composer").onsubmit = async (ev) => {
  ev.preventDefault();
  if (!current) return;
  const text = $("prompt").value.trim();
  if (!text) return;
  $("prompt").value = "";
  bubble("user", text);
  const res = await api("/api/agents/" + current + "/chat", { method: "POST", body: { message: text } });
  if (res.kind === "memory") {
    bubble("assistant", "Correction enregistrée dans l’onglet Mémoire.", "mémoire");
    await refreshMemory();
    return;
  }
  let msg = res.answer || "";
  (res.artifacts || []).forEach((a) => {
    msg += `\nPièce : ${a.name} → /api/artifacts/${a.name}`;
  });
  bubble("assistant", msg, res.offline ? "runner hors-ligne" : "runner");
};

refreshAgents();
