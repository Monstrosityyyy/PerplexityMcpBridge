const entitiesDiv = document.getElementById("entities");
const search = document.getElementById("search");
const statusNode = document.getElementById("status");
let entities = [];

async function refreshStatus() {
  const res = await fetch("/api/health");
  const json = await res.json();
  statusNode.textContent = JSON.stringify(json, null, 2);
}

function renderEntities() {
  const term = search.value.toLowerCase().trim();
  entitiesDiv.innerHTML = "";
  entities
    .filter((e) => e.entity_id.toLowerCase().includes(term))
    .forEach((entity) => {
      const row = document.createElement("label");
      row.innerHTML = `<input type="checkbox" data-entity="${entity.entity_id}" ${
        entity.selected ? "checked" : ""
      } /> ${entity.entity_id} (${entity.state})`;
      entitiesDiv.appendChild(row);
    });
}

document.getElementById("discover").addEventListener("click", async () => {
  const res = await fetch("/api/discover");
  const data = await res.json();
  const selected = new Set(data.selected);
  entities = data.entities.map((e) => ({ ...e, selected: selected.has(e.entity_id) }));
  renderEntities();
  await refreshStatus();
});

search.addEventListener("input", renderEntities);

document.getElementById("save").addEventListener("click", async () => {
  const selectedEntities = Array.from(
    entitiesDiv.querySelectorAll("input[type=checkbox]:checked")
  ).map((x) => x.dataset.entity);

  const body = {
    exposure_mode: document.getElementById("mode").value,
    selected_entities: selectedEntities,
    cloudflare_enabled: document.getElementById("cf-enabled").checked,
    cloudflare_mode: "token",
    cloudflare_tunnel_token: document.getElementById("cf-token").value || null,
    cloudflare_hostname: document.getElementById("cf-hostname").value || null,
    bearer_token: document.getElementById("bearer-token").value || null,
    require_cf_access_headers: document.getElementById("cf-access").checked,
    cf_access_client_id: document.getElementById("cf-id").value || null,
    cf_access_client_secret: document.getElementById("cf-secret").value || null,
  };
  const res = await fetch("/api/wizard/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  alert(res.ok ? `Saved. Token: ${data.masked_bearer_token}` : `Error: ${JSON.stringify(data)}`);
  await refreshStatus();
});

document.getElementById("launch").addEventListener("click", async () => {
  const res = await fetch("/api/launch", { method: "POST" });
  const data = await res.json();
  alert(res.ok ? "Tunnel started" : `Launch error: ${JSON.stringify(data)}`);
  await refreshStatus();
});

refreshStatus();
