# castle

Jedyny host homelaba. Uruchamia wszystko: Docker, DNS, reverse proxy, usługi.
Konto administracyjne opisane osobno: [[figielak]].

#host

## Stan ogólny

| | |
|---|---|
| Hostname | `castle` |
| Adres IP | `192.168.10.10/24` (rezerwacja DHCP w ruterze) |
| Brama | `192.168.10.1` |
| Interfejs | `wlan0` — **Wi-Fi**, `eth0` odłączony |
| Sprzęt | Raspberry Pi 4 Model B Rev 1.5, 4 GB RAM |
| Architektura | `aarch64` (`linux/arm64`) |
| OS | Raspberry Pi OS Lite, Debian 13 (trixie) |
| Kernel | `6.18.39+rpt-rpi-v8` |
| Strefa czasowa | Europe/Warsaw, NTP aktywny |
| Repo | `/opt/homelab`, właściciel `figielak` |

Stan zebrany: 2026-09-21.

## Rejestr portów

**Aktualizuj przy każdej nowej usłudze.** Przy jednym hoście to jedyna ochrona
przed kolizjami.

### Zajęte

| Port | Proto | Usługa | Proces | Uwagi |
|---|---|---|---|---|
| 22 | tcp | SSH | `sshd` | tylko klucz, root zablokowany |
| 53 | tcp + udp | DNS | `AdGuardHome` | `*:53`, wszystkie interfejsy; `network_mode: host` |
| 80 | tcp | Caddy | kontener `caddy` | przekierowanie na HTTPS |
| 443 | tcp + udp | Caddy | kontener `caddy` | udp = HTTP/3 (QUIC) |
| 2375 | tcp | Docker socket proxy | kontener `beszel-socket-proxy` | **tylko `127.0.0.1`**; tylko odczyt Docker API dla agenta [[beszel]] |
| 3000 | tcp | panel AdGuard | `AdGuardHome` | wystawiony jako `adguard.home.figielak.dev`; **nadal osiągalny bezpośrednio** |
| 5353 | udp | mDNS | `avahi-daemon` | **nie koliduje z 53** |
| 32929, 49401 | udp | mDNS | `avahi-daemon` | porty efemeryczne, zmienne |
| 41641 | udp | Tailscale | `tailscaled` | IPv4 + IPv6, usługa systemowa; zobacz [[tailscale]] |

Docker nie zajmuje żadnego portu na hoście — `dockerd` słucha na gnieździe
`/var/run/docker.sock`, nie na TCP. Kontenery aplikacyjne też nie publikują
portów. Wyjątki:
- AdGuard w trybie `host` (port 53), zobacz [[adguard]]
- `beszel-socket-proxy` na `127.0.0.1:2375`: tylko localhost, bo agent
  w trybie `host` nie dosięgnie go po nazwie kontenera
- `beszel-agent` w trybie `host` **nie zajmuje portu**, bo słucha na unix
  sockecie. Zobacz [[beszel]].
- `dashboard-agent` w trybie `host` **nie zajmuje portu**, tylko wysyła dane
  na zewnątrz. Zobacz [[dashboard-agent]].

**`systemd-resolved` na tym hoście nie działa.** `/etc/resolv.conf` generuje
NetworkManager i wskazuje wprost na 8.8.8.8 i 1.1.1.1. Nie ma stub listenera
na 127.0.0.53, dzięki czemu port 53 był wolny dla AdGuarda i `DNSStubListener=no`
nie było potrzebne. Gdyby `systemd-resolved` kiedykolwiek zostało włączone,
ten warunek wraca.

### Zarezerwowane (planowane, jeszcze nie zajęte)

Brak. Kolejne usługi idą za Caddy i **nie publikują portów na hoście** —
wystarczy dodać blok w `Caddyfile` i podłączyć kontener do sieci `proxy`.

## Dyski

| Urządzenie | Rozmiar | FS | Label | Montowanie |
|---|---|---|---|---|
| `sda1` | 512 MB | vfat | `bootfs` | `/boot/firmware` |
| `sda2` | 118,7 GB | ext4 | `rootfs` | `/` |

- Boot z SSD działa: `BOOT_ORDER=0xf14` (USB przed SD), root na `/dev/sda2`.
- SSD podłączony przez mostek USB-SATA ASMedia ASM1153.
- `/` zajęte w 4% (4,2 GB / 117 GB).
- Swap: aktywny `zram0` (2 GB). `loop0` (`origin:rpi-swap`, 2 GB) istnieje,
  ale jest nieaktywny — i dobrze, swap na SSD zużywa jego żywotność.
- `fstab` montuje po `PARTUUID`, nie po `/dev/sdX` — odporne na zmianę kolejności USB.

**HDD 1 TB nie jest podłączony.** `/mnt/hdd` nie istnieje, `lsusb` widzi tylko
mostek SSD. Blokuje to backupy (krok 6) i dane masowe (krok 9).

## Budżet RAM

| | |
|---|---|
| Całość | 3,7 GiB |
| Baseline systemu (bez Dockera) | ~185 MiB |
| Baseline z `dockerd` + `containerd`, bez kontenerów | ~246 MiB |
| Narzut samego Dockera | ~61 MiB (zmierzone 2026-09-21) |
| Narzut `tailscaled` | ~60 MiB RSS (zmierzone 2026-09-24) |
| Dostępne na kontenery | ~3,4 GiB (po odjęciu Dockera i `tailscaled`) |

Suma `mem_limit` wszystkich stacków musi się w tym mieścić. Przy każdej nowej
usłudze odnotuj tu przydział.

| Stack | `mem_limit` | Zmierzone | Status |
|---|---|---|---|
| `adguard` | 256 MiB | 76 MiB | działa od 2026-09-21 |
| `caddy` | 256 MiB | 55 MiB | działa od 2026-09-21 |
| `mealie` | 1024 MiB | ~250 MiB | działa od 2026-09-21 |
| `uptime-kuma` | 256 MiB | ~122 MiB | działa od 2026-09-24 |
| `beszel` (hub + agent + proxy) | 128 + 64 + 64 MiB | ~12 + 5 + 18 MiB | działa od 2026-09-24; **pomiar tuż po starcie**, do powtórzenia |
| `dashboard-agent` | 64 MiB | ~13 MiB | działa od 2026-09-24 |
| `calibre-web` | 256 MiB | ~203 MiB | działa od 2026-09-25; **79% limitu**, do obserwacji |
| `metube` | 512 MiB | ~65 MiB | działa od 2026-09-25; w spoczynku; **szczyt ~400 MiB** przy pobieraniu 1080p (78% limitu) |
| **Przydzielone razem** | **2,85 GiB** | **~820 MiB** | pozostaje ~0,55 GiB z dostępnych |

Pomiary ze stanu ustalonego (po restarcie, z załadowanymi listami filtrów).
Tuż po `docker compose up` wartości są o połowę niższe i wprowadzają w błąd.

## Stan wdrożenia

Kolejność z `CLAUDE.md`:

| Krok | Stan |
|---|---|
| 1. Baza: OS, boot z SSD, hardening SSH, HDD, Docker | **częściowo** — OS ✓, boot z SSD ✓, SSH ✓, Docker ✓, **HDD ✗ (brak sprzętu)** |
| 2. Repo + szkielet dokumentacji | **gotowe** |
| 3. AdGuard Home + drugi DNS w routerze | **gotowe** |
| 4. Caddy + sieć `proxy` + domena wewnętrzna | **gotowe** |
| 5. Mealie | **gotowe** — wzorzec zwalidowany |
| 6. Backup restic | zablokowane brakiem HDD |
| 7. Monitoring | **gotowe** (2026-09-24): Uptime Kuma + Beszel |
| 8. Tailscale | **gotowe** (2026-09-24), świadomie przed krokiem 7, bo krok 6 stoi przez brak sprzętu |
| 9. Syncthing | nie rozpoczęte |

