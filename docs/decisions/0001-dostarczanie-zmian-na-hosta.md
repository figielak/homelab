# 0001 — Dostarczanie zmian na hosta

## Kontekst
Jeden host `pi4-core`, jeden administrator. Konfiguracja ma żyć w Git,
infrastruktura ma być odtwarzalna z samego repo i kopii danych.

## Wybór
GitHub (repo prywatne) jako origin. Pi klonuje przez read-only deploy key
do /opt/homelab i aktualizuje się przez `git pull --ff-only`.
Pi nigdy nie pushuje.

## Konsekwencje
- Zdalny remote pełni też rolę backupu konfiguracji.
- Deploy jest dwuetapowy (push, potem pull) — świadomy koszt.
- Sekrety nie są dostarczane przez Git. Na razie `.env` tworzony ręcznie
  na hostcie wg `.env.example`, kopia w menedżerze haseł.
  Dług techniczny: docelowo SOPS + age.
- `--ff-only` wymusza wykrycie ręcznych zmian na hostcie.