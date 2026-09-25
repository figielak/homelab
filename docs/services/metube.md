# MeTube

Webowy interfejs do `yt-dlp`. Wklejasz link z YouTube'a albo jednej z kilkuset
innych stron, a plik wideo lub audio ląduje na serwerze. Stamtąd pobierasz go
przez przeglądarkę. Obsługuje playlisty, kanały i subskrypcje.

Wdrożony **poza kolejnością** z `CLAUDE.md`, na wyraźną prośbę. Tak jak
[[calibre-web]], bliżej mu do „danych masowych" z kroku 9.

#usługa

## Dlaczego akurat to

MeTube to cienka nakładka na `yt-dlp`: jeden kontener, bez bazy, stan w kilku
plikach JSON. Obraz ma natywny build `arm64`. Sam `yt-dlp` z linii komend
robi to samo, ale wymaga SSH, a MeTube działa z telefonu.

## Podstawowe dane

| | |
|---|---|
| Host | [[castle]] |
| URL | `https://metube.home.figielak.dev` przez [[caddy]], **za `basic_auth`** |
| Port | 8081 **wyłącznie wewnątrz sieci `proxy`**, nic na hoście |
| Dane | `/srv/homelab/data/metube/` (właściciel `figielak`, UID 1000) |
| Stack | `stacks/metube/` |
| Obraz | `ghcr.io/alexta69/metube:2026.09.25` (manifest ma `arm64`) |
| RAM | `mem_limit` 512 MiB, **zmierzone ~65 MiB w spoczynku** (2026-09-25); szczyt przy pobieraniu do zmierzenia |

| Katalog | W kontenerze | Zawartość |
|---|---|---|
| `state/` | `/state` | `queue.json`, `completed.json`, `subscriptions.json` |
| `downloads/` | `/downloads` | pobrane pliki; ścieżka z `.env` (`DOWNLOADS_DIR`) |

## Decyzje, których nie widać w konfiguracji

- **Logowanie na proxy, nie w aplikacji.** MeTube nie ma kont. Bez bramki
  każdy w LAN i tailnecie mógłby zlecać pobieranie, zapełnić SSD, na którym
  stoi cały host (a z nim DNS domu), i przeglądać historię. `basic_auth`
  w Caddy, hash bcrypt w `stacks/caddy/.env`. Caddy trzyma wynik weryfikacji
  bcrypta w pamięci, więc nie liczy go przy każdym żądaniu.
- **Pobrania na SSD, tymczasowo.** HDD nie jest podłączony. Po podłączeniu
  zmieniasz `DOWNLOADS_DIR` w `.env` i przenosisz pliki, a compose zostaje bez zmian.
- **Bez `YTDL_NIGHTLY_UPDATE_TIME`.** Ta opcja aktualizuje `yt-dlp` w działającym
  kontenerze, poza repo, co łamie przypięcie wersji. Aktualizujemy tag obrazu.

## Zależności

- **Zależy od:** [[caddy]] (dostęp, TLS i logowanie), [[adguard]] (rozwiązywanie
  nazwy), sieci `proxy`.
- **Zależy od niej:** nic.

## Co backupować

Tylko `state/`: kilka KB, a w nim lista subskrypcji. **Pobrań nie backupujemy**,
bo da się je pobrać ponownie, a zjadłyby miejsce na backupy. Jeśli coś zniknie
ze źródła i jest cenne, przenieś to poza katalog MeTube.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalogi danych
sudo mkdir -p /srv/homelab/data/metube/{state,downloads}
sudo chown -R 1000:1000 /srv/homelab/data/metube
#    (opcjonalnie) stan z backupu:
#    sudo cp -a <backup>/metube/state/. /srv/homelab/data/metube/state/

# 3. konfiguracja stacku
cd /opt/homelab/stacks/metube
cp .env.example .env

# 4. start
docker compose config
docker compose up -d
docker compose logs -f
```

### Wystawienie przez proxy z logowaniem

Blok `@metube` w `stacks/caddy/config/Caddyfile` jest w repo. Potrzebne są dwie
zmienne w `stacks/caddy/.env`:

```bash
cd /opt/homelab/stacks/caddy
docker compose exec caddy caddy hash-password    # pyta o hasło, wypisuje hash
```

```dotenv
METUBE_AUTH_USER=krystian
METUBE_AUTH_HASH='$2a$14$...'   # pojedyncze cudzysłowy są obowiązkowe
```

Zmienne środowiskowe wymagają odtworzenia kontenera, sam `caddy reload` nie wystarczy:

```bash
docker compose config | grep METUBE      # hash musi zaczynać się od $2a$14$
docker compose up -d                     # odtwarza caddy, kilka sekund przerwy dla wszystkich usług
docker compose exec caddy printenv METUBE_AUTH_HASH
```

**Pusta zmienna = Caddy nie wstanie**, a razem z nim wszystkie usługi. Najpierw
`.env`, potem `up -d`.

## Znane problemy i ograniczenia

- **Pobieranie z YouTube'a przestaje działać** — prawie zawsze winny jest za stary
  `yt-dlp`. Rozwiązanie: nowszy tag obrazu (nowe wydanie MeTube wychodzi przy
  każdym stabilnym `yt-dlp`).
- **Aplikacje do wysyłania linków** (iOS Shortcut, rozszerzenia przeglądarki)
  muszą obsłużyć `basic_auth` i `CORS_ALLOWED_ORIGINS`. Dziś żadna nie jest
  skonfigurowana. Wklejasz link w UI.
- **Wi-Fi.** Pobieranie i późniejsze ściąganie pliku z serwera idą przez
  to samo Wi-Fi, przez które host obsługuje DNS domu.

## Log zmian

- 2026-09-25 — stack utworzony, obraz `2026.09.25`, `basic_auth` w Caddy,
  pobrania na SSD do czasu podłączenia HDD
