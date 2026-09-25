# Dashboard agent

Wysyła statystyki [[castle]] na dashboard figielak.dev. Co 60 s robi POST
z JSON-em: zasoby hosta, DNS, ruch sieciowy i stan usług, a do części
prywatnej monitory, kontenery i ostatni backup. Strona zapisuje dane
w Firestore i pokazuje je w kaflach.

#usługa #monitoring

## Dlaczego tak

- **Push, nie pull.** Homelab nie jest wystawiony do internetu i tak zostaje.
  Agent tylko wysyła dane, niczego nie nasłuchuje.
- **Kontener, nie timer systemd.** `koncept.md` strony zakładał skrypt
  z cronem, ale zasada homelaba mówi: poza systemem bazowym wszystko w Dockerze.
- **Źródła zamiast Beszela.** CPU, RAM, dysk, temperatura i ruch pochodzą
  wprost z `/proc`, `/sys` i `statvfs`. Nie trzeba konta w Beszelu ani znać
  jego API. Stan usług bierze z `/metrics` [[uptime-kuma]], jedynego API
  Kumy 2.5.5 z dostępnością za 30 dni (sprawdzone w kodzie).

**Sekcje publiczne** (`lab`, `dns`, `traffic`, `services`, decyzja z 2026-09-24)
niosą tylko liczby i ogólne rodzaje usług (`dns`, `media`, `files`, `backup`),
bez nazw hostów, domen, IP i nazw monitorów.

**Sekcje prywatne** (`monitors`, `containers`, `backup`, od 2026-09-25) strona
zapisuje w osobnym dokumencie (`homelab/private`) i pokazuje tylko za hasłem.
Mogą więc zawierać **nazwy** usług i kontenerów. Nadal nie wychodzą z Pi:
nazwy hostów, domeny, IP, URL-e, obrazy ani treść `Status` Dockera poza stanem
zdrowia. Serwer przyjmuje tylko „zwykłe” nazwy: litery, cyfry, spacja, `-`, `_`,
maksymalnie 40 znaków. Agent sprawdza je przed wysyłką (`plain_name`), a nazwę
spoza wzorca pomija i loguje, zamiast ją poprawiać.

## Podstawowe dane

| | |
|---|---|
| Host | [[castle]] |
| Stack | `stacks/dashboard-agent/` |
| Obraz | `python:3.14.7-alpine3.24` (arm64 potwierdzony w Docker Hub), skrypt z repo montowany `:ro`, bez builda |
| Porty | żadne; `network_mode: host`, ale nic nie nasłuchuje |
| Dane | `/srv/homelab/data/dashboard-agent/` (właściciel `65534`): `state.json`, `last_ok` |
| RAM | `mem_limit` 64 MiB, zmierzone ~13 MiB (2026-09-24) |
| Interwał | 60 s (~1440 zapisów Firestore na dobę) |

Adresy (strona, Kuma, AdGuard, socket proxy) i sekrety są **wyłącznie
w `.env`**, nie w repo ani w tej notatce. Lista zmiennych: `.env.example`.

## Skąd dane

| Sekcja | Źródło | Uwagi |
|---|---|---|
| `lab` | `/proc/stat` (2 próbki co 5 s), `/proc/meminfo`, `thermal_zone0`, `/proc/uptime`, `statvfs` na katalogu danych (SSD) | `containers` z socket proxy [[beszel]] (tylko GET) |
| `dns` | AdGuard `/control/stats` | wymaga **retencji statystyk 7 dni**, wtedy API zwraca 168 kubełków godzinowych i „dziś” liczy się od północy w Polsce |
| `traffic` | `/proc/net/dev` (`wlan0` + `eth0`) | **ruch samego Pi, nie całego domu**; „łącznie” od pierwszego startu agenta (`totalSince`) |
| `services` | Kuma `/metrics` (API key) | `monitor_status`, `monitor_uptime_ratio` i `monitor_response_time_seconds` z `window="30d"` |
| `monitors` 🔒 | ten sam odczyt Kumy co `services` | jeden wpis na usługę z paska na stronie |
| `containers` 🔒 | socket proxy [[beszel]], `GET /containers/json?all=1` | `state` = `State` Dockera; `health` z `Status`: `(healthy)`, `(unhealthy)`, `(health: starting)` |
| `backup` 🔒 | plik `last-backup.json` w katalogu danych agenta | wysyłany dopiero, gdy plik istnieje (krok 6) |

