## Informacje


## Instalacja

1. Zainstaluj Docker i Docker Compose
2. Sklonuj repozytorium do `/opt/homelab`
3. Skopiuj pliki '.env'
4. Uruchom proxy: `docker compose up -d`
5. Uruchom wybrane usługi z katalogu `services`

## Uruchamianie

**Uruchomienie proxy**
```bash
docker compose up -d
```

**Uruchomienie pojedyńczej usługi**
```bash
cd services/<nazwa_uslugi>
docker compose --env-file ../../.env up -d
```

## Dostępy do usług
| Usługa | Subdomena | Hostname | Port |
| --- | --- | --- | --- |
| Nginx Proxy Manager | <adres_ip> | - | 81 |
| Portainer | portainer.home.local | portainer | 9000 |
| Vaultwarden | vaultwarden.home.local | vaultwarden | 80 |
