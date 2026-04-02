(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /** Ingress-säker URL (respekterar &lt;base&gt;). */
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
      throw new Error(`Ogiltigt svar (${res.status})`);
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
  let currentStep = 0;

  function setStep(n) {
    currentStep = n;
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

  function renderStatusGrid(data) {
    const rows = [
      ["Home Assistant", data.ha_connected ? "Ansluten" : "Ej ansluten", data.ha_connected],
      ["Tunnel", data.tunnel_running ? "Körs" : "Stoppad", data.tunnel_running],
      ["Publik värd", data.tunnel_hostname || "—", null],
      ["Auth", data.auth_configured ? "Konfigurerad" : "Saknas", data.auth_configured],
      ["Exponerade entiteter", String(data.exposed_entity_count ?? "0"), null],
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
      statusGrid.innerHTML = `<div class="status-pill"><span>API</span><strong class="bad">Fel</strong></div>`;
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
          <div class="entity-meta">Tillstånd: ${entity.state ?? "—"}</div>
        </div>
      `;
      entitiesDiv.appendChild(row);
    });

    entityCount.textContent = `${filtered.length} av ${entities.length} visas`;
    entitiesHint.hidden = entities.length > 0;
  }

  search.addEventListener("input", renderEntities);

  $("#discover").addEventListener("click", async () => {
    try {
      toast("Hämtar entiteter…");
      const data = await fetchJson("api/discover");
      const selected = new Set(data.selected || []);
      entities = (data.entities || []).map((e) => ({
        ...e,
        selected: selected.has(e.entity_id),
      }));
      renderEntities();
      await refreshStatus();
      toast(`Hämtade ${entities.length} entiteter.`);
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
    };

    try {
      const data = await fetchJson("api/wizard/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      toast(`Sparat. Token (maskad): ${data.masked_bearer_token || "ok"}`);
      updateMcpUrlPreview();
      await refreshStatus();
    } catch (e) {
      toast(e.message || String(e), true);
    }
  });

  $("#launch").addEventListener("click", async () => {
    try {
      await fetchJson("api/launch", { method: "POST" });
      toast("Tunnel startad (om token och inställningar stämmer).");
      await refreshStatus();
    } catch (e) {
      toast(e.message || String(e), true);
    }
  });

  $("#btn-refresh-status").addEventListener("click", () => {
    refreshStatus();
    toast("Status uppdaterad.");
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
