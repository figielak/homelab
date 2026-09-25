# Tailscale

VPN do zdalnego dostępu do homelaba. Z telefonu lub laptopa poza domem
`*.home.figielak.dev` działa tak samo jak w sieci domowej. Nie trzeba otwierać
portów na routerze ani publikować czegokolwiek w internecie.

#usługa #sieć

## Dlaczego akurat to

- **Goły WireGuard** wymagałby przekierowania portu na routerze i ręcznego
  zarządzania kluczami każdego urządzenia. Tailscale przechodzi przez NAT
  bez otwierania portów, a urządzenia dodaje się przez logowanie.
- **Raspberry Pi Connect** jest świadomie odrzucony w `CLAUDE.md`. Daje dostęp
  do samego Pi, a nie do usług za Caddy, i wiąże z Raspberry Pi,
  co utrudnia migrację na x86.
- Koszt: zależność od zewnętrznego koordynatora (serwery Tailscale) i konta.
  Ruch idzie bezpośrednio między urządzeniami albo przez relay DERP. Treść
  jest szyfrowana end-to-end.

## Jak to działa: subnet route `192.168.10.10/32`

`castle` ogłasza w tailnecie trasę **tylko do własnego adresu LAN**.

1. Telefon poza domem pyta swój zwykły resolver o `mealie.home.figielak.dev`.
2. Publiczny wildcard w Cloudflare (`*.home → 192.168.10.10`, DNS only)
   zwraca adres z sieci domowej.
3. Tailscale ma trasę do `192.168.10.10/32` przez `castle` i kieruje tam ruch tunelem.
4. Ruch trafia na 443 do [caddy](caddy.md), a certyfikat wildcard pasuje, bo nazwa
   się nie zmienia.

Dzięki temu **ani DNS, ani Caddy nie wymagały żadnej zmiany**. `/32` zamiast
`/24`: z zewnątrz widać wyłącznie `castle`, a nie router czy inne urządzenia w domu.

## Podstawowe dane

| | |
|---|---|
| Host | [castle](../hosts/castle.md) |
| Uruchomienie | **na hoście, nie w Dockerze**: usługa systemd `tailscaled` (wyjątek dopuszczony w `CLAUDE.md`) |
| Pakiet | `tailscale` z `pkgs.tailscale.com/stable/debian` (trixie), wersja `1.102.4` |
| Adres w tailnecie | `100.93.181.44` |
| Ogłaszana trasa | `192.168.10.10/32` |
| Porty | 41641/udp (IPv4 i IPv6), interfejs `tailscale0` |
| Stan | `/var/lib/tailscale/tailscaled.state` |
| RAM | ~60 MiB RSS (2026-09-24), bez `mem_limit`, liczone do baseline'u hosta |
| Pliki w repo | `hosts/castle/etc/sysctl.d/99-tailscale.conf` |

**Wersja nie jest zamrożona** (`apt-mark hold` nie jest użyte). Łatki
bezpieczeństwa komponentu, który wpuszcza ruch z zewnątrz, są ważniejsze
niż powtarzalność wersji. Aktualizacje idą razem z `apt upgrade`.

## Zależności

- **Zależy od:** internetu i serwerów koordynacyjnych Tailscale; konta
  Tailscale; **publicznego wildcardu w Cloudflare** (rozwiązywanie nazw poza domem);
  `ip_forward` na hoście.
- **Zależy od niej:** zdalny dostęp do wszystkich usług. W domu nic od niej
  nie zależy. Awaria Tailscale nie dotyka sieci lokalnej.

## Konfiguracja w panelu admina

Ta część **nie jest w repo**. Po odtworzeniu trzeba ją powtórzyć ręcznie:

- trasa `192.168.10.10/32` **zatwierdzona** dla `castle`
- **key expiry wyłączone** dla `castle`. Bez tego host po ~180 dniach wypada
  z tailnetu, a zauważysz to dopiero wtedy, gdy będziesz poza domem.
- Tailscale SSH **nieużywane**: dostęp administracyjny dalej idzie przez `sshd` z kluczem
- ACL domyślne (każde urządzenie w tailnecie widzi każde)

## Co backupować

Nic nie jest konieczne. `/var/lib/tailscale/` zawiera tożsamość maszyny.
Bez niej odtworzony host loguje się jako **nowa maszyna**: dostaje nowy adres 100.x,
a trasę i key expiry trzeba ustawić od nowa w panelu. To kilka minut pracy,
więc katalogu świadomie nie backupujemy. Zawiera klucz prywatny maszyny.

## Procedura odtworzenia od zera

```bash
# 1. repo apt Tailscale (komendy z pkgs.tailscale.com/stable/ dla trixie)
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg >/dev/null
curl -fsSL https://pkgs.tailscale.com/stable/debian/trixie.tailscale-keyring.list | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt-get update && sudo apt-get install tailscale

# 2. forwarding na stale
cd /opt/homelab && git pull --ff-only
sudo install -o root -g root -m 644 hosts/castle/etc/sysctl.d/99-tailscale.conf /etc/sysctl.d/
sudo sysctl --system | grep forwarding

# 3. dolaczenie do tailnetu — wypisze URL do zalogowania w przegladarce
sudo tailscale up --advertise-routes=192.168.10.10/32
```

Potem w panelu admina: usuń starą maszynę `castle` (jeśli została), zatwierdź
trasę, wyłącz key expiry.

Na nowym sprzęcie (x86) zmieniasz tylko nazwę dystrybucji w URL-ach z kroku 1
i adres w `--advertise-routes`, jeśli host dostanie inny IP.

### Weryfikacja

```bash
tailscale status                    # castle + urzadzenia klienckie
sysctl net.ipv4.ip_forward          # = 1
sudo ss -ulpn | grep tailscaled     # 41641/udp
systemctl is-enabled tailscaled     # enabled
```

Telefon na LTE, z wyłączonym Wi-Fi: przy włączonym Tailscale
`https://mealie.home.figielak.dev` otwiera się z poprawnym certyfikatem.
**Przy wyłączonym Tailscale nie otwiera się.** To potwierdza, że usług nie
widać z internetu.

### Klienci

- Telefon: aplikacja Tailscale, logowanie tym samym kontem. Trasy przyjmuje domyślnie.
- Laptop z Linuksem: trasy trzeba włączyć jawnie:
  `sudo tailscale set --accept-routes`

## Jak wyłączyć

```bash
sudo tailscale down
sudo apt purge tailscale
sudo rm /etc/apt/sources.list.d/tailscale.list /usr/share/keyrings/tailscale-archive-keyring.gpg
sudo rm /etc/sysctl.d/99-tailscale.conf && sudo sysctl --system
```

Potem usuń maszynę w panelu admina. `ip_forward` zostanie na 1, dopóki działa
Docker. To normalne.

## Znane problemy i ograniczenia

- **Z tailnetu osiągalne są wszystkie porty `castle`**, w tym 22 (SSH) i 3000
  (panel AdGuarda z pominięciem Caddy). Przy domyślnych ACL to tylko własne
  urządzenia, więc akceptowalne. Gdyby do tailnetu dołączył ktoś jeszcze,
  trzeba zawęzić ACL.
- **DNS rebinding protection.** Niektóre resolvery (routery, sieci firmowe,
  hotelowe) odrzucają publiczne odpowiedzi z prywatnym IP. Objaw: Tailscale
  połączony, a nazwa się nie rozwiązuje. Obejście: split DNS w panelu Tailscale,
  `home.figielak.dev → 192.168.10.10` (AdGuard jest osiągalny przez trasę).
  Na razie nieskonfigurowane, bo nie było potrzeby.
- **Laptop z `--accept-routes` w domu** idzie do `castle` tunelem zamiast
  bezpośrednio. Działa, ale z niepotrzebnym narzutem.
- **Cały ruch zdalny idzie przez Wi-Fi `castle`.** To istniejący dług,
  zobacz [castle](../hosts/castle.md).

## Log zmian

- 2026-09-24 — zainstalowany `1.102.4` z repo apt dla trixie; subnet route
  `192.168.10.10/32` zatwierdzona, key expiry wyłączone; dostęp z telefonu
  na LTE zweryfikowany, także po restarcie hosta. Wdrożone przed krokiem 7
  (monitoring), świadomie, bo krok 6 blokuje brak HDD.
