# Beszel

Monitoring zasobów: CPU, RAM, dysk, sieć i temperatura [[castle]] oraz RAM
i CPU każdego kontenera. Odpowiada na pytanie „dlaczego pada?” i „czy
`mem_limit` są dobrze dobrane?”. Druga połowa kroku 7, obok [[uptime-kuma]]
(„czy działa?”).

#usługa #monitoring

## Dlaczego akurat to

Prometheus + Grafana są świadomie odrzucone na Pi 4 (`CLAUDE.md`): kilka
kontenerów i kilkaset MiB RAM. Beszel to jedna binarka huba (PocketBase/SQLite)
i jedna agenta, razem kilkanaście MiB. Ma historię metryk, alerty i widok
kontenerów. Netdata było alternatywą, ale zużywa znacznie więcej RAM.

## Podstawowe dane

| | |
|---|---|
| Host | [[castle]] |
| URL | `https://beszel.home.figielak.dev` przez [[caddy]] |
| Stack | `stacks/beszel/`, trzy kontenery |
| Obrazy | `henrygd/beszel:0.20.0`, `henrygd/beszel-agent:0.20.0`, `lscr.io/linuxserver/socket-proxy:3.4.4-r0-ls98` (arm64 potwierdzony w Docker Hub) |
| Porty | hub 8090 **tylko w sieci `proxy`**; proxy **`127.0.0.1:2375`**; agent żadnego (unix socket) |
| Dane | `/srv/homelab/data/beszel/hub` (baza huba), `/srv/homelab/data/beszel/socket` (socket agenta); właściciel root |
| RAM | `mem_limit` 128 + 64 + 64 MiB; zmierzone ~12 + 5 + 18 MiB **tuż po starcie** (2026-09-24), do powtórzenia w stanie ustalonym |

## Architektura

```
hub (beszel, sieć proxy) ──unix socket──▶ agent (network_mode: host)
                                            │
                                            └─tcp 127.0.0.1:2375─▶ socket proxy ──▶ docker.sock
```

- **Hub ↔ agent przez unix socket** we wspólnym katalogu. Agent nie ma żadnego
  portu sieciowego, a hub uwierzytelnia się kluczem SSH (publiczny w `.env` agenta).
- **Agent w `network_mode: host`.** To wyjątek od zasady, bo w sieci bridge
  agent widziałby tylko interfejs własnego kontenera, a nie `wlan0` / `tailscale0`.
- **Socket proxy zamiast `docker.sock`.** Dostęp do `docker.sock`, także `:ro`,
  to root na hoście: przez API da się uruchomić kontener z zamontowanym `/`.
  Proxy przepuszcza tylko GET na endpointy, których używa agent 0.20.0
  (sprawdzone w `agent/docker.go`: `/containers/json`, `/containers/{id}/json`,
  `/containers/{id}/stats`, `/version`, `/info`). `POST=0`, `ALLOW_LOGS=0`.
- **Proxy na `127.0.0.1`**, bo agent w trybie host nie dosięgnie kontenera
  po nazwie. Z LAN-u ani z tailnetu proxy jest niedostępne.

## Zależności

- **Zależy od:** [[caddy]] (dostęp do panelu), sieci `proxy`, Dockera.
- **Zależy od niej:** nic. Awaria Beszela oznacza brak metryk, ale żadna
  usługa od niego nie zależy.

## Co backupować

`/srv/homelab/data/beszel/hub/` zawiera historię metryk, konto admina,
ustawienia alertów i klucz SSH huba. Utrata nie jest krytyczna: tracisz
historię, a konfigurację odtworzysz ręcznie w kilka minut. Jeśli odtworzysz
hub bez backupu, wygeneruje **nowy klucz**, więc trzeba zaktualizować
`BESZEL_AGENT_KEY` w `.env`. SQLite jak w [[mealie]]: backup przy zatrzymanym
kontenerze albo przez `sqlite3 .backup`.

Katalogu `socket/` nie backupujemy, bo agent tworzy socket przy starcie.

## Procedura odtworzenia od zera

Dwie fazy: agent potrzebuje klucza, który hub generuje przy pierwszym starcie.

