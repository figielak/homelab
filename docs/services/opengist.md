# Opengist

Samodzielnie hostowany odpowiednik GitHub Gist: snippety, notatki, pliki
konfiguracyjne z podświetlaniem składni i wyszukiwaniem. Każdy gist to osobne
repozytorium git, więc da się go sklonować, edytować lokalnie i wypchnąć.

Wdrożony **poza kolejnością** z `CLAUDE.md`, na wyraźną prośbę.

#usługa

## Dlaczego akurat to

Jeden binarny plik Go na SQLite, bez osobnej bazy i bez zależności. Na Pi 4 to
jedna z najtańszych usług w tym homelabie. Dane nie są zamknięte w żadnym
formacie: gist to zwykłe repo git w `repos/`, więc da się je wyciągnąć nawet
bez działającego Opengista.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| URL | `https://opengist.home.figielak.dev` przez [caddy](caddy.md) |
| Git | `git clone https://opengist.home.figielak.dev/<user>/<gist>.git`, tylko HTTPS |
| Port | 6157 **wyłącznie wewnątrz sieci `proxy`**, nic na hoście |
| Dane | `/srv/homelab/data/opengist/` (właściciel `figielak`, UID 1000) |
| Stack | `stacks/opengist/` |
| Obraz | `ghcr.io/thomiceli/opengist:1.15.2` (manifest ma `arm64`) |
| RAM | `mem_limit` 256 MiB, `GOMEMLIMIT` 200 MiB; **zmierzone ~90 MiB** (2026-09-25, pusta instancja) |

Zawartość katalogu danych:

| Ścieżka | Zawartość | Backup |
|---|---|---|
| `opengist.db` (+ `-wal`, `-shm`) | użytkownicy, metadane gistów, ustawienia z panelu admina | **tak** |
| `repos/` | gołe repozytoria git, jedno na gist: właściwa treść | **tak** |
| `opengist-secret.key` | klucz sesji i szyfrowania danych MFA w bazie | **tak**, bez niego MFA z backupu nie zadziała |
| `opengist.index/` | indeks wyszukiwania bleve | nie, odbudowuje się z repozytoriów |

### Dlaczego bez SSH

Wbudowany serwer SSH Opengista wymaga opublikowania portu 2222 na hoście,
a kontenery aplikacyjne portów nie publikują. Tryb `host` (przez systemowy
OpenSSH na porcie 22) wymaga osobnego konta systemowego i `AuthorizedKeysCommand`,
czyli zmian w systemie bazowym dla wygody. Git przez HTTPS robi to samo:
push wymaga loginu i hasła albo tokenu dostępu (Settings → Access tokens).

## Zależności

- **Zależy od:** [caddy](caddy.md) (dostęp po nazwie i TLS), [adguard](adguard.md) (rozwiązywanie
  nazwy), sieci `proxy`.
- **Zależy od niego:** nic.

## Co backupować

Cały katalog `/srv/homelab/data/opengist/` poza `opengist.index/`.

**SQLite w trybie WAL.** Ta sama uwaga co przy [mealie](mealie.md): kopia działającej bazy
może być niespójna. Przy restic albo zatrzymujemy kontener, albo robimy
`sqlite3 .backup` dla `opengist.db`. Repozytoria w `repos/` kopiują się bezpiecznie,
dopóki nikt w tej chwili nie pushuje.

**Kopii zapasowej dziś nie ma** (HDD niepodłączony, krok 6 stoi).

## Procedura odtworzenia od zera

```bash
# 1. repo
cd /opt/homelab && git pull --ff-only

# 2. katalog danych — entrypoint i tak zrobi chown na UID 1000,
#    ale tworzymy go jawnie, zeby nie powstal jako root przez Dockera
sudo mkdir -p /srv/homelab/data/opengist
sudo chown 1000:1000 /srv/homelab/data/opengist

# 3. przy odtwarzaniu: dane z backupu PRZED pierwszym startem,
#    inaczej Opengist wygeneruje nowy opengist-secret.key
#    sudo cp -a <backup>/opengist/. /srv/homelab/data/opengist/

# 4. konfiguracja stacku
cd /opt/homelab/stacks/opengist
cp .env.example .env

# 5. start
docker compose config
docker compose up -d
docker compose logs -f
```

### Wystawienie przez proxy

Blok w `stacks/caddy/config/Caddyfile`:

```caddyfile
@opengist host opengist.home.figielak.dev
handle @opengist {
	reverse_proxy opengist:6157
}
```

```bash
cd /opt/homelab/stacks/caddy
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Pierwsze logowanie

**Pierwsze założone konto zostaje adminem.** Do czasu wyłączenia rejestracji
każdy w sieci domowej i w tailnecie może założyć konto, więc rób to od razu
po starcie.

1. Zarejestruj konto, hasło do menedżera haseł jako „Homelab Opengist”.
2. Admin → Configuration → włącz **Disable signup**. Ustawienie żyje w bazie,
   nie w compose: przy odtworzeniu bez backupu trzeba je włączyć ponownie.
3. Opcjonalnie **Require login**: bez tego gisty publiczne widzi każdy w sieci
   domowej bez logowania. Prywatne i niepubliczne gisty są chronione niezależnie
   od tego ustawienia.

## Znane problemy i ograniczenia

- **Zablokowany admin**: reset hasła i nadanie uprawnień admina działa z CLI
  w kontenerze (`./opengist admin ...`, dokumentacja: *Reset password*,
  *Manage admins*).
- **SQLite tylko na dysku lokalnym.** Nie przenoś katalogu danych na NFS/SMB.

## Log zmian

- 2026-09-25 — stack utworzony, obraz `1.15.2`, SSH wyłączony, wystawiony
  przez [caddy](caddy.md) pod `opengist.home.figielak.dev`
