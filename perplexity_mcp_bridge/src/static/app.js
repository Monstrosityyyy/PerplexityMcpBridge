(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /** Resolves API paths correctly behind Home Assistant ingress (&lt;base&gt;). */
  function apiUrl(path) {
    return new URL(path.replace(/^\//, ""), document.baseURI).href;
  }

  const toastEl = $("#toast");
  let toastTimer;

  function toast(msg, isError = false) {
    toastEl.textContent = msg;
    toastEl.hidden = false;
    toastEl.classList.toggle("error", isError);
    toastEl.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toastEl.classList.remove("is-visible");
      setTimeout(() => {
        toastEl.hidden = true;
      }, 400);
    }, 4200);
  }

  async function fetchJson(path, opts) {
    const res = await fetch(apiUrl(path), opts);
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      throw new Error(`Invalid response (${res.status})`);
    }
    if (!res.ok) {
      const detail = data.detail || data.message || JSON.stringify(data);
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  const entitiesDiv = $("#entities");
  const search = $("#search");
  const statusNode = $("#status");
  const statusGrid = $("#status-grid");
  const entityCount = $("#entity-count");
  const entitiesHint = $("#entities-hint");
  let entities = [];

  function setStep(n) {
    $$(".step").forEach((btn) => {
      const step = Number(btn.dataset.step);
      const on = step === n;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-current", on ? "step" : "false");
    });
    $$(".panel").forEach((panel) => {
      const p = Number(panel.dataset.panel);
      panel.hidden = p !== n;
      panel.classList.toggle("is-active", p === n);
    });
  }

  $$(".step").forEach((btn) => {
    btn.addEventListener("click", () => setStep(Number(btn.dataset.step)));
  });

  $$("[data-goto]").forEach((btn) => {
    btn.addEventListener("click", () => setStep(Number(btn.dataset.goto)));
  });

  function modeLabel(mode) {
    if (mode === "long_lived_token") return "Long-lived token";
    if (mode === "supervisor") return "Supervisor";
    return "None";
  }

  function renderStatusGrid(data) {
    const base = data.ha_api_base || "—";
    const rows = [
      ["Home Assistant", data.ha_connected ? "Connected" : "Not connected", data.ha_connected],
      ["HA API mode", modeLabel(data.ha_connection_mode), null],
      ["HA API base", base, null],
      ["Tunnel", data.tunnel_running ? "Running" : "Stopped", data.tunnel_running],
      ["Public host", data.tunnel_hostname || "—", null],
      ["MCP bearer auth", data.auth_configured ? "Set" : "Missing", data.auth_configured],
      ["Exposed entities", String(data.exposed_entity_count ?? "0"), null],
    ];
    statusGrid.innerHTML = rows
      .map(
        ([label, val, ok]) => `
      <div class="status-pill">
        <span>${label}</span>
        <strong class="${ok === true ? "ok" : ok === false ? "bad" : ""}">${val}</strong>
      </div>`
      )
      .join("");
  }

  async function refreshStatus() {
    try {
      const json = await fetchJson("api/health");
      statusNode.textContent = JSON.stringify(json, null, 2);
      renderStatusGrid(json);
    } catch (e) {
      statusNode.textContent = String(e.message || e);
      statusGrid.innerHTML = `<div class="status-pill"><span>API</span><strong class="bad">Error</strong></div>`;
    }
  }

  function renderEntities() {
    const term = search.value.toLowerCase().trim();
    const filtered = entities.filter((e) => {
      const id = (e.entity_id || "").toLowerCase();
      const dom = id.split(".")[0] || "";
      return id.includes(term) || dom.includes(term);
    });

    entitiesDiv.innerHTML = "";
    filtered.forEach((entity) => {
      const row = document.createElement("label");
      row.className = "entity-row";
      const id = entity.entity_id || "";
      row.innerHTML = `
        <input type="checkbox" data-entity="${id}" ${entity.selected ? "checked" : ""} />
        <div>
          <div class="entity-id">${id}</div>
          <div class="entity-meta">State: ${entity.state ?? "—"}</div>
        </div>
      `;
      entitiesDiv.appendChild(row);
    });

    entityCount.textContent = `${filtered.length} of ${entities.length} shown`;
    entitiesHint.hidden = entities.length > 0;
  }

  search.addEventListener("input", renderEntities);

  $("#discover").addEventListener("click", async () => {
    try {
      toast("Loading entities…");
      const data = await fetchJson("api/discover");
      const selected = new Set(data.selected || []);
      entities = (data.entities || []).map((e) => ({
        ...e,
        selected: selected.has(e.entity_id),
      }));
      renderEntities();
      await refreshStatus();
      toast(`Loaded ${entities.length} entities.`);
    } catch (e) {
      toast(e.message || String(e), true);
    }
  });

  $("#select-all").addEventListener("click", () => {
    entitiesDiv.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      cb.checked = true;
    });
  });

  $("#deselect-all").addEventListener("click", () => {
    entitiesDiv.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      cb.checked = false;
    });
  });

  $("#save").addEventListener("click", async () => {
    const selectedEntities = Array.from(entitiesDiv.querySelectorAll('input[type="checkbox"]:checked')).map(
      (x) => x.dataset.entity
    );

    const haLlat = ($("#ha-llat").value || "").trim();

    const body = {
      exposure_mode: $("#mode").value,
      selected_entities: selectedEntities,
      cloudflare_enabled: $("#cf-enabled").checked,
      cloudflare_mode: "token",
      cloudflare_tunnel_token: $("#cf-token").value || null,
      cloudflare_hostname: $("#cf-hostname").value || null,
      bearer_token: $("#bearer-token").value || null,
      require_cf_access_headers: $("#cf-access").checked,
      cf_access_client_id: $("#cf-id").value || null,
      cf_access_client_secret: $("#cf-secret").value || null,
      home_assistant_long_lived_token: haLlat || null,
    };

    try {
      const data = await fetchJson("api/wizard/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast(`Saved. MCP token (masked): ${data.masked_bearer_token || "ok"}`);
      updateMcpUrlPreview();
      await refreshStatus();
    } catch (e) {
      toast(e.message || String(e), true);
    }
  });

  $("#launch").addEventListener("click", async () => {
    try {
      await fetchJson("api/launch", { method: "POST" });
      toast("Tunnel start requested (requires valid Cloudflare settings).");
      await refreshStatus();
    } catch (e) {
      toast(e.message || String(e), true);
    }
  });

  $("#btn-refresh-status").addEventListener("click", () => {
    refreshStatus();
    toast("Status refreshed.");
  });

  function updateMcpUrlPreview() {
    const host = ($("#cf-hostname").value || "").trim();
    const box = $("#mcp-url-box");
    const code = $("#mcp-url");
    if (host) {
      const url = host.startsWith("http") ? host : `https://${host}`;
      code.textContent = `${url.replace(/\/$/, "")}/mcp`;
      box.hidden = false;
    } else {
      box.hidden = true;
    }
  }

  $("#cf-hostname").addEventListener("input", updateMcpUrlPreview);

  setStep(0);
  refreshStatus();
  updateMcpUrlPreview();
})();