```bash
# 1. repo i katalogi danych (sudo) — kontenery dzialaja jako root
cd /opt/homelab && git pull --ff-only
sudo mkdir -p /srv/homelab/data/beszel/{hub,socket}

# 1a. ODTWORZENIE Z BACKUPU — przed pierwszym startem
#     sudo cp -a <backup>/beszel/hub/. /srv/homelab/data/beszel/hub/

# 2. hub i proxy
cd /opt/homelab/stacks/beszel
cp .env.example .env
docker compose config --quiet
docker compose up -d beszel beszel-socket-proxy
```

Blok `@beszel` w `stacks/caddy/config/Caddyfile` już jest. Reload Caddy:
`docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`
(w katalogu `stacks/caddy`).

W UI (`https://beszel.home.figielak.dev`):

1. Załóż konto admina (menedżer haseł: „Homelab Beszel”). Przy odtworzeniu
   z backupu konto już istnieje.
2. **Add system**: Name `castle`, Host / IP `/beszel_socket/beszel.sock`.
3. Skopiuj klucz publiczny.

```bash
# 3. agent
cd /opt/homelab/stacks/beszel
nano .env      # BESZEL_AGENT_KEY="ssh-ed25519 AAAA..." — w cudzyslowie
docker compose up -d
```

### Weryfikacja

```bash
docker compose ps                  # trzy kontenery healthy
sudo ss -tlnp | grep 2375          # tylko 127.0.0.1:2375

# proxy przepuszcza odczyt, blokuje reszte
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:2375/containers/json                 # 200
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:2375/containers/mealie/restart # 403
curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:2375/containers/caddy/logs?stdout=1"  # 403
```

W UI: `castle` zielony, widoczne kontenery, temperatura i dysk (~117 GB, `/` na SSD).

## Konfiguracja w UI

Powiadomienia i alerty żyją w bazie huba, **nie w Git**. Ta sekcja to jedyna
kopia poza bazą. Aktualizuj ją przy każdej zmianie w UI.

- **Powiadomienia** (Settings → Notifications): `ntfy://ntfy.sh/<temat>`,
  ten sam temat co w [[uptime-kuma]]. Nazwa tematu działa jak hasło:
  menedżer haseł, „Homelab ntfy”.
- **Alerty dla `castle`** (ikona dzwonka na liście systemów):

| Alert | Próg | Dlaczego |
|---|---|---|
| Disk | 80% | pobrania [[metube]] leżą na SSD systemu; pełny dysk to awaria całego hosta, a z nim DNS domu |
| Status | host przestał raportować | Kuma działa na tym samym hoście i jego śmierci nie zgłosi |

## Znane problemy i ograniczenia

- **Inspect kontenera ujawnia jego zmienne środowiskowe.** `CONTAINERS=1`
  przepuszcza `/containers/{id}/json`, a tam są m.in. `CF_API_TOKEN` Caddy.
  Kto ma dostęp do proxy (localhost) albo do panelu Beszela, może go odczytać.
  Akceptowalne, bo każdy z dostępem do localhost i tak jest w grupie `docker`,
  ale **konto admina Beszela chroni też ten token**.
- **Podgląd logów kontenerów w UI nie działa**: świadomie, `ALLOW_LOGS=0`,
  bo logi mogą zawierać sekrety.
- **Brak S.M.A.R.T.** SSD. Wymaga dostępu agenta do `/dev/sda` i podwyższonych
  uprawnień, a SSD siedzi za mostkiem USB-SATA (ASM1153). Na razie pominięte.
- **Pomiary RAM są z pierwszych minut.** Do powtórzenia po kilku dniach
  (`docker stats --no-stream beszel beszel-agent beszel-socket-proxy`).

## Log zmian

- 2026-09-24 — stack utworzony (`0.20.0` + socket proxy `3.4.4`), wystawiony
  przez [[caddy]] pod `beszel.home.figielak.dev`; ograniczenia proxy
  zweryfikowane (GET 200, POST i logi 403); temperatura i dysk widoczne
- 2026-09-25 — powiadomienia ntfy, alerty Disk 80% i Status dla `castle`
