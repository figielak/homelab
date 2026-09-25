# AdGuard Home

DNS dla całej sieci domowej z blokowaniem reklam i trackerów. Pełni też rolę
wewnętrznego resolvera dla `*.home.figielak.dev` (DNS rewrite → [castle](../hosts/castle.md)).

#usługa #dns

## Dlaczego akurat to

Alternatywą był Pi-hole. AdGuard wybrany, bo ma wbudowaną obsługę DoH/DoT
po stronie upstreamu bez dokładania drugiego kontenera, konfigurację trzyma
w jednym pliku YAML (łatwo backupować i odtworzyć) i nie wymaga osobnego
serwera DHCP, żeby sensownie działać.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| Panel | `https://adguard.home.figielak.dev` przez [caddy](caddy.md); nadal osiągalny też bezpośrednio na `http://192.168.10.10:3000` |
| Porty | 53 tcp/udp (DNS), 3000 tcp (panel) |
| Dane | `/srv/homelab/data/adguard/{work,conf}` |
| Stack | `stacks/adguard/` |
| Obraz | `adguard/adguardhome:v0.107.79` |
| RAM | `mem_limit` 256 MiB, **zmierzone ~50 MiB** (2026-09-21, świeża instalacja) |
| Sieć | `network_mode: host` — **nie należy do sieci `proxy`** |

## Zależności

- **Zależy od:** Dockera i samego hosta. Nic poza tym — musi wstać jako pierwszy.
- **Zależy od niej:** każde urządzenie w sieci domowej, o ile router podaje
  `192.168.10.10` jako DNS. Także rozwiązywanie `*.home.figielak.dev`,
  czyli dostęp do wszystkich usług po nazwie — bez AdGuarda nie działa
  ani [caddy](caddy.md), ani nic za nim.

**`castle` celowo nie używa AdGuarda jako własnego resolvera.** Host zostaje
przy zewnętrznym DNS z NetworkManagera. Inaczej powstaje pętla: kontener nie
wstaje → host traci DNS → `docker pull` nie działa → nie da się naprawić
AdGuarda bez ręcznej edycji `/etc/resolv.conf`. Kosztem jest brak filtrowania
zapytań z samego Pi — czyli głównie `apt update`.

## Co backupować

Wystarczy katalog `/srv/homelab/data/adguard/`. Najważniejszy jest
`conf/AdGuardHome.yaml` — zawiera całą konfigurację: upstreamy, listy
blokujące, reguły, rewrity i **hash hasła administratora**.

Katalog `work/` trzyma statystyki i log zapytań. Przy odtworzeniu nie jest
konieczny — stracisz historię, nie konfigurację.

**Dane należą do `root` (0:0), nie do `figielak`.** Kontener AdGuarda działa
jako root i sam ustawia właściciela; `AdGuardHome.yaml` ma tryb `600`.
Backup musi zachowywać właściciela i uprawnienia numerycznie — restic robi to
domyślnie, pod warunkiem że odtwarzasz jako root. **Nie rób `chown` na 1000**
po odtworzeniu: AdGuard i tak zapisuje jako root, a rozjazd uprawnień na pliku
z hashem hasła to niepotrzebne ryzyko.

## Procedura odtworzenia od zera

Zakłada działający host z Dockerem i wolny port 53.

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalogi danych — wlascicielem zostaje root, kontener dziala jako root
sudo mkdir -p /srv/homelab/data/adguard/{work,conf}

# 3. konfiguracja stacku
cd /opt/homelab/stacks/adguard
cp .env.example .env

# 4a. ODTWORZENIE Z BACKUPU — wgraj AdGuardHome.yaml przed pierwszym startem
#     sudo cp -a <backup>/conf/AdGuardHome.yaml /srv/homelab/data/adguard/conf/
#     sudo chown 0:0 /srv/homelab/data/adguard/conf/AdGuardHome.yaml
#     sudo chmod 600 /srv/homelab/data/adguard/conf/AdGuardHome.yaml

# 5. start
docker compose config    # sprawdza skladnie i podstawienie zmiennych
docker compose up -d
docker compose ps
```

Jeśli `conf/AdGuardHome.yaml` istnieje, AdGuard startuje od razu
z pełną konfiguracją i pomija kreator. Jeśli nie — patrz niżej.

### Pierwsza instalacja (bez backupu)

Kreator jest dostępny na `http://192.168.10.10:3000`.

**W kroku „Admin Web Interface" ustaw port na 3000, nie 80.** Domyślną
propozycją kreatora jest 80, a ten port jest zarezerwowany dla Caddy —
przyjęcie domyślnej wartości sprawi, że Caddy nie wstanie.

Nasłuch DNS zostaw na wszystkich interfejsach (port 53).

Po kreatorze: hasło administratora do menedżera haseł, wpis „Homelab AdGuard".

### Przepięcie sieci na AdGuarda

W routerze ustaw DNS:

1. **Podstawowy:** `192.168.10.10` (castle)
2. **Zapasowy:** publiczny resolver, np. `1.1.1.1`

Drugi wpis jest świadomym kompromisem: gdy Pi padnie, reklamy przestają być
blokowane, ale internet w domu działa. Bez niego restart Pi odcina całą sieć.

Weryfikacja z dowolnego urządzenia:

```bash
dig @192.168.10.10 example.com +short
dig @192.168.10.10 doubleclick.net +short    # powinno zwrocic 0.0.0.0 lub nic
```

## Znane problemy i ograniczenia

- **Tryb `host` wyklucza sieć `proxy`.** Caddy nie dosięgnie kontenera po
  nazwie. W `Caddyfile` idzie przez adres hosta — `{$HOST_IP}:3000`,
  gdzie `HOST_IP` pochodzi z `.env` stacku Caddy.
- **Panel na porcie 3000 jest osiągalny bezpośrednio**, z pominięciem Caddy.
  Wynika to z trybu `host` i nie da się tego obejść bez firewalla.
- **DNS idzie przez Wi-Fi** — `castle` nie ma podłączonego kabla. Każde
  zapytanie w domu zależy od jakości połączenia bezprzewodowego Pi.
- Zmiana konfiguracji przez panel **nie trafia do Git**. Źródłem prawdy jest
  `AdGuardHome.yaml` na hoście, chroniony backupem — nie repozytorium.

## Log zmian

- 2026-09-21 — stack utworzony, obraz `v0.107.79` (arm64 potwierdzony)
- 2026-09-21 — uruchomiony, status `healthy`, zajmuje 53 tcp/udp na wszystkich
  interfejsach; zużycie ~50 MiB; upstream Quad9 (`9.9.9.9`, `149.112.112.112`);
  ustalono, że dane należą do `root`, nie do UID 1000
- 2026-09-21 — router przepięty: AdGuard jako podstawowy DNS dla całej sieci,
  `1.1.1.1` jako zapasowy; rozwiązywanie zweryfikowane przez `dig`
- 2026-09-21 — dodany DNS rewrite `*.home.figielak.dev` → `192.168.10.10`;
  panel wystawiony przez [caddy](caddy.md) pod `adguard.home.figielak.dev`
