# Mealie

Menedżer przepisów kulinarnych. Importuje przepisy z adresu URL, planuje
posiłki i generuje listy zakupów.

Pierwsza usługa „użytkowa" w homelabie — waliduje cały wzorzec: sieć `proxy`,
bind mount, wpis w `Caddyfile`, certyfikat z wildcardu.

#usługa

## Dlaczego akurat to

Alternatywą był Tandoor. Mealie wybrany, bo działa sensownie na SQLite (bez
osobnego kontenera z bazą, co przy 4 GB RAM ma znaczenie), ma czytelny import
przepisów z linku i wygodną aplikację webową na telefonie.

Tandoor był wcześniej uruchamiany w poprzedniej wersji homelaba i został
odstawiony.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| URL | `https://mealie.home.figielak.dev` przez [caddy](caddy.md) |
| Port | 9000 **wyłącznie wewnątrz sieci `proxy`** — nic na hoście |
| Dane | `/srv/homelab/data/mealie/` (właściciel `figielak`, UID 1000) |
| Stack | `stacks/mealie/` |
| Obraz | `ghcr.io/mealie-recipes/mealie:v3.27.0` |
| RAM | `mem_limit` 1 GiB |
| Baza | SQLite — `data/mealie.db` |

## Dlaczego SQLite, a nie PostgreSQL

Dokumentacja Mealie podaje SQLite jako odpowiedni dla 1–20 użytkowników.
Tutaj użytkowników jest kilku w jednym domu.

Zysk jest podwójny: nie ma drugiego kontenera zjadającego pamięć z twardego
limitu 4 GB, a backup sprowadza się do skopiowania jednego katalogu, zamiast
zrzutu bazy skoordynowanego z resztą danych.

**Ograniczenie:** dane muszą leżeć na dysku lokalnym. SQLite na zasobie
sieciowym (NFS/SMB) grozi uszkodzeniem bazy i blokadami. Przy ewentualnym
przenoszeniu danych na NAS ta usługa musi zostać na dysku lokalnym.

## Zależności

- **Zależy od:** [caddy](caddy.md) (dostęp po nazwie i TLS), [adguard](adguard.md) (rozwiązywanie
  `mealie.home.figielak.dev`), sieci `proxy`.
- **Zależy od niej:** nic.

Awaria Mealie nie dotyka niczego innego. Awaria Caddy lub AdGuarda czyni
Mealie nieosiągalnym, mimo że kontener działa.

## Co backupować

Cały katalog `/srv/homelab/data/mealie/` — baza, zdjęcia przepisów i pliki
użytkowników są w jednym miejscu.

**Uwaga przy SQLite:** kopiowanie pliku bazy w trakcie zapisu może dać
niespójny backup. Przy wdrażaniu restica (krok 6) trzeba albo zatrzymać
kontener na czas kopii, albo użyć `sqlite3 .backup`. Zwykłe `cp` działającej
bazy to proszenie się o kopię, która odtworzy się do błędu.

To pierwsza usługa w tym homelabie, która ma dane **nie do odtworzenia** —
ręcznie wpisanych przepisów nikt nie wygeneruje ponownie.

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalog danych — wlascicielem musi byc UID 1000 (PUID w compose)
sudo mkdir -p /srv/homelab/data/mealie
sudo chown -R 1000:1000 /srv/homelab/data/mealie

# 3. konfiguracja stacku
cd /opt/homelab/stacks/mealie
cp .env.example .env

# 4. ODTWORZENIE Z BACKUPU — przed pierwszym startem
#    sudo cp -a <backup>/mealie/. /srv/homelab/data/mealie/
#    sudo chown -R 1000:1000 /srv/homelab/data/mealie

# 5. start
docker compose config
docker compose up -d
docker compose logs -f
```

Pierwszy start wykonuje migracje bazy i trwa dłużej — stąd `start_period: 90s`
w healthchecku.

### Wystawienie przez proxy

Blok w `stacks/caddy/config/Caddyfile` jest już na miejscu:

```caddyfile
@mealie host mealie.home.figielak.dev
handle @mealie {
	reverse_proxy mealie:9000
}
```

Po zmianie w `Caddyfile`:

```bash
cd /opt/homelab/stacks/caddy
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

Certyfikat wildcard obejmuje tę nazwę automatycznie — nic nie trzeba wydawać.
DNS rewrite w AdGuardzie też już działa dla `*.home.figielak.dev`.

### Pierwsze logowanie

Domyślne konto: `changeme@example.com` / `MyPassword`.

**Zmień je natychmiast po pierwszym zalogowaniu.** `ALLOW_SIGNUP` jest
wyłączone, więc kolejne konta zakładasz z panelu administratora.
Hasło do menedżera haseł, wpis „Homelab Mealie".

## Znane problemy i ograniczenia

- **`BASE_URL` musi się zgadzać z adresem w przeglądarce.** Przy niezgodności
  Mealie generuje linki na zły adres — widać to przy udostępnianiu przepisów
  i w mailach.
- **Bez konfiguracji SMTP nie działa reset hasła ani zaproszenia użytkowników.**
  Świadomie pominięte; konta zakłada administrator ręcznie.
- **Import przepisu z linku wymaga internetu** i nie radzi sobie z każdą stroną.

## Log zmian

- 2026-09-21 — stack utworzony, obraz `v3.27.0`, SQLite, wystawiony przez
  [caddy](caddy.md) pod `mealie.home.figielak.dev`