🔒 = sekcja prywatna.

Mapowanie monitorów Kumy jest w `config.json`: `services` przypisuje monitory
do rodzaju, a `monitors` do nazwy usługi. **Nazwa w `monitors` musi być
identyczna** (wielkość liter też) z `name` w `src/lib/services.ts` strony,
bo po niej pasek usług łączy kropkę z usługą. Zmiana nazwy po jednej
stronie wymaga zmiany po drugiej.

Usługa albo rodzaj bez żadnego monitora w Kumie nie jest wysyłany. Strona
pokazuje wtedy „—” albo szarą kropkę. Agregacja w obu sekcjach:
`up` = żaden monitor nie jest down (pending w trakcie ponowień i maintenance
liczą się jako działające, tak jak w alertach Kumy), `uptime30d` = najgorszy,
`avgMs` = średnia. „AdGuard” łączy panel, DNS i rewrite, więc jego `avgMs`
miesza czasy HTTP i DNS i jest tylko orientacyjne.

### Plik statusu backupu

Zadanie backupu (krok 6) po każdym przebiegu zapisuje
`/srv/homelab/data/dashboard-agent/last-backup.json`. Agent tylko go czyta:
nie ma dostępu do repozytorium restica ani jego hasła.

```json
{ "tool": "restic", "lastRunAt": "2026-09-25T02:00:12Z", "ok": true, "sizeGb": 12.4, "snapshots": 31 }
```

- `tool`: `restic`, `borg` albo `kopia`.
- `lastRunAt`: ISO **ze strefą czasową**, nie z przyszłości.
- `ok`: czy przebieg się udał. Nieudany przebieg też zapisuje plik, z `ok: false`.
- `sizeGb` (GiB, ≥ 0) i `snapshots` (liczba całkowita ≥ 0) są opcjonalne.
- Zapis atomowy (`tmp` + `mv` w tym samym katalogu) z prawami `0644`, żeby
  agent (`65534`) nie przeczytał połowy pliku.

Strona uznaje backup starszy niż 26 h za zaległy. Dopóki pliku nie ma,
pokazuje „Brak kopii” na czerwono, i to jest zamierzone.

**Dlaczego AdGuard ma dokładnie 7 dni:** przy dłuższej retencji API przechodzi
na dni liczone od północy UTC. Agent wtedy celowo pomija sekcję `dns`
i loguje `ustaw retencje statystyk na 7 dni`.

## Kontrakt

`POST` z nagłówkami `Authorization: Bearer <token>` i
`Content-Type: application/json`. Źródło prawdy o walidacji to
`src/lib/server/homelab.ts` w repo strony.

```json
{
  "v": 1,
  "lab": { "cpu": 6.4, "cpuTempC": 57.9, "ramUsedGb": 0.84, "ramTotalGb": 3.71,
           "disks": [{ "kind": "system", "usedGb": 9.6, "totalGb": 116.9 }],
           "uptimeDays": 0.07, "containers": 8 },
  "dns": { "queriesToday": 3077, "blockedToday": 202, "queriesWeek": 4257, "blockedWeek": 382 },
  "services": [{ "kind": "dns", "up": true, "uptime30d": 100.0, "avgMs": 4 }],
  "traffic": { "downGbToday": 0.0, "upGbToday": 0.0, "downGbTotal": 0.0, "upGbTotal": 0.0,
               "totalSince": "2026-09-24" },
  "monitors":   [{ "name": "Mealie", "up": true, "uptime30d": 99.9, "avgMs": 42 }],
  "containers": [{ "name": "mealie", "state": "running", "health": "healthy" }],
  "backup":     { "tool": "restic", "lastRunAt": "2026-09-25T02:00:12+00:00", "ok": true,
                  "sizeGb": 12.4, "snapshots": 31 },
  "sentAt": "2026-09-24T13:42:47+00:00"
}
```

- Sekcja, której źródło nie odpowiedziało, jest pomijana. Strona zachowuje
  wtedy jej poprzednią wartość i czas.
- Serwer odrzuca pojedynczą sekcję, a nie cały push. Odpowiedź 200 zawiera
  listę `rejected` z powodami, które agent loguje. Przy 4xx/5xx agent loguje
  kod i treść odpowiedzi.
- Limity: `monitors` do 30, `containers` do 60, nazwy unikalne w sekcji,
  całe body do 16 KiB.
