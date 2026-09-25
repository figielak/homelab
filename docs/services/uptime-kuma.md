# Uptime Kuma

Monitoring dostępności. Co minutę sprawdza usługi i DNS, a przy awarii
i powrocie wysyła push na telefon przez ntfy. Pilnuje też wygasania
certyfikatu wildcard.

Pierwsza połowa kroku 7. Druga to [[beszel]] (zasoby hosta).

#usługa #monitoring

## Dlaczego akurat to

Odpowiada na pytanie „czy działa?” z perspektywy użytkownika, a nie
„ile zużywa?”. Jeden kontener, SQLite, konfiguracja przez UI, wbudowane
powiadomienia (w tym ntfy) i alerty o certyfikatach. Prometheus + Grafana są
świadomie odrzucone na Pi 4 (`CLAUDE.md`), a Healthchecks.io czy UptimeRobot
nie widzą usług w sieci domowej.

## Podstawowe dane

| | |
|---|---|
| Host | [[castle]] |
| URL | `https://uptime-kuma.home.figielak.dev` przez [[caddy]] |
| Port | 3001 **wyłącznie wewnątrz sieci `proxy`**, nic na hoście |
| Dane | `/srv/homelab/data/uptime-kuma/` (właściciel UID 1000) |
| Stack | `stacks/uptime-kuma/` |
| Obraz | `louislam/uptime-kuma:2.5.5-slim-rootless` (arm64 potwierdzony w Docker Hub) |
| RAM | `mem_limit` 256 MiB, **zmierzone ~122 MiB** (2026-09-24, 4 monitory) |
| Baza | SQLite, `kuma.db` w katalogu danych |

### Dlaczego wariant `slim-rootless`

- **slim:** bez wbudowanego MariaDB i Chromium. Zostajemy przy SQLite, a typu
  monitora „Browser Engine” nie używamy. Obraz jest ~300–400 MB mniejszy.
- **rootless:** działa jako `node` (UID 1000). Traci tylko monitoring
  kontenerów przez `docker.sock`, którego **świadomie nie montujemy**:
  dostęp do gniazda to root na hoście. Stan usług widać przez HTTP.

`UPTIME_KUMA_SQLITE_SINGLE_CONNECTION` nie jest ustawione. W kodzie 2.5.5
pojedyncze połączenie jest domyślne, a zmienna służy tylko do jego wyłączenia.

## Konfiguracja w UI

Monitory i powiadomienia żyją w SQLite, **nie w Git**. Ta sekcja to jedyna
kopia konfiguracji poza bazą. Aktualizuj ją przy każdej zmianie w UI.

### Powiadomienia

- ntfy, serwer `https://ntfy.sh`, „Default enabled” (włączone dla każdego nowego monitora)
- **Nazwa tematu działa jak hasło**: kto ją zna, czyta alerty. Jest w menedżerze
  haseł jako „Homelab ntfy” i nigdy nie trafia do repo.
- Konto admina: menedżer haseł, „Homelab Uptime Kuma”
- API key `dashboard-agent` (Settings → API Keys, bez wygasania) do `/metrics`:
  menedżer haseł, „Homelab Kuma API key”

### Monitory

Interwał 60 s, 2–3 ponowienia przed alertem, żeby pojedynczy błąd Wi-Fi
nie budził alarmu.

| Nazwa | Typ | Ustawienia | Co wykrywa |
|---|---|---|---|
| Mealie | HTTP(s) | `https://mealie.home.figielak.dev`, alert o wygasaniu certyfikatu | Caddy + TLS + Mealie; certyfikat wildcard |
| AdGuard panel | HTTP(s) | `https://adguard.home.figielak.dev` | panel AdGuarda przez Caddy |
| Beszel | HTTP(s) | `https://beszel.home.figielak.dev` | hub [[beszel]] przez Caddy |
| Uptime Kuma | HTTP(s) | `https://uptime-kuma.home.figielak.dev` | panel Kumy przez Caddy; własnej śmierci nie zgłosi (patrz niżej) |
| AdGuard DNS | DNS | `example.com`, resolver `192.168.10.10:53` | AdGuard odpowiada jako resolver domu |
| AdGuard rewrite | DNS | `mealie.home.figielak.dev`, resolver `192.168.10.10:53` | działa rewrite `*.home.figielak.dev` |
| Dashboard agent | Push | interwał 60 s, 2 ponowienia; URL w `.env` [[dashboard-agent]] | agent przestał wysyłać dane na stronę |

