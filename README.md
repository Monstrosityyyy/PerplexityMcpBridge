# Perplexity MCP Bridge — Home Assistant add-on repository

Detta är ett **Home Assistant add-on repository** (inte en enskild add-on-mapp). Du lägger till hela GitHub-URL:en under **Inställningar → Tillägg → Tilläggsbutik → ⋮ → Repositories** och installerar sedan add-on:en **Perplexity MCP Bridge** från butiken.

## Installera i Home Assistant

1. Pusha detta repo till GitHub (eller annan git-värd som Supervisor kan nå).
2. I `repository.yaml` i roten: byt `YOUR_USERNAME` och repo-URL mot din riktiga GitHub-adress, committa och pusha.
3. I Home Assistant: **Inställningar → Tillägg → Tilläggsbutik** → öppna menyn (⋮) → **Repositories**.
4. Klistra in **rot-URL:en till GitHub-repot** (t.ex. `https://github.com/dittkonto/perplexity-mcp-bridge-ha`) i fältet **Add** och klicka **+ Add**.
5. Uppdatera sidan om det behövs. Under **Lokala tillägg** ska **Perplexity MCP Bridge** visas.
6. Öppna add-on:en, installera och starta den.

## Repo-struktur (krav från Home Assistant)

| Sökväg | Syfte |
|--------|--------|
| `repository.yaml` | Krävs i roten: talar om för Supervisor att detta är ett app-/add-on-repository (namn, URL, underhållare). |
| `perplexity_mcp_bridge/` | En undermapp **per add-on** med `config.yaml`, `Dockerfile`, kod, m.m. |

Mappnamnet `perplexity_mcp_bridge` matchar `slug` i add-onens `config.yaml`.

## Dokumentation för själva add-on:en

Se [perplexity_mcp_bridge/README.md](perplexity_mcp_bridge/README.md) för arkitektur, säkerhet, MCP-URL, Cloudflare och felsökning.

## Utveckling lokalt

Bygg och testa add-on:en som vanligt från mappen `perplexity_mcp_bridge/` om du kör lokal Supervisor/build; roten används bara för att HA ska kunna lista add-on:en när du lägger till repository-URL:en.
