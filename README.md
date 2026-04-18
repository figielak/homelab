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
