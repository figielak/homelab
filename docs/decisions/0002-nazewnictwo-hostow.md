# 0003 — Nazewnictwo hostów

## Kontekst
Pierwotnie host nazywał się `pi4-core`. Cel projektu zakłada migrację
na sprzęt x86 w perspektywie 2–4 lat, bez przywiązania do Raspberry Pi.
Hostname trafia do metadanych snapshotów restic, do MagicDNS Tailscale,
do ścieżek w repo i do dokumentacji — zmiana po wdrożeniu jest kosztowna.

## Rozważane opcje
- `pi4-core` — koduje model sprzętu, dezaktualizuje się przy migracji.
- `core` — rola bez sprzętu; problem wraca przy dwóch hostach naraz.
- Nazwa własna ze zbioru <nazwa zbioru> — wybrane.

## Wybór
Hostname: castle. Kolejne hosty dostają nazwy z tego samego tematycznego zbioru. Np. tower, bazar, garden itp.
Zasady: małe litery, bez podkreślników i diakrytyków, bez kolizji
z nazwami usług wystawianych w `*.home.arpa`.

## Konsekwencje
- Nazwa hosta nie niesie informacji o sprzęcie.
- Podczas migracji obie maszyny mogą działać równolegle bez konfliktu.
- Wymagany rejestr nazw w `docs/hosts/`, żeby nie zgubić, co jest czym.