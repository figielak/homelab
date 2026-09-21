---
paths:
  - "docs/**/*.md"
---

# Dokumentacja

Vault Obsidiana. Notatki linkowane wikilinkami `[[nazwa]]`, tagowane
(`#usługa`, `#backup`, `#do-zrobienia`).

**Nigdy nie wpisuj tu wartości sekretów.** `docs/` jest w Git i trafia na GitHuba.
Zapisujesz najwyżej, gdzie sekretu szukać (nazwa wpisu w menedżerze haseł).

## Notatka hosta — `docs/hosts/<nazwa>.md`

Najważniejszy plik w całym repo. Zawiera **rejestr portów** — przy jednym hoście
to jedyna ochrona przed kolizjami. Aktualizuj przy każdej nowej usłudze.

Poza tym: stan wyjściowy, konto administracyjne z UID/GID, dyski, baseline RAM,
log zmian.

Log zmian to jedna linia na wpis:

```markdown
- 2026-09-11 — sklonowane repo do /opt/homelab (deploy key read-only)
```

## Notatka usługi — `docs/services/<nazwa>.md`

Tworzona przy każdej nowej usłudze. Zawsze zawiera:

- Do czego służy i **dlaczego wybrana akurat ta**
- URL, zajmowane porty, ścieżka do danych, szacowane zużycie RAM
- Zależności: od czego zależy, co zależy od niej
- Co trzeba zbackupować, żeby ją odtworzyć
- **Procedura odtworzenia od zera, krok po kroku** — najważniejsza sekcja,
  bo realizuje cel odtwarzalności
- Znane problemy i obejścia
- Log zmian z datami

## Decyzje — `docs/decisions/NNNN-tytul.md`

Powściągliwie. Nowy ADR tylko wtedy, gdy decyzja spełnia **wszystkie trzy**
warunki z CLAUDE.md. Jeśli nie masz pewności — nie proponuj.

Format: kontekst → rozważane opcje → wybór → konsekwencje. 10–20 linijek.

## Runbooki — `docs/runbooks/`

Procedury, które zostaną wykonane ponownie: bootstrap hosta, backup, restore,
aktualizacje, awarie, zmiana sieci przy przeprowadzce.

Runbook ma być wykonywalny bez myślenia — komendy gotowe do wklejenia
plus oczekiwany wynik każdego kroku.