**Dlaczego osobny monitor rewrite'u:** kontener rozwiązuje nazwy przez resolver
hosta (8.8.8.8/1.1.1.1), który dostaje odpowiedź z publicznego wildcardu
w Cloudflare. Monitory HTTP przechodzą więc nawet wtedy, gdy rewrite
w AdGuardzie jest zepsuty.

**Nowy stack = nowy monitor** tutaj i w tabeli.

**Nazwy monitorów są częścią kontraktu.** [[dashboard-agent]] mapuje je
w `config.json` na usługi z prywatnego dashboardu. Zmiana nazwy monitora
w UI wymaga zmiany w `config.json`, inaczej kropka na stronie zrobi się szara.

## Zależności

- **Zależy od:** [[caddy]] (dostęp do panelu), sieci `proxy`, internetu
  (ntfy.sh, resolver hosta).
- **Zależy od niej:** nic. Awaria Kumy oznacza brak alertów, ale żadna usługa
  od niej nie zależy.

## Co backupować

Katalog `/srv/homelab/data/uptime-kuma/`: monitory, historia, powiadomienia.
Przy SQLite obowiązuje to samo co w [[mealie]]: kopia działającej bazy przez
`cp` może być niespójna. Zatrzymaj kontener albo użyj `sqlite3 .backup`.

Utrata danych nie jest krytyczna: tracisz historię dostępności, a konfigurację
odtworzysz ręcznie z tabeli wyżej.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalog danych — wlascicielem musi byc UID 1000 (obraz rootless)
sudo mkdir -p /srv/homelab/data/uptime-kuma
sudo chown 1000:1000 /srv/homelab/data/uptime-kuma

# 3. ODTWORZENIE Z BACKUPU — przed pierwszym startem
#    sudo cp -a <backup>/uptime-kuma/. /srv/homelab/data/uptime-kuma/
#    sudo chown -R 1000:1000 /srv/homelab/data/uptime-kuma

# 4. start
cd /opt/homelab/stacks/uptime-kuma
cp .env.example .env
docker compose config --quiet && docker compose up -d
docker compose ps    # przez pierwsze ~3 min "starting" — start_period 180s
```

Blok `@uptime-kuma` w `stacks/caddy/config/Caddyfile` już jest. Po zmianie
w `Caddyfile`:
`docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile`
(w katalogu `stacks/caddy`).

Bez backupu: załóż konto admina przy pierwszym wejściu, dodaj ntfy i monitory
według sekcji „Konfiguracja w UI”.

### Weryfikacja

```bash
docker stats --no-stream uptime-kuma   # limit 256MiB egzekwowany
docker stop mealie                     # w ciagu ~3 min push "down"
docker start mealie                    # push "up"
```

## Znane problemy i ograniczenia

- **Monitor na tym samym hoście nie zgłosi śmierci hosta.** Gdy `castle`
  padnie (zasilanie, Wi-Fi, SSD), zapada cisza zamiast alertu. Rozwiązaniem
  jest zewnętrzny „dead man's switch” (np. healthchecks.io z pingiem
  z `castle`). **Świadomie zaakceptowane** 2026-09-24: na razie bez niego.
  Rozważane i odrzucone: Kuma na Raspberry Pi Zero 2 W. Pada razem z `castle`
  przy braku prądu lub internetu, ma kartę SD i jest drugim hostem do utrzymania.
- **Kuma nie monitoruje sama siebie.** Jeśli kontener stanie, alerty znikają
  bez ostrzeżenia. Zaakceptowane razem z punktem wyżej. Rozwiąże to ten sam
  dead man's switch.
- **Treść alertów przechodzi przez publiczny ntfy.sh.** Zawiera nazwy usług
  i komunikaty błędów, nic więcej. Przy potrzebie większej prywatności:
  własny serwer ntfy.
- **Konfiguracja przez UI nie trafia do Git.** Źródłem prawdy jest SQLite,
  a kopią zapasową tabela w tej notatce.

## Log zmian

- 2026-09-24 — stack utworzony, obraz `2.5.5-slim-rootless`, wystawiony przez
  [[caddy]] pod `uptime-kuma.home.figielak.dev`; 4 monitory, powiadomienia
  ntfy; test alertu (zatrzymanie Mealie) zaliczony; zużycie ~122 MiB
- 2026-09-24 — dodany monitor Beszel
- 2026-09-24 — API key i monitor Push dla [[dashboard-agent]]
- 2026-09-25 — monitor „Uptime Kuma” (panel przez Caddy) dla prywatnego dashboardu
