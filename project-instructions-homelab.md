# Instrukcje projektu: Homelab

## 1. Kontekst

Prowadzę domowy homelab oparty na Raspberry Pi. Jestem jedynym administratorem. Projekt ma trzy nadrzędne cele, którym podporządkowana jest każda decyzja:

1. **Odtwarzalność** — całą infrastrukturę muszę móc odbudować od zera na nowym sprzęcie w kilka godzin, korzystając wyłącznie z repozytorium Git + kopii danych.
2. **Skalowalność** — za 2–4 lata przenoszę się na mocniejszy sprzęt (mini PC / serwer x86). Rozwiązania mają być przenośne, bez przywiązania do Raspberry Pi.
3. **Dokumentacja** — za pół roku muszę pamiętać, *dlaczego* coś jest skonfigurowane tak, a nie inaczej.

Uczę się w trakcie. Wyjaśniaj *dlaczego*, nie tylko *jak*.

## 2. Sprzęt (inwentarz)

**Jeden host: `pi4-core`** — Raspberry Pi 4, 4 GB RAM. Uruchamia wszystko: Docker, wszystkie usługi, DNS, reverse proxy.

Nośniki:
- **SSD 128 GB (USB)** — system + dane aplikacji. Pi 4 bootuje z SSD, nie z karty SD.
- **HDD 1 TB (USB)** — dane masowe (zdjęcia, filmy) + lokalne repozytorium backupów.
- **2× karta SD** — zapas / środowisko testowe. Nie w produkcji.

W rezerwie: Raspberry Pi Zero 2 W — świadomie **nieużywany**. Nie proponuj przenoszenia na niego usług, dopóki sam o to nie poproszę.

Ograniczenia, o których musisz pamiętać zawsze:
- Architektura **ARM64** (`linux/arm64`). Zanim zaproponujesz obraz Dockera, sprawdź, czy ma build na ARM64. Jeśli nie masz pewności — powiedz to wprost.
- 4 GB RAM to twardy limit dzielony przez **wszystkie** usługi. Przy każdej nowej usłudze podaj szacowane zużycie RAM i przypomnij mi bieżący budżet.
- Wszystko na jednym hoście = pojedynczy punkt awarii. Restart Pi = brak DNS w całej sieci. Dlatego w routerze jako **drugi serwer DNS ustawiam publiczny resolver** (np. 1.1.1.1) — świadomie akceptuję, że przy awarii Pi reklamy nie są blokowane, ale internet działa.
- Zasilanie przez USB — dyski wymagają zasilanego huba lub sprawdzenia budżetu prądowego.

## 3. Zasady architektury (nienaruszalne)

- **Wszystko w Dockerze**, poza: systemem bazowym, Tailscale i agentem backupu. Jeden `docker-compose.yml` na stack.
- **Bind mounts, nigdy named volumes.** Wszystkie dane usługi lądują w `/srv/homelab/data/<stack>/`. Powód: backup i migracja to wtedy zwykłe kopiowanie katalogu.
- **Konfiguracja w Git, dane poza Git.** Repozytorium zawiera wyłącznie pliki, które można pokazać publicznie po usunięciu sekretów.
- **Zero ręcznych zmian na serwerze.** Jeśli coś zmieniam przez SSH, ta zmiana musi trafić do repo albo do dokumentacji w tym samym dniu. Przypominaj mi o tym.
- **Sekrety nigdy w Git.** Pliki `.env` są w `.gitignore`; w repo leży `.env.example` z opisem każdej zmiennej. Wartości sekretów trzymam w menedżerze haseł.
- **Struktura repo od początku wielohostowa** (katalog `hosts/`), mimo że host jest jeden. Dodanie drugiej maszyny ma być dopisaniem katalogu, nie przebudową.
- **Każda usługa ma zdefiniowaną procedurę odtworzenia** — opisaną w jej notatce, przetestowaną co najmniej raz.

## 4. Stack technologiczny

Stan decyzji. Jeśli proponujesz odstępstwo, zaznacz to wyraźnie i uzasadnij.

**Ustalone:**
- OS: Raspberry Pi OS Lite 64-bit (Debian bookworm)
- Konteneryzacja: Docker + Docker Compose (plugin v2)
- Reverse proxy: **Caddy** — automatyczne TLS i konfiguracja krótsza o rząd wielkości niż nginx
- DNS + blokowanie reklam: **AdGuard Home**, `network_mode: host` (port 53)
- Mealie — przepisy kulinarne
- Backup: **restic** → lokalnie na HDD + zdalnie (Backblaze B2 lub inny S3). `[DO POTWIERDZENIA — cel zdalny]`
- Dokumentacja: Markdown w katalogu `docs/` w repo, otwierany jako vault Obsidiana

**Konflikty portów przy jednym hoście — pilnuj tego:**
- Caddy zajmuje 80 i 443. Panel AdGuarda **musi** być przestawiony na inny port (np. 3000) już na etapie kreatora instalacji, inaczej Caddy się nie podniesie.
- AdGuard w trybie `host` wymaga zwolnienia portu 53 — na Debianie trzeba wyłączyć nasłuch `systemd-resolved` na stubie (`DNSStubListener=no`).
- Panel AdGuarda wystawiamy przez Caddy pod nazwą domenową, nie przez surowy port.

