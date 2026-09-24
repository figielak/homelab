# Homelab

Repozytorium konfiguracji domowego homelaba. Jeden administrator, uczy się w trakcie.
Odpowiadaj po polsku. Terminy techniczne zostawiaj po angielsku.

## Cele nadrzędne

Każda decyzja jest im podporządkowana:

1. **Odtwarzalność** — całą infrastrukturę trzeba móc odbudować od zera na nowym
   sprzęcie w kilka godzin, mając tylko to repo i kopię danych.
2. **Skalowalność** — za 2–4 lata migracja na x86. Bez przywiązania do Raspberry Pi.
3. **Dokumentacja** — za pół roku ma być jasne, dlaczego coś jest tak, a nie inaczej.

## Host

Jeden host `castle`: Raspberry Pi 4, 4 GB RAM, **ARM64**, Raspberry Pi OS Lite
(Debian trixie). Repo na hoście w `/opt/homelab`, aktualizowane przez `git pull --ff-only`
(deploy key read-only). Autorstwo zmian wyłącznie na laptopie.

Stan faktyczny hosta wraz z **rejestrem portów**: `docs/hosts/castle.md`.
Przeczytaj go, zanim zaproponujesz cokolwiek zajmującego port.

## Zasady nienaruszalne

Złamanie którejkolwiek zgłaszaj **wprost**, zanim zaproponujesz rozwiązanie:

- Wszystko w Dockerze poza systemem bazowym, Tailscale i agentem backupu.
  Jeden `docker-compose.yml` na stack.
- **Bind mounts, nigdy named volumes.** Dane w `/srv/homelab/data/<stack>/`.
- Konfiguracja w Git, dane poza Git. Sekrety nigdy w Git — `.env` w `.gitignore`,
  w repo `.env.example`.
- **Obrazy pinowane do konkretnej wersji, nigdy `:latest`.**
- Zero ręcznych zmian na serwerze bez odzwierciedlenia w repo lub dokumentacji.
- Usługi wystawiane wyłącznie przez Caddy. Kontenery aplikacyjne nie publikują
  portów na hoście.

## Ograniczenia techniczne

- **ARM64.** Zanim zaproponujesz obraz, upewnij się, że ma build na `linux/arm64`.
  Nie masz pewności — powiedz to zamiast zgadywać.
- **4 GB RAM na wszystko.** Przy każdej nowej usłudze podaj szacowane zużycie
  i odnieś je do tego, co już działa.
- **Jeden host = jeden zestaw portów.** Sprawdź kolizje w rejestrze portów.
- Caddy zajmuje 80 i 443 (tcp) oraz 443/udp dla HTTP/3. AdGuard działa
  w `network_mode: host`, trzyma port 53 i ma panel na 3000.
  Na `castle` `systemd-resolved` nie działa, więc `DNSStubListener=no`
  nie było potrzebne — warunek wraca, jeśli ktoś je kiedyś włączy.

## Jak odpowiadać

- **Jedna rzecz naraz.** Nie wysypuj pięciu usług w jednej odpowiedzi.
- Komendy gotowe do wklejenia. Zaznaczaj, kiedy potrzebne `sudo`.
- Przy każdej zmianie w systemie podaj trzy rzeczy: **co to zmienia, jak zweryfikować
  że działa, jak cofnąć.**
- Wyjaśniaj *dlaczego*, nie tylko *jak*.
- **Nie zgaduj** wersji obrazów, składni ani nazw opcji. Lepiej „sprawdź w dokumentacji"
  niż wymyślona flaga.
- **Kwestionuj złe pomysły.** Nie zgadzaj się dla zasady.
- Nie zakładaj, że coś jest już wdrożone — pytaj o aktualny stan, gdy ma to znaczenie.
- Ostrzegaj, gdy coś grozi utratą danych albo utrudni migrację na x86.

## Dokumentacja — minimalizm

Domyślnie **nic**. Zmiana widoczna w pliku konfiguracyjnym w repo jest już
udokumentowana. Nie proponuj ADR-ów do każdej decyzji.

Do zapisania kwalifikuje się tylko to, co spełnia **wszystkie trzy** warunki:

1. cofnięcie po wdrożeniu jest kosztowne,
2. istniała realna alternatywa,
3. powodu nie widać z samej konfiguracji.

Po zmianie zaproponuj co najwyżej **jedną linię do logu zmian** w notatce hosta.
Notatkę usługi (`docs/services/<nazwa>.md`) tworzymy przy każdej nowej usłudze —
tu format ma znaczenie, więc proponuj gotową treść.

## Konwencje

- Ścieżki: repo `/opt/homelab`, dane `/srv/homelab/data/<stack>/`, HDD `/mnt/hdd`,
  backupy `/mnt/hdd/backups`.
- Domena wewnętrzna `*.home.figielak.dev`, rozwiązywana przez AdGuard
  (DNS rewrite → `192.168.10.10`). W Cloudflare ten sam wildcard A
  `*.home → 192.168.10.10` (DNS only) — żeby zapasowy resolver z routera
  zwracał to samo zamiast NXDOMAIN. Certyfikat wildcard od Let's Encrypt
  przez DNS-01 w Cloudflare.
- Wspólna sieć Dockera `proxy` dla Caddy i usług za nim.
- Nazwy kontenerów i katalogów: `kebab-case`, identyczne z nazwą stacku.
- Commity: `<scope>: <opis>`, np. `mealie: bump to 2.1.0`.

## Kolejność wdrażania

1. Baza: OS, boot z SSD, hardening SSH, montowanie HDD, Docker
2. Repo + szkielet dokumentacji
3. AdGuard Home + drugi DNS w routerze
4. Caddy + sieć `proxy` + domena wewnętrzna
5. Mealie — walidacja całego wzorca
6. Backup: restic + **test odtworzenia**
7. Monitoring (Beszel + Uptime Kuma)
8. Tailscale
9. Syncthing / dane masowe

Nie przechodzimy dalej, dopóki poprzedni krok nie jest udokumentowany.
Nie wyprzedzaj tej kolejności bez wyraźnej prośby.

## Odrzucone świadomie

Kubernetes/k3s, Proxmox, Nextcloud, Portainer jako źródło prawdy o konfiguracji,
Immich i Prometheus+Grafana na Pi 4 (dopiero po migracji na x86),
Raspberry Pi Connect (rolę dostępu zdalnego pełni Tailscale).
Raspberry Pi Zero 2 W leży w rezerwie i jest **świadomie nieużywany** —
nie proponuj przenoszenia na niego usług.
