# Homelab

Konfiguracja domowego homelaba na jednym hoście. Wszystko, czego potrzeba
do odbudowy infrastruktury od zera: to repozytorium + kopia danych.

**Host:** `castle` — Raspberry Pi 4, 4 GB RAM, ARM64, Raspberry Pi OS Lite
(Debian trixie), adres `192.168.10.10`.

## Od czego zacząć

1. [`docs/hosts/castle.md`](docs/hosts/castle.md) — **najważniejszy plik**.
   Stan faktyczny hosta, rejestr portów, budżet RAM, dług techniczny, log zmian.
   Przeczytaj, zanim cokolwiek dołożysz.
2. `docs/services/<nazwa>.md` — notatka na usługę, z procedurą odtworzenia.
3. `CLAUDE.md` — zasady projektu i konwencje.

## Struktura

```
docs/            vault Obsidiana — hosts/, services/, decisions/
stacks/          jeden katalog = jeden docker-compose.yml
hosts/castle/    pliki systemowe hosta (ścieżka w repo = ścieżka na hoście)
scripts/         narzędzia, m.in. collect-host-state.sh
```

## Zasady, które trzymają to w kupie

- Konfiguracja w Git, **dane poza Git** (`/srv/homelab/data/<stack>/`)
- Bind mounts, nigdy named volumes
- Obrazy pinowane do wersji, nigdy `:latest`
- Sekrety w `.env` (w `.gitignore`), w repo tylko `.env.example`
- Usługi wystawiane wyłącznie przez Caddy; kontenery nie publikują portów

## Uruchomione usługi

| Usługa | Adres | Notatka |
|---|---|---|
| AdGuard Home | `adguard.home.figielak.dev` | [docs](docs/services/adguard.md) |
| Caddy | — (reverse proxy) | [docs](docs/services/caddy.md) |
| Mealie | `mealie.home.figielak.dev` | [docs](docs/services/mealie.md) |
| Tailscale | — (zdalny dostęp, na hoście) | [docs](docs/services/tailscale.md) |
| Uptime Kuma | `uptime-kuma.home.figielak.dev` | [docs](docs/services/uptime-kuma.md) |
| Beszel | `beszel.home.figielak.dev` | [docs](docs/services/beszel.md) |
| Dashboard agent | — (push na figielak.dev) | [docs](docs/services/dashboard-agent.md) |
| Calibre-Web | `calibre-web.home.figielak.dev` | [docs](docs/services/calibre-web.md) |

Domena wewnętrzna `*.home.figielak.dev` rozwiązywana przez AdGuard (DNS rewrite),
certyfikat wildcard od Let's Encrypt przez DNS-01 w Cloudflare. W Cloudflare
jest też publiczny wildcard `*.home → 192.168.10.10` (adres prywatny, więc
z internetu nieosiągalny). Poza domem dostęp daje Tailscale.

## Dostarczanie zmian na hosta

Autorstwo zmian wyłącznie na laptopie. Host aktualizuje się przez:

```bash
cd /opt/homelab && git pull --ff-only
```

Deploy key jest read-only — Pi nigdy nie pushuje.

## Stan

Kroki 1–5 oraz 7–8 kolejności wdrażania zamknięte (baza, repo, AdGuard, Caddy,
Mealie, monitoring, Tailscale). Krok 6 (backup) czeka na HDD.

**Otwarte ryzyko: brak jakiegokolwiek backupu.** Szczegóły w długu technicznym
notatki hosta.
