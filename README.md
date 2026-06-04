## Informacje

Self-hosted homelab oparty na Docker Compose. Każda usługa ma własny katalog w `services/` z plikiem `docker-compose.yml` i `.env`.

Dane wszystkich usług trzymane są w katalogu `data/` w głównym folderze projektu (wyjątek: NPM trzyma dane lokalnie w `services/nginx-proxy/data/`).

## Instalacja

1. Zainstaluj Docker i Docker Compose
2. Sklonuj repozytorium
3. Dla każdej usługi skopiuj `.env.example` do `.env` i uzupełnij wartości
4. Uruchom usługi zgodnie z sekcją poniżej

## Uruchamianie usług

**Najpierw zawsze uruchom NPM** — tworzy sieć `proxy` wymaganą przez pozostałe usługi:

```bash
cd services/nginx-proxy
docker compose up -d
```

**Uruchomienie pojedynczej usługi:**

```bash
cd services/<nazwa>
docker compose up -d
```

**Zatrzymanie usługi:**

```bash
cd services/<nazwa>
docker compose down
```

## Dostępy do usług

| Usługa | Subdomena | Port bezpośredni |
| --- | --- | --- |
| Nginx Proxy Manager | - | :81 (panel admina) |
| Portainer | portainer.home.local | :9000 |
| AdGuard Home | - | :3001 (panel), :3000 (wizard) |
| Vaultwarden | vaultwarden.home.local | - |
| Mealie | mealie.home.local | - |
| Grocy | grocy.home.local | - |
| Gotify | gotify.home.local | - |
| Watchtower | - | - (brak UI) |

## Backup

Dane wszystkich usług:

```bash
# Kopiuj dane
rsync -av --progress data/ /cel/backup/data/
rsync -av --progress services/nginx-proxy/data/ /cel/backup/services/nginx-proxy/data/
```