Istnieje `/srv/homelab/data/` z podkatalogami `adguard/`, `caddy/`, `mealie/`,
`uptime-kuma/`, `beszel/`, `dashboard-agent/`.
Nie istnieją `/mnt/hdd` ani `/mnt/hdd/backups` — czekają na podłączenie dysku.

## Znane odstępstwa i dług techniczny

- **`sudo` bez hasła** — `/etc/sudoers.d/90-cloud-init-users`:
  `figielak ALL=(ALL) NOPASSWD:ALL`. Kto zdobędzie klucz SSH, ma roota bez
  dodatkowej bariery. Pozostałość po cloud-init, nie świadoma decyzja.
  **Świadomie odłożone** 2026-09-21 — do rozważenia razem z passphrase na kluczu
  SSH, który chroni szerzej (nie tylko ten host). #do-zrobienia
- **Grupa `docker` = uprawnienia roota** — dostęp do `/var/run/docker.sock`
  pozwala zamontować `/` do kontenera. Przyjęte świadomie, bo `sudo docker`
  przy pracy z compose'em jest nieużywalne. Zobacz [[figielak]].
- **Brak jakiegokolwiek backupu, a dane nieodtwarzalne już są.** HDD nie jest
  podłączony, więc krok 6 stoi. Od 2026-09-21 [[mealie]] trzyma przepisy
  wpisane ręcznie — istnieją w jednym egzemplarzu, na jednym dysku.
  Pad SSD = ich utrata. To samo dotyczy książek wgranych do [[calibre-web]].
  **To najpoważniejsze otwarte ryzyko tego homelaba.**
  #do-zrobienia
- **Host na Wi-Fi** — `eth0` odłączony. Każde zapytanie DNS w domu idzie przez
  Wi-Fi. Rezerwacja DHCP jest przypięta do MAC-a `wlan0`;
  po przepięciu na kabel `eth0` dostanie inny adres i wymaga drugiej rezerwacji.
- **`castle` jest teraz pojedynczym punktem awarii DNS dla całego domu.**
  Router podaje `192.168.10.10` jako podstawowy resolver, `1.1.1.1` jako
  zapasowy. Awaria Pi oznacza brak filtrowania, ale nie brak internetu —
  to świadomie przyjęty kompromis.

## Parametry jądra

`/boot/firmware/cmdline.txt` ma dopisane:

```
cgroup_enable=memory cgroup_memory=1
```

**Bez tego `mem_limit` w stackach jest ignorowany.** Raspberry Pi OS domyślnie
wyłącza cgroup pamięci, a Docker przyjmuje wtedy `mem_limit` po cichu, bez
egzekwowania go. Objaw: `docker stats` pokazuje `0B / 0B` albo limit równy
całej pamięci hosta.

**Po włączeniu cgroupa istniejące kontenery trzeba odtworzyć**
(`docker compose up -d --force-recreate`). Sam restart hosta nie wystarczy —
kontener startuje z konfiguracją zapisaną przy jego tworzeniu.

Plik nie jest kopiowany do repo celowo: zawiera `root=PARTUUID=...` związany
z konkretnym dyskiem. Przy odbudowie na nowym sprzęcie dopisz same powyższe
parametry do istniejącej linii, nie nadpisuj całego pliku. Linia musi
pozostać jedna.

## Pliki systemowe w repo

Ręczne zmiany w konfiguracji systemu leżą w `hosts/castle/`, gdzie ścieżka
w repo odwzorowuje ścieżkę na hoście. Kopiowane ręcznie, w obie strony —
nie ma tu automatyki. Pliki mają być **bajtowo identyczne** z tymi na hoście,
dzięki czemu rozjazd wykrywa zwykły `diff`:

```bash
diff /opt/homelab/hosts/castle/etc/ssh/sshd_config.d/10-homelab-hardening.conf \
     /etc/ssh/sshd_config.d/10-homelab-hardening.conf
```

