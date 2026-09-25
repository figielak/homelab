# Quartz

Statyczna strona WWW z dokumentacji homelaba (`docs/`, czyli vault Obsidiana).
Czytanie notatek z przeglądarki, np. z telefonu: działające linki,
wyszukiwarka, graf, strony tagów. **Tylko do odczytu** — pisze się
w Obsidianie na laptopie, a strona jest przebudowywana po `git pull`.

Wdrożona **poza kolejnością** z `CLAUDE.md`, na wyraźną prośbę.

#usługa

## Dlaczego akurat to

Strona ma być widokiem na istniejący vault, a nie drugim miejscem do pisania.
Quartz jest zbudowany pod Obsidiana: rozwiązuje `[[link]]` po samej nazwie
pliku, jak Obsidian (`markdownLinkResolution: shortest`), więc `[[castle]]`
z `services/` trafia do `hosts/castle.md`. Od 2026-09-25 notatki używają
względnych linków Markdown (żeby działały też na GitHubie) — Quartz
rozwiązuje je poprawnie przy tym samym ustawieniu, a wikilinki dopisane
przez pomyłkę nadal zadziałają na stronie.

Odrzucone:
- **An Otter Wiki** — rozwiązuje wikilinki jako ścieżki od korzenia
  (`[[castle]]` → `/castle`), co psuje linki między folderami vaulta,
  i ma własne repozytorium, z którym vault trzeba by synchronizować.
- **BookStack** — wymaga MariaDB, a treść żyje w bazie, nie w plikach.
- **`linuxserver/obsidian`** — pełny pulpit przez VNC, za ciężki na Pi.

Na stałe **nic nie działa**: kontener Quartza tylko generuje HTML i znika,
a pliki serwuje istniejący już [caddy](caddy.md). Stały koszt RAM: 0.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| URL | `https://quartz.home.figielak.dev`, pliki serwuje [caddy](caddy.md) (`file_server`) |
| Port | brak — nie ma działającej usługi |
| Treść | `/opt/homelab/docs` (repo), montowana tylko do odczytu |
| Wynik | `/srv/homelab/data/quartz/public/` (właściciel UID 1000) |
| Stack | `stacks/quartz/`: `Dockerfile`, `docker-compose.yml`, `quartz.config.yaml` |
| Obraz | `homelab/quartz:5.0.0`, budowany lokalnie z `node:22.16.0-slim` + Quartz `v5.0.0` |
| Rozmiar obrazu | **~4,7 GB** (pluginy z własnymi `node_modules`) |
| RAM | tylko na czas budowania, `mem_limit` 1 GiB, `--concurrency 2` |

Czas budowy strony (2026-09-25): laptop x86 **3 s**, `castle` **16 s**
(14 notatek, z czego 15 s to parsowanie). Obraz: laptop ~2 min, na Pi niezmierzone.

### Jak to jest złożone

- Quartz to **projekt do sklonowania**, nie paczka. Dockerfile klonuje go
  po tagu, zamiast trzymać ~300 jego plików w tym repo. W repo leży tylko
  `quartz.config.yaml`.
- Pluginy v5 to osobne repozytoria, przypięte do commitów w `quartz.lock.json`
  z tagu Quartza. Pobiera je `git clone` przy budowie obrazu, więc obraz
  potrzebuje `git` i dostępu do GitHuba. Budowa strony już nie.
- `quartz.config.yaml` = domyślny config z `v5.0.0`, zmiany oznaczone
  komentarzem `homelab:`. Najważniejsze: **analityka wyłączona**
  (domyślnie Plausible), `og-image` i `cname` wyłączone, data zmiany
  z frontmattera albo systemu plików (bez `.git` w kontenerze).
- **Montowanie katalogu nadrzędnego, w obu miejscach.** Build kasuje
  `public/` w całości i tworzy od nowa (`rm -r`). Dlatego:
  - kontener Quartza montuje `data/quartz` jako `/out` i pisze do `/out/public`
    — punktu montowania nie da się skasować;
  - Caddy montuje `data/quartz` jako `/srv/quartz` — mount samego `public/`
    zostałby przy starym, skasowanym katalogu (ta sama pułapka co z Caddyfile).

## Zależności

- **Zależy od:** [caddy](caddy.md) (serwowanie plików i TLS), [adguard](adguard.md) (nazwa),
  repo w `/opt/homelab` (treść).
- **Zależy od niej:** nic.

## Co backupować

**Nic.** Wynik da się w całości odtworzyć z repo, a konfiguracja jest w Git.
`/srv/homelab/data/quartz/` można pominąć w restic.

## Aktualizacja strony

Po każdej zmianie w `docs/`, na `castle`:

```bash
cd /opt/homelab && git pull --ff-only
cd stacks/quartz && docker compose run --rm quartz
```

W trakcie budowania (~16 s na Pi) strona jest pusta, bo build najpierw
kasuje `public/`. Przy domowym użyciu bez znaczenia.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalog wyniku — przed pierwszym startem Caddy, inaczej Docker
#    utworzy go jako root przy montowaniu
sudo mkdir -p /srv/homelab/data/quartz
sudo chown 1000:1000 /srv/homelab/data/quartz

# 3. konfiguracja stacku
cd /opt/homelab/stacks/quartz
cp .env.example .env

# 4. obraz (dlugo, jednorazowo) i strona
docker compose build
docker compose run --rm quartz
```

### Wystawienie przez proxy

W `stacks/caddy/docker-compose.yml` mount
`${DATA_ROOT}/quartz:/srv/quartz:ro`, w `Caddyfile`:

```caddyfile
@quartz host quartz.home.figielak.dev
handle @quartz {
	root * /srv/quartz/public
	try_files {path} {path}.html {path}/ =404
	encode gzip
	file_server
}
```

Nowy mount wymaga **odtworzenia** kontenera Caddy (`docker compose up -d`),
sam `caddy reload` nie wystarczy.

## Znane problemy i ograniczenia

- **Obraz waży ~4,7 GB** na SSD, żeby wygenerować ~250 KB HTML. Przyjęte, bo
  `/` jest zajęte w 4%, a budowa na hoście pozwala odtworzyć stronę z samego
  repo.
- **Strona nie odświeża się sama.** Po `git pull` trzeba uruchomić build.
- **Brak własnej strony 404.** Quartz generuje `404.html`, ale Caddy go nie
  używa — `handle_errors` w wildcardowym bloku działałby dla wszystkich usług.
- **Podbicie wersji** = tag w `docker-compose.yml` (`QUARTZ_VERSION` i `image`)
  + porównanie `quartz.config.yaml` z nowym domyślnym configiem.
- **`docs/index.md`** to strona główna. Bez niego `/` zwraca 404.

## Log zmian

- 2026-09-25 — stack utworzony, Quartz `v5.0.0`, strona z `docs/` pod
  `quartz.home.figielak.dev`, serwowana przez [caddy](caddy.md)
- 2026-09-25 — wikilinki w `docs/` zamienione na względne linki Markdown;
  po `git pull` sprawdzić linki między folderami (np. usługa → `castle`)
