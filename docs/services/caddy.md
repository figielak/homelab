# Caddy

Reverse proxy i jedyne wejście do wszystkich usług homelaba. Obsługuje TLS
dla `*.home.figielak.dev` — certyfikat wildcard od Let's Encrypt, wydawany
przez walidację DNS-01 w Cloudflare.

#usługa #proxy

## Dlaczego akurat to

Wybrany zamiast nginx i Traefika: automatyczne TLS bez dodatkowej obsługi,
a konfiguracja jest krótsza o rząd wielkości. Dodanie usługi to trzy linie
w `Caddyfile`, nie osobny plik z blokiem `server` i ścieżkami certyfikatów.

## Dlaczego własny build zamiast oficjalnego obrazu

To odstępstwo od zasady „bierzemy gotowe, pinowane obrazy" i ma konkretny powód.

Oficjalny obraz Caddy **nie zawiera pluginów DNS**, a bez pluginu nie ma
walidacji DNS-01 — czyli nie ma certyfikatu wildcard. Utrzymujący plugin
publikują gotowy obraz `ghcr.io/caddy-dns/cloudflare`, ale jest on
**wyłącznie `amd64`** (sprawdzone 2026-09-21), więc na ARM64 odpada.

Zostaje `Dockerfile` budujący dwuetapowo z `caddy:<wersja>-builder`.
Obie wersje — Caddy i pluginu — są pinowane w `ARG`, więc zasada
„nigdy `:latest`" zostaje zachowana. Kosztem jest krok `docker compose build`
w procedurze odtworzenia: kilka minut na Pi 4 i wymagany internet.

**Po migracji na x86 warto to sprawdzić ponownie** — jeśli gotowy obraz
zyska build `arm64`/zostaniemy na `amd64`, własny `Dockerfile` przestanie
być potrzebny.

## Dlaczego DNS w Cloudflare, skoro domena jest na name.com

Rejestracja została w name.com, do Cloudflare przeniesione są tylko serwery
nazw. Powody:

1. **Plugin name.com jest porzucony** — ostatni commit w `caddy-dns/namedotcom`
   z października 2023, przy zmienionym od tego czasu API `libdns`.
   `caddy-dns/cloudflare` ma commity z 2026.
2. **Token można ograniczyć do jednej strefy.** Klucz API name.com daje pełny
   dostęp do konta, z transferem domeny włącznie. Token leży w `.env`
   na hoście, gdzie grupa `docker` jest równoważna rootowi — zakres uprawnień
   jest tu realnym zabezpieczeniem, nie formalnością.

## Podstawowe dane

| | |
|---|---|
| Host | [[castle]] |
| Domena | `*.home.figielak.dev` |
| Porty | 80 tcp, 443 tcp, 443 udp (HTTP/3) |
| Dane | `/srv/homelab/data/caddy/{data,config}` |
| Stack | `stacks/caddy/` |
| Obraz | `homelab/caddy:2.11.4-cf0.2.4` (budowany lokalnie) |
| Sieć | `proxy` (external) |
| Pliki statyczne | `/srv/homelab/data/quartz` → `/srv/quartz` (ro), strona [[quartz]] |
| Sekrety | `CF_API_TOKEN` — menedżer haseł, „Homelab Cloudflare DNS token" |

## Zależności

- **Zależy od:** sieci `proxy`, tokenu Cloudflare, aktywnej strefy DNS
  w Cloudflare. Certyfikat da się wydać tylko z działającym internetem.
- **Zależy od niej:** każda usługa wystawiana po nazwie. Caddy nie działa =
  nic nie jest dostępne przez HTTPS.
- **AdGuard** ([[adguard]]) musi mieć DNS rewrite `*.home.figielak.dev`
  → `192.168.10.10`, inaczej nazwy nie rozwiążą się w sieci lokalnej.

Caddy i AdGuard są od siebie niezależne: awaria proxy nie psuje DNS w domu,
awaria DNS-a nie zatrzymuje samego proxy (choć nikt do niego nie trafi).

## Co backupować

Katalog `/srv/homelab/data/caddy/data`. Trzyma certyfikaty **i klucz konta
ACME**.

Utrata nie jest katastrofą — Caddy wyrobi nowe certyfikaty przy starcie.
Ale Let's Encrypt ma limity (rzędu 5 identycznych certyfikatów na tydzień),
więc przy kilku nieudanych próbach odbudowy można się na nie natknąć
i zostać bez HTTPS do końca tygodnia.

`config/` to stan autozapisu Caddy, odtwarzalny z `Caddyfile`. Nieistotny.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. siec wspoldzielona (raz na host)
docker network create proxy 2>/dev/null || echo "siec proxy juz istnieje"

# 3. katalogi danych
sudo mkdir -p /srv/homelab/data/caddy/{data,config}

# 4. sekrety i zmienne
cd /opt/homelab/stacks/caddy
cp .env.example .env
#    uzupelnij CF_API_TOKEN i ACME_EMAIL z menedzera hasel

# 5. ODTWORZENIE Z BACKUPU (opcjonalne, oszczedza limity Let's Encrypt)
#    sudo cp -a <backup>/caddy/data/. /srv/homelab/data/caddy/data/

# 6. build — kilka minut na Pi 4
docker compose build

# 7. sprawdzenie skladni bez uruchamiania
docker compose config

# 8. start
docker compose up -d
docker compose logs -f
```

Pierwszy start wydaje certyfikat wildcard. W logach szukaj wpisu o wydaniu
certyfikatu dla `*.home.figielak.dev`. Trwa to od kilkunastu sekund
do kilku minut — walidacja DNS-01 czeka na propagację rekordu TXT.

### Warunek wstępny: strefa w Cloudflare musi być aktywna

```bash
dig NS figielak.dev +short
```

Musi zwracać serwery Cloudflare. **Przy nieaktywnej strefie nie uruchamiaj
Caddy** — będzie w kółko ponawiał walidację i można trafić na limity
Let's Encrypt.

## Dodanie nowej usługi za proxy

W `stacks/caddy/config/Caddyfile`, wewnątrz bloku `*.home.figielak.dev`:

```caddyfile
@mealie host mealie.home.figielak.dev
handle @mealie {
	reverse_proxy mealie:9000
}
```

Usługa musi należeć do sieci `proxy`, wtedy adresujesz ją nazwą kontenera.
Wyjątkiem jest AdGuard w trybie `host` — do niego idzie `{$HOST_IP}:3000`.

Przeładowanie bez restartu:

```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

**Sam `git pull` niczego nie zmienia** — Caddy trzyma konfigurację w pamięci.
Po zmianie trzeba wykonać jedno z dwojga, zależnie od tego, co się zmieniło:

| Zmiana | Polecenie w `stacks/caddy` |
|---|---|
| tylko `Caddyfile` | `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile` |
| `docker-compose.yml` (mount, zmienna, port) | `docker compose up -d` — odtwarza kontener; `reload` tego nie widzi |

Po `up -d` sprawdź, że kontener faktycznie powstał od nowa:
`docker compose ps --format '{{.Name}}  {{.RunningFor}}'` → „… seconds ago”.

### Pliki statyczne zamiast proxy

Dla strony bez własnego serwera (np. [[quartz]]) Caddy serwuje pliki z dysku:
mount w `docker-compose.yml` + `root` i `file_server` w bloku zamiast
`reverse_proxy`. Montuj **katalog nadrzędny** wyniku, jeśli generator
kasuje i tworzy katalog wyjściowy od nowa — to ta sama pułapka i-węzła co
przy `Caddyfile` (patrz „Znane problemy”).

Certyfikat wildcard obejmuje nową nazwę automatycznie — nie trzeba go wydawać
ponownie.

## Znane problemy i ograniczenia

- **`.dev` jest na liście HSTS preload.** Przeglądarki wymuszają HTTPS
  i nie pozwalają ominąć błędu certyfikatu. Zepsuty certyfikat = usługa
  niedostępna, bez obejścia „kliknij mimo to".
- **Panel AdGuarda pozostaje osiągalny bezpośrednio** na `192.168.10.10:3000`,
  z pominięciem proxy. Wynika to z trybu `host` i bez firewalla się tego
  nie obejdzie.
- **Certyfikat wymaga internetu i działającego Cloudflare.** Przy odnowieniu
  bez łączności certyfikat wygaśnie po 90 dniach. Caddy odnawia z dużym
  wyprzedzeniem, więc realne ryzyko jest niskie.
- **Build jest krokiem manualnym.** Po zmianie `ARG` w `Dockerfile` trzeba
  `docker compose build`, samo `up -d` nie przebuduje obrazu.
- **Montujemy katalog `config/`, nie sam `Caddyfile`** — i tak musi zostać.
  Bind mount pojedynczego pliku wiąże i-węzeł, a `git pull` podmienia pliki
  przez `rename`, tworząc nowy i-węzeł. Kontener zostawał wtedy ze starą
  treścią, a `caddy reload` raportował sukces po wczytaniu starego pliku —
  objaw jest mylący, bo wszystko wygląda na działające.
  Wpadliśmy w to 2026-09-21 przy dodawaniu [[mealie]].
- **`Brak takiej uslugi w homelabie` przy aktualnym `Caddyfile`** = Caddy nie
  wczytał zmian: pominięty `reload` albo `up -d`. Sprawdzenie:
  `docker compose exec caddy grep -c <nazwa> /etc/caddy/Caddyfile` (plik jest)
  i `docker compose ps` (od kiedy działa kontener). Trafiło się 2026-09-25
  dwa razy: przy [[opengist]] i [[quartz]].

## Log zmian

- 2026-09-21 — stack utworzony; Caddy `2.11.4` + plugin `cloudflare v0.2.4`,
  build własny (gotowy obraz pluginu jest tylko `amd64`);
  DNS `figielak.dev` przeniesiony z name.com do Cloudflare
- 2026-09-21 — `Caddyfile` przeniesiony do `config/`, montowany jako katalog
  zamiast pojedynczego pliku (patrz „Znane problemy")
- 2026-09-25 — mount `/srv/quartz` (ro) i pierwszy blok z `file_server`
  zamiast `reverse_proxy`: statyczna strona [[quartz]]