| Plik | Cel na hoście |
|---|---|
| `hosts/castle/etc/ssh/sshd_config.d/10-homelab-hardening.conf` | `/etc/ssh/sshd_config.d/` (właściciel `root`, `644`) |
| `hosts/castle/etc/sysctl.d/99-tailscale.conf` | `/etc/sysctl.d/` (właściciel `root`, `644`), potem `sudo sysctl --system` |

## Log zmian

Kolejność chronologiczna, najstarsze u góry.

- 2026-09-11 — sklonowane repo do `/opt/homelab` (deploy key read-only)
- 2026-09-21 — zebrany stan faktyczny hosta; rezerwacja DHCP `192.168.10.10`;
  ustalono, że `systemd-resolved` nie działa, więc port 53 jest wolny
- 2026-09-21 — wyłączone logowanie roota po SSH
  (`/etc/ssh/sshd_config.d/10-homelab-hardening.conf`)
- 2026-09-21 — zainstalowany Docker Engine 29.8.1 z oficjalnego repo
  (`download.docker.com/linux/debian trixie stable`) + Compose v5.5.1;
  `figielak` dodany do grupy `docker`; narzut ~61 MiB RAM
- 2026-09-21 — uruchomiony AdGuard Home `v0.107.79`; zajęte 53 tcp/udp i 3000 tcp;
  utworzone `/srv/homelab/data/adguard/` (właściciel `root`)
- 2026-09-21 — router przepięty na `castle` jako podstawowy DNS,
  `1.1.1.1` jako zapasowy; krok 3 zamknięty
- 2026-09-21 — uruchomiony Caddy (własny build 2.11.4 + cloudflare v0.2.4);
  zajęte 80 tcp, 443 tcp/udp; utworzona sieć `proxy`; wydany certyfikat
  wildcard `*.home.figielak.dev`; panel AdGuarda wystawiony przez proxy
- 2026-09-21 — włączony cgroup pamięci w `cmdline.txt` + EEPROM zaktualizowany
  do wersji z 2026-05-17 + restart. Kontenery odtworzone przez
  `--force-recreate`, `mem_limit` wreszcie egzekwowany — wcześniej limity
  w obu stackach były martwe. Zmierzone: AdGuard 76 MiB, Caddy 55 MiB
- 2026-09-21 — uruchomiony Mealie `v3.27.0` za Caddy jako
  `mealie.home.figielak.dev`; dane w `/srv/homelab/data/mealie` (UID 1000).
  Pierwsza usługa z danymi nie do odtworzenia — backupu nadal brak
- 2026-09-21 — `Caddyfile` przeniesiony do `stacks/caddy/config/`
  i montowany jako katalog; rejestr portów zweryfikowany przez `ss`
- 2026-09-24 — publiczny wildcard A `*.home.figielak.dev → 192.168.10.10`
  w Cloudflare; zapasowy DNS z routera dawał NXDOMAIN dla usług
- 2026-09-24 — Tailscale `1.102.4` na hoście, subnet route `192.168.10.10/32`;
  zajęte 41641/udp, ~60 MiB RAM; krok 8 przed 7, świadomie
- 2026-09-24 — uruchomiony Uptime Kuma `2.5.5-slim-rootless` za Caddy jako
  `uptime-kuma.home.figielak.dev`; alerty przez ntfy; ~122 MiB RAM
- 2026-09-24 — uruchomiony Beszel `0.20.0` (hub + agent + socket proxy);
  zajęte `127.0.0.1:2375`; krok 7 zamknięty
- 2026-09-24 — uruchomiony `dashboard-agent` (push statystyk na figielak.dev
  co 60 s), ~13 MiB RAM; retencja statystyk AdGuarda zmieniona na 7 dni
- 2026-09-25 — uruchomiony Calibre-Web `0.6.27-ls402` za Caddy jako
  `calibre.home.figielak.dev`; bez portów na hoście; ~203 MiB RAM
- 2026-09-25 — uruchomiony MeTube `2026.09.25` za Caddy (`basic_auth`) jako
  `metube.home.figielak.dev`; pobrania na SSD do czasu HDD; ~65 MiB RAM w spoczynku
