# figielak — konto administracyjne

Konto administracyjne na hoście [[castle]]. **To nie jest notatka hosta** —
leży w `docs/hosts/` wyłącznie dlatego, że opisuje stan systemu. Do rozważenia
przeniesienie albo scalenie z notatką hosta.

#konto

## Podstawowe dane

| | |
|---|---|
| Użytkownik | `figielak`, UID 1000, GID 1000 |
| Grupy | `sudo`, `docker` (dodana przy instalacji Dockera 2026-09-21) |
| Powłoka | `/bin/bash` |
| Hasło | menedżer haseł, wpis „Homelab Castle" |
| Logowanie SSH | wyłącznie kluczem, hasła wyłączone, root zablokowany |

## Hasło i `sudo` — stan faktyczny

Hasło służy do **logowania lokalnego** (klawiatura + monitor podłączone
bezpośrednio do Pi). **Nie jest wymagane przy `sudo`**, bo
`/etc/sudoers.d/90-cloud-init-users` zawiera `figielak ALL=(ALL) NOPASSWD:ALL`.

Konsekwencja: klucz SSH jest **jedynym** poświadczeniem oddzielającym
kogokolwiek od roota na tym hoście. Odłożone świadomie 2026-09-21 —
szczegóły i alternatywa w długu technicznym [[castle]].

## Klucz SSH

- Klucz publiczny: `~/.ssh/authorized_keys` na hoście
- Klucz prywatny: laptop, `~/.ssh/`
- Logowanie roota po SSH wyłączone drop-inem
  `hosts/castle/etc/ssh/sshd_config.d/10-homelab-hardening.conf`

**Passphrase na kluczu nie została zweryfikowana.** Jeśli klucz jej nie ma,
skradziony plik daje natychmiastowego roota (patrz wyżej). Sprawdzenie:

```bash
ssh-keygen -y -f ~/.ssh/<klucz> </dev/null
```

Brak pytania o hasło = brak passphrase. #do-zrobienia

## UID 1000 przy odtwarzaniu

**Konto administracyjne musi powstać jako pierwsze na nowym sprzęcie**, żeby
dostało UID 1000.

Powód: część usług zapisuje dane jako UID 1000 (`PUID`/`PGID` w [[mealie]]),
a backup odtwarza właściciela **numerycznie**. Konto z innym UID-em oznacza
dane, do których kontener nie ma dostępu.

Nie dotyczy to wszystkich usług — [[adguard]] działa w kontenerze jako root
i jego dane należą do `0:0`. Przy odtwarzaniu sprawdź w notatce usługi,
czyją własnością mają być pliki.

## Ryzyko przyjęte świadomie

Grupa `docker` daje uprawnienia równoważne rootowi — dostęp do socketu
Dockera pozwala zamontować `/` do kontenera. Akceptowane przy jednym
administratorze; przy dodaniu drugiej osoby wymaga ponownej oceny.
