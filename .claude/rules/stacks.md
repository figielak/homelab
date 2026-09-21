---
paths:
  - "stacks/**/docker-compose.yml"
  - "stacks/**/.env.example"
---

# Stacki Dockera

Checklista przed zaproponowaniem zmiany w `docker-compose.yml`.

## Zawsze wymagane

Każda usługa ma mieć:

- `image:` z **konkretnym tagiem wersji**. Nigdy `:latest`, nigdy sam tag `stable`.
- `restart: unless-stopped`
- `mem_limit` — wynikający z realnego zapotrzebowania, nie wzięty z sufitu.
  Suma limitów wszystkich stacków musi mieścić się w 4 GB minus baseline systemu.
- `healthcheck`
- `container_name` w `kebab-case`, identyczny z nazwą katalogu stacku

## Wolumeny

Tylko bind mounts. Nigdy `volumes:` na poziomie top-level z named volume.

Poprawnie:
```yaml
volumes:
  - ${DATA_ROOT}/<stack>:/sciezka/w/kontenerze
```

`DATA_ROOT` pochodzi z `.env` obok compose'a i wskazuje na `/srv/homelab/data`.
Nie wpisuj ścieżek na sztywno — przy migracji na x86 zmienia się jedna zmienna,
nie każdy plik.

## Sieć i porty

Kontenery aplikacyjne **nie publikują portów na hoście**. Brak sekcji `ports:`.
Dostęp wyłącznie przez Caddy w sieci `proxy`:

```yaml
networks:
  - proxy
```

Wyjątki (AdGuard w `network_mode: host`) muszą być uzasadnione i odnotowane
w rejestrze portów w `docs/hosts/`.

## Sekrety

Wartości sekretów nigdy w `docker-compose.yml`. Zawsze `${ZMIENNA}` z `.env`.
Do repo trafia wyłącznie `.env.example` z pustymi albo przykładowymi wartościami.

Uwaga na semantykę: `.env` obok compose'a służy do **interpolacji** `${VAR}`
w samym pliku compose. Dyrektywa `env_file:` wstrzykuje zmienne do kontenera
i nie działa na interpolację. To dwie różne rzeczy.

## ARM64

Zanim zaproponujesz obraz, potwierdź, że ma build na `linux/arm64`.
Jeśli nie masz pewności, powiedz to wprost i zaproponuj weryfikację:

```bash
docker manifest inspect <obraz>:<tag> | grep -A2 architecture
```

## Po zmianie

Zaproponuj weryfikację przez `docker compose config` (sprawdza składnię
i podstawienie zmiennych bez uruchamiania czegokolwiek), a dopiero potem
`docker compose up -d`.
