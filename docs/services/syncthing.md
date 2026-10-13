# Syncthing

Synchronizacja plików między urządzeniami, bez chmury. Tutaj: vaulty Obsidiana
między laptopem a telefonem.

Wdrożony **przed krokiem 6** (backup) z `CLAUDE.md`, na wyraźną prośbę.
Krok 9 jest przez to zamknięty tylko częściowo: dane masowe czekają na HDD.

#usługa

## Dlaczego akurat to i po co na serwerze

Syncthing jest P2P: laptop i telefon zsynchronizowałyby się bez serwera, ale
tylko wtedy, gdy oba są jednocześnie włączone i się widzą. `castle` jest
trzecim, zawsze włączonym węzłem. Zmiana z telefonu trafia na laptop także
wtedy, gdy laptop w chwili edycji spał. **To jedyny powód, dla którego usługa
działa na serwerze.**

- **Obsidian Sync** robi to samo, ale jest płatny i trzyma notatki u dostawcy.
- **Git w vaultcie** wymaga ręcznych commitów, a na Androidzie jest niewygodny.
- Pliki zostają zwykłymi plikami Markdown na dysku, bez własnego formatu.

**To nie jest backup.** Skasowanie albo zepsucie notatki synchronizuje się
na wszystkie urządzenia. Wersjonowanie plików na `castle` (niżej) łagodzi to
częściowo, ale nie zastępuje restica.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| Panel | `https://syncthing.home.figielak.dev` przez [caddy](caddy.md) |
| Adres synchronizacji | `tcp://192.168.10.10:22000`, wpisywany ręcznie u klientów |
| Porty | **22000 tcp + udp na hoście** (wyjątek, niżej); 8384 wyłącznie w sieci `proxy` |
| Dane | `/srv/homelab/data/syncthing/` (właściciel `figielak`, UID 1000) |
| Stack | `stacks/syncthing/` |
| Obraz | `syncthing/syncthing:2.1.6` (manifest ma `arm64`) |
| RAM | `mem_limit` 256 MiB, `GOMEMLIMIT` 200 MiB; szacunek 50–100 MiB, **do zmierzenia** |

Zawartość katalogu danych:

| Ścieżka | Zawartość | Backup |
|---|---|---|
| `config/` | `config.xml`, klucze (`cert.pem`, `key.pem`) wyznaczające Device ID, baza indeksu | **tak** |
| `vaults/<nazwa>/` | synchronizowane vaulty | **tak** |
| `vaults/<nazwa>/.stversions/` | stare wersje plików (wersjonowanie) | opcjonalnie |

### Dlaczego port 22000 jest opublikowany na hoście

To **świadomy wyjątek** od reguły „kontenery aplikacyjne nie publikują portów”.
Protokół synchronizacji to nie HTTP, więc Caddy go nie przeniesie.

- Port jest otwarty tylko w sieci domowej. Na routerze nic nie jest
  przekierowane, z internetu jest nieosiągalny.
- Poza domem działa przez trasę `192.168.10.10/32` z [tailscale](tailscale.md):
  ten sam adres, bez żadnej dodatkowej konfiguracji.
- Każde połączenie jest uwierzytelniane przez TLS po Device ID. Urządzenie
  spoza listy zostaje odrzucone.

Odrzucone alternatywy:

- `network_mode: host` (zalecany w dokumentacji obrazu): panel na 8384 byłby
  osiągalny z pominięciem Caddy, a doszedłby port 21027/udp.
- Sidecar Tailscale albo `tailscale serve`: zero portów w LAN, ale Tailscale
  musiałby działać na telefonie i laptopie także w domu.
- Same relaye Syncthinga: wolno i z zależnością od internetu.

Skutek uboczny trybu bridge: **local discovery nie działa**, bo kontener widzi
tylko własny adres z podsieci Dockera. Dlatego adres `castle` wpisuje się
u klientów ręcznie.

## Zależności

- **Zależy od:** [caddy](caddy.md) i [adguard](adguard.md) tylko dla panelu. Sama
  synchronizacja idzie po adresie IP i działa bez nich. Poza domem:
  [tailscale](tailscale.md).
- **Zależy od niego:** nic. Bez `castle` laptop i telefon dalej synchronizują
  się bezpośrednio, gdy są jednocześnie online.

## Konfiguracja w panelu

Ta część **nie jest w repo**, żyje w `config/config.xml`. Po odtworzeniu bez
backupu trzeba ją powtórzyć.

1. **Hasło GUI** (Settings → GUI). Menedżer haseł, „Homelab Syncthing”.
2. Settings → Connections: wyłączone **Global Discovery**, **Local Discovery**,
   **Enable Relaying** i **Enable NAT traversal**. Przy stałym adresie są
   zbędne, a `castle` nie rozmawia dzięki temu z serwerami zewnętrznymi.