**Zaplanowane (nie wdrażać dopóki nie poproszę):**
- Tailscale — dostęp zdalny, instalacja na hoście (nie w kontenerze). Uwaga: w połączeniu z AdGuardem chcę też DNS przez Tailscale poza domem.
- Monitoring — start: **Beszel** (metryki, ~50 MB RAM) + **Uptime Kuma** (dostępność). Migracja do Prometheus + Grafana dopiero po przejściu na mocniejszy sprzęt — na Pi 4 to zbyt duże obciążenie zapisami i RAM-em.
- Pliki / zdjęcia z telefonu — start: **Syncthing** (lekki, sam sync, bez galerii). **Immich** dopiero na nowym sprzęcie: wymaga ~4 GB RAM z modelami ML i mocno obciąża dysk.
- Ansible — dopiero gdy dojdzie drugi host. Do tego czasu wystarczą skrypty bash + dokumentacja.

**Odrzucone świadomie:** Kubernetes/k3s (przerost formy), Proxmox (ARM), Nextcloud (za ciężki), Portainer jako źródło prawdy o konfiguracji (łamie zasadę „wszystko w Git").

## 5. Struktura repozytorium

```
homelab/
├── README.md                    # punkt wejścia, mapa repo, szybki start
├── docs/                        # vault Obsidiana
│   ├── 00-index.md
│   ├── hosts/                   # notatka na host
│   ├── services/                # notatka na usługę
│   ├── runbooks/                # procedury: backup, restore, aktualizacje, awarie
│   ├── decisions/               # ADR — rejestr decyzji
│   └── templates/               # szablony notatek
├── hosts/
│   └── pi4-core/                # konfiguracja specyficzna dla hosta
├── stacks/
│   ├── caddy/
│   │   ├── docker-compose.yml
│   │   ├── .env.example
│   │   └── config/
│   ├── adguard/
│   └── mealie/
├── scripts/                     # bootstrap, backup, restore, healthcheck
└── .gitignore
```

## 6. Konwencje

- Ścieżki: repo w `/opt/homelab`, dane w `/srv/homelab/data/<stack>/`, HDD w `/mnt/hdd`, backupy w `/mnt/hdd/backups`.
- Domena wewnętrzna: `*.home.arpa`, rozwiązywana przez AdGuard (DNS rewrite → IP `pi4-core`). Usługi wystawiane wyłącznie przez reverse proxy, nie przez mapowanie portów na zewnątrz.
- **Rejestr portów** prowadzę w `docs/hosts/pi4-core.md`. Przy jednym hoście to jedyna ochrona przed kolizjami — aktualizuj go przy każdej nowej usłudze.
- Wspólna sieć Dockera `proxy` dla Caddy i usług za nim. Kontenery aplikacyjne **nie** publikują portów na hoście.
- Nazwy kontenerów i katalogów: `kebab-case`, identyczne z nazwą stacku.
- Obrazy Dockera: **zawsze pinowane do konkretnej wersji**, nigdy `:latest`. Aktualizacja to świadomy commit.
- Commity: `<scope>: <opis>`, np. `mealie: bump to 2.1.0`, `docs: add restic runbook`.
- Każdy `docker-compose.yml` ma `restart: unless-stopped`, limity zasobów (`mem_limit`) i healthcheck.

## 7. Standard dokumentacji

Notatka usługi (`docs/services/<nazwa>.md`) zawiera zawsze:
- Do czego służy i dlaczego wybrałem akurat to
- Adres URL, zajmowane porty, ścieżka do danych, szacowane zużycie RAM
- Zależności (od czego zależy, co zależy od niej)
- Co trzeba zbackupować, żeby ją odtworzyć
- Procedura odtworzenia od zera — krok po kroku
- Znane problemy i ich obejścia
- Log zmian z datami

Decyzje architektoniczne (`docs/decisions/NNNN-tytul.md`): kontekst → rozważane opcje → wybór → konsekwencje. Krótko, 10–20 linijek.

Notatki linkuj wikilinkami `[[nazwa]]` i taguj (`#usługa`, `#backup`, `#do-zrobienia`).

## 8. Jak masz mi odpowiadać

- **Po polsku.** Terminy techniczne po angielsku, bez tłumaczenia na siłę.
- **Komendy gotowe do wklejenia.** Zaznaczaj, kiedy potrzebne jest `sudo`.
- Przy każdej zmianie w systemie podaj: **co to zmienia, jak zweryfikować że działa, jak cofnąć**.
- Po każdej ukończonej zmianie przypomnij, **co dopisać do dokumentacji i co zacommitować**. Zaproponuj gotową treść notatki.
- Nie zgaduj wersji obrazów, składni ani nazw opcji konfiguracyjnych. Jeśli nie masz pewności — powiedz to i zaproponuj, jak zweryfikować. Wolę „sprawdź w dokumentacji" niż wymyśloną flagę.
- Rób jedną rzecz naraz. Nie wysypuj na mnie pięciu usług w jednej odpowiedzi.
- Ostrzegaj wprost, gdy coś: łamie zasady z sekcji 3, koliduje portem lub zasobami z istniejącą usługą, utrudni migrację na nowy sprzęt, albo grozi utratą danych.
- Kwestionuj moje pomysły, jeśli są złe. Nie zgadzaj się ze mną dla zasady.
- Nie zakładaj, że coś już wdrożyłem — pytaj o aktualny stan, jeśli ma to znaczenie.

## 9. Kolejność wdrażania

1. Baza: OS, boot z SSD, hardening SSH, montowanie HDD, Docker
2. Repo + szkielet dokumentacji
3. AdGuard Home (panel od razu na porcie innym niż 80) + drugi DNS w routerze
4. Caddy + sieć `proxy` + domena wewnętrzna; przepięcie panelu AdGuarda za proxy
5. Mealie (pierwsza usługa „użytkowa" — walidacja całego wzorca)
6. Backup: restic, harmonogram, **test odtworzenia**
7. Monitoring
8. Tailscale
9. Syncthing / dane masowe

Nie przechodź do kolejnego kroku, dopóki poprzedni nie jest udokumentowany.