- „Gb” to GiB (1024³), tak jak w `df -h`.
- Pola opcjonalne: `containers`, `queriesWeek`/`blockedWeek`, `uptime30d`/`avgMs`,
  `health`, `sizeGb`/`snapshots`. `updateAvailable` agent na razie pomija.

## Zależności

- **Zależy od:**
  - strony (endpoint, Firestore),
  - [[adguard]] (API na `127.0.0.1:3000`),
  - [[uptime-kuma]] (przez [[caddy]]),
  - socket proxy z [[beszel]] (`127.0.0.1:2375`).

  Awaria jednego źródła usuwa tylko jego sekcję.
- **Zależy od niego:** tylko kafle na stronie.

## Sekrety

| Zmienna | Gdzie jest |
|---|---|
| `PUSH_TOKEN` | menedżer haseł „figielak.dev push token” + Secret Manager `stats-push-token` |
| `KUMA_API_KEY` | menedżer haseł „Homelab Kuma API key” |
| `KUMA_PUSH_URL` | Kuma, monitor „Dashboard agent” (URL zawiera token) |
| `ADGUARD_USER` / `ADGUARD_PASSWORD` | menedżer haseł „Homelab AdGuard” (konto administratora) |

## Co backupować

Nic krytycznego. `state.json` trzyma tylko liczniki ruchu: jego utrata zeruje
„łącznie” i ustawia nowe `totalSince`.

## Procedura odtworzenia od zera

```bash
cd /opt/homelab && git pull --ff-only
sudo mkdir -p /srv/homelab/data/dashboard-agent
sudo chown 65534:65534 /srv/homelab/data/dashboard-agent

cd /opt/homelab/stacks/dashboard-agent
cp .env.example .env && nano .env    # wartości z menedżera haseł
docker compose run --rm dashboard-agent python /app/agent.py --dry-run   # JSON, bez wysyłki
docker compose up -d
```

Przed startem:

- AdGuard: Ustawienia → Ustawienia ogólne → Statystyki → **7 dni**.
- Kuma: API key (Settings → API Keys) oraz monitor Push „Dashboard agent”
  (interwał 60 s, 2 ponowienia).

### Weryfikacja

```bash
docker compose ps                                        # healthy po ~2 min
docker compose logs --since 5m                           # pusto = brak błędów
sudo cat /srv/homelab/data/dashboard-agent/last_ok       # czas ostatniej udanej wysyłki
```

- Monitor „Dashboard agent” w Kumie jest zielony.
- Kafle na stronie pokazują dane „na żywo”.
- Na prywatnym dashboardzie pasek usług ma kolorowe kropki z czasami, a kafel
  „Serwer” pokazuje listę kontenerów.

Test ręczny endpointu `curl`-em musi mieć `-H 'Content-Type: application/json'`.
Bez tego nagłówka ochrona CSRF w Astro zwraca 403, zanim zapytanie dotrze
do endpointu.

## Znane problemy i ograniczenia

- **`.env` zawiera hasło administratora AdGuarda.** AdGuard nie ma ról,
  a osobnego użytkownika dla agenta świadomie nie tworzymy. Wyciek `.env`
  oznacza zmianę hasła AdGuarda i aktualizację `.env`.
- **Ruch to tylko ruch `castle`**, nie całego domu. Ruch domowy wymagałby
  danych z routera.
- **Publiczne dane mówią coś o homelabie**: kiedy był restart (uptime), że
  usługa leży i jak bardzo host jest obciążony. Przyjęte, bo nie wynika z nich
  adres ani sposób dostępu (tylko Tailscale).
- **Agent loguje wyłącznie błędy.** Puste logi oznaczają, że wszystko działa.
  Postęp widać po `last_ok`. Wyjątek: stale wpisy „brak monitorow” znaczą, że
  usługa z `config.json` nie ma jeszcze monitora w Kumie.
- **Gdy padnie Kuma, sekcje `services` i `monitors` przestają przychodzić.**
  Strona pokazuje wtedy ich wiek. Monitor „Uptime Kuma” nie zgłosi śmierci
  samej Kumy.

## Log zmian

- 2026-09-24 — stack utworzony i uruchomiony; pierwsza udana wysyłka o 14:23 UTC;
  retencja statystyk AdGuarda zmieniona na 7 dni; w Kumie API key i monitor Push
- 2026-09-25 — sekcje prywatne `monitors`, `containers`, `backup` (ta ostatnia
  czeka na `last-backup.json` z kroku 6); logowanie `rejected` z odpowiedzi strony