3. Usunięty **Default Folder**.
4. Urządzenia: laptop i telefon dodane po Device ID.
5. Jeden folder na vault, ścieżka `/var/syncthing/vaults/<nazwa>`,
   File Versioning: **Staggered**.

### Ignore patterns

W każdym folderze z vaultem, na każdym urządzeniu (Folder → Edit → Ignore Patterns):

```
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.trash
```

Stan okien i paneli różni się między laptopem a telefonem. Bez tego każde
otwarcie Obsidiana generuje pliki `.sync-conflict`.

### Klienci

Na obu urządzeniach: w ustawieniach urządzenia `castle` pole **Addresses**
zmienione z `dynamic` na `tcp://192.168.10.10:22000`.

- **Laptop (Fedora):**
  ```bash
  sudo dnf install syncthing
  systemctl --user enable --now syncthing
  ```
  Panel lokalny: `http://127.0.0.1:8384`.
- **Telefon (Android):** aplikacja Syncthing-Fork (oficjalna aplikacja
  Androida została wycofana). Wyłącz dla niej optymalizację baterii, inaczej
  system ubija synchronizację w tle.

### Dodawanie vaulta

Zaczynaj od urządzenia, które **ma** vault, i udostępniaj do **pustych**
folderów na pozostałych. Dwie niezależne kopie tego samego vaulta spięte
naraz kończą się falą plików `.sync-conflict`.

## Co backupować

Cały katalog `/srv/homelab/data/syncthing/`. `config/` zawiera klucz prywatny
urządzenia: bez niego odtworzony `castle` dostaje nowe Device ID i trzeba go
sparować z laptopem i telefonem od nowa.

**Kopii zapasowej dziś nie ma** (HDD niepodłączony, krok 6 stoi). W praktyce
vaulty istnieją w trzech egzemplarzach, więc pad SSD ich nie niszczy.
Nie chroni to przed błędem użytkownika.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalog danych — tworzymy jawnie, zeby nie powstal jako root przez Dockera
sudo mkdir -p /srv/homelab/data/syncthing
sudo chown 1000:1000 /srv/homelab/data/syncthing

# 3. przy odtwarzaniu: dane z backupu PRZED pierwszym startem,
#    inaczej Syncthing wygeneruje nowe klucze i nowe Device ID
#    sudo cp -a <backup>/syncthing/. /srv/homelab/data/syncthing/

# 4. konfiguracja stacku
cd /opt/homelab/stacks/syncthing
cp .env.example .env

# 5. start
docker compose config
docker compose up -d
docker compose logs -f
```

Blok w `stacks/caddy/config/Caddyfile` jest już w repo, wystarczy reload:

```bash
cd /opt/homelab/stacks/caddy
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

**Hasło GUI ustaw od razu po starcie.** Do tego momentu panel jest otwarty
dla każdego w sieci domowej i w tailnecie, a z panelu da się udostępnić
dowolny folder z `/var/syncthing`.

Bez backupu: przejdź sekcję „Konfiguracja w panelu”, a na laptopie i telefonie
usuń stare urządzenie `castle` i dodaj nowe. Vaulty wrócą z klientów same.

### Weryfikacja

```bash
docker ps --filter name=syncthing     # (healthy)
sudo ss -tulpn | grep 22000           # tcp i udp
curl -s https://syncthing.home.figielak.dev/rest/noauth/health   # {"status":"OK"}
```

Test właściwy: zatrzymaj Syncthing na laptopie, zmień notatkę na telefonie,
uruchom laptop. Zmiana ma dojść przez `castle`.

## Jak wyłączyć

```bash
cd /opt/homelab/stacks/syncthing && docker compose down
```

Potem usuń blok z `Caddyfile` i zrób reload. Vaulty na laptopie i telefonie
zostają nietknięte.

## Znane problemy i ograniczenia

- **Nie synchronizuj `docs/` z tego repo.** To też vault Obsidiana, ale żyje
  w Git. Syncthing nadpisujący pliki w `.git` psuje repozytorium.
- **Pliki `.sync-conflict-*`** powstają, gdy ta sama notatka zmieniła się na
  dwóch urządzeniach przed synchronizacją. Syncthing nie scala treści, trzeba
  to zrobić ręcznie i skasować plik konfliktu.
- **Monitor w [uptime-kuma](uptime-kuma.md) sprawdza tylko panel.** Zerwanego
  połączenia z telefonem nie wykryje, to widać dopiero w panelu.

## Log zmian

- 2026-10-13 — stack utworzony, obraz `2.1.6`, port 22000 tcp/udp na hoście
  jako wyjątek, panel przez [caddy](caddy.md) pod `syncthing.home.figielak.dev`
