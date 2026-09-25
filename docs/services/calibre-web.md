# Calibre-Web

Webowa biblioteka e-booków. Przeglądanie, czytanie w przeglądarce, pobieranie
na czytnik, katalog OPDS dla aplikacji czytnikowych. Nowe książki trafiają
przez upload w interfejsie.

Wdrożona **poza kolejnością** z `CLAUDE.md`, na wyraźną prośbę. Bliżej jej
do „danych masowych" z kroku 9 niż do czegokolwiek wcześniej.

#usługa

## Dlaczego akurat to

Biblioteka jest w formacie Calibre (`metadata.db`), więc w każdej chwili da się ją
otworzyć desktopowym Calibre na laptopie. Nie ma tu zamkniętego formatu.
Calibre-Web jest lekki i działa na SQLite, bez osobnej bazy.

Alternatywą był **Calibre-Web-Automated**, fork z automatycznym importem z katalogu
i konwersją formatów. Odrzucony, bo ma wbudowany pełny Calibre (dużo więcej RAM),
a jego wsparcie dla arm64 nie było zweryfikowane. Automatyczny import ma sens
dopiero przy masowym zasilaniu biblioteki, np. z Syncthinga (krok 9).

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| URL | `https://calibre.home.figielak.dev` przez [caddy](caddy.md) |
| | Adres to `calibre`, a nie `calibre-web`. To wyjątek od reguły „nazwa = stack”, zrobiony dla wygody. |
| OPDS | `https://calibre.home.figielak.dev/opds` (login jak do UI) |
| Port | 8083 **wyłącznie wewnątrz sieci `proxy`**, nic na hoście |
| Dane | `/srv/homelab/data/calibre-web/` (właściciel `figielak`, UID 1000) |
| Stack | `stacks/calibre-web/` |
| Obraz | `lscr.io/linuxserver/calibre-web:0.6.27-ls402` (manifest ma `arm64`) |
| RAM | `mem_limit` 256 MiB, **zmierzone ~203 MiB** (2026-09-25, pusta biblioteka) |

Dwa podkatalogi danych, dwie bazy SQLite:

| Katalog | W kontenerze | Zawartość |
|---|---|---|
| `config/` | `/config` | `app.db`: użytkownicy, ustawienia, półki, postęp czytania |
| `library/` | `/books` | biblioteka Calibre: `metadata.db` + katalogi z plikami książek |

## Zależności

- **Zależy od:** [caddy](caddy.md) (dostęp po nazwie i TLS), [adguard](adguard.md) (rozwiązywanie
  nazwy), sieci `proxy`.
- **Zależy od niej:** nic.

## Co backupować

Cały katalog `/srv/homelab/data/calibre-web/`, czyli oba podkatalogi.
Sama biblioteka bez `app.db` odtworzy książki, ale bez kont i postępu czytania.

**SQLite ×2.** Ta sama uwaga co przy [mealie](mealie.md): kopia działającej bazy może być
niespójna. Przy restic albo zatrzymujemy kontener, albo robimy `sqlite3 .backup`
dla `app.db` i `metadata.db`.

**Kopii zapasowej dziś nie ma** (HDD niepodłączony, krok 6 stoi). Książki wgrane
przez upload istnieją tylko na SSD.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalogi danych — wlascicielem musi byc UID 1000 (PUID w compose)
sudo mkdir -p /srv/homelab/data/calibre-web/{config,library}
sudo chown -R 1000:1000 /srv/homelab/data/calibre-web

# 3. BIBLIOTEKA — przed pierwszym startem, jedno z dwojga:
#    a) z backupu:
#       sudo cp -a <backup>/calibre-web/. /srv/homelab/data/calibre-web/
#    b) nowa, pusta — patrz "Pusta biblioteka" nizej
#    potem:
#       sudo chown -R 1000:1000 /srv/homelab/data/calibre-web

# 4. konfiguracja stacku
cd /opt/homelab/stacks/calibre-web
cp .env.example .env

# 5. start
docker compose config
docker compose up -d
docker compose logs -f
```

### Pusta biblioteka

Calibre-Web **nie tworzy biblioteki**, tylko wskazuje na istniejącą. Pustą robi się raz
na laptopie: w desktopowym Calibre wybierz „Przełącz/utwórz bibliotekę” i nowy, pusty
katalog. Powstanie w nim `metadata.db`. Potem:

```bash
# z laptopa
rsync -av ~/Calibre-pusta/ figielak@castle:/tmp/calibre-library/
# na castle
sudo cp -a /tmp/calibre-library/. /srv/homelab/data/calibre-web/library/
sudo chown -R 1000:1000 /srv/homelab/data/calibre-web
rm -rf /tmp/calibre-library
```

### Wystawienie przez proxy

Blok w `stacks/caddy/config/Caddyfile`:

```caddyfile
@calibre-web host calibre.home.figielak.dev
handle @calibre-web {
	reverse_proxy calibre-web:8083
}
```

```bash
cd /opt/homelab/stacks/caddy
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Pierwsze logowanie

Domyślne konto: `admin` / `admin123`.

1. Przy pierwszym wejściu ustaw lokalizację biblioteki na `/books`.
2. **Od razu zmień hasło admina.** Zapisz je w menedżerze haseł jako „Homelab Calibre-Web”.
3. Włącz upload: Admin → Edit Basic Configuration → Feature Configuration →
   Enable Uploads. **Najpierw wyczyść** pole Path to Kepubify E-Book Converter
   (External binaries), inaczej zapis się nie uda. Szczegóły w znanych problemach.
4. Na koncie użytkownika zaznacz Allow Uploads.

## Znane problemy i ograniczenia

- **Brak konwersji formatów na ARM64.** Mod `universal-calibre` działa tylko na x86-64.
  Książki trzeba wgrywać od razu w formacie czytnika. Wróci po migracji na x86.
- **SQLite tylko na dysku lokalnym.** Nie przenoś `library/` ani `config/` na NFS/SMB.
- **„Kepubify binary not found” blokuje zapis Basic Configuration** (`0.6.27-ls402`).
  Na Linuksie Calibre-Web akceptuje tylko pliki `kepubify-linux-64bit` i `kepubify-linux-32bit`
  (`cps/binary_helper.py`). Obraz linuxserver instaluje program jako `/usr/bin/kepubify`
  i przy pierwszym starcie sam wpisuje tę ścieżkę do `app.db`. Przez to każdy zapis
  ustawień się wycofuje. Obejście: puste pole kepubify, czyli brak KEPUB dla Kobo.
  Przy aktualizacji obrazu sprawdź, czy błąd poprawiono.
- **Zablokowany admin** = reset hasła przez bezpośrednią edycję `app.db`
  (README obrazu linuxserver).

## Log zmian

- 2026-09-25 — stack utworzony, obraz `0.6.27-ls402`, pusta biblioteka,
  wystawiony przez [caddy](caddy.md) pod `calibre.home.figielak.dev`
