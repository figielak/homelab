#!/usr/bin/env bash
#
# Zbiera stan faktyczny hosta do wklejenia w docs/hosts/<host>.md.
# Tylko odczyt — nie zmienia niczego w systemie.
#
# Użycie:
#   sudo ./scripts/collect-host-state.sh [plik_wyjsciowy]
#
# Sekcje specyficzne dla Raspberry Pi są pomijane na innym sprzęcie,
# żeby skrypt przeżył migrację na x86.

set -uo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Uruchom przez sudo — bez roota nie odczytasz sshd -T, sudoers ani wlascicieli procesow w ss." >&2
  exit 1
fi

OUT="${1:-/tmp/$(hostname)-stan.txt}"

# Konto administracyjne: to, które wywołało sudo. Można nadpisać: ADMIN_USER=nazwa sudo ...
ADMIN="${ADMIN_USER:-${SUDO_USER:-root}}"

section() { printf '\n=== %s ===\n' "$1"; }

collect() {
  printf '=== ZEBRANE: %s (host: %s, admin: %s) ===\n' "$(date -Is)" "$(hostname)" "$ADMIN"

  section "MODEL I SYSTEM"
  if [ -r /proc/device-tree/model ]; then
    tr -d '\0' < /proc/device-tree/model; echo
  else
    command -v dmidecode >/dev/null && dmidecode -s system-product-name 2>/dev/null || echo "model: nieznany"
  fi
  grep PRETTY_NAME /etc/os-release
  uname -m
  uname -r
  uptime -p

  section "UŻYTKOWNIK"
  id "$ADMIN"
  getent passwd "$ADMIN"
  passwd -S "$ADMIN"
  getent group docker || echo "grupa docker: BRAK"

  section "DYSKI I BOOT"
  lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT
  echo "root na: $(findmnt -n -o SOURCE /)"
  df -h / /srv /mnt/hdd 2>&1
  echo "--- fstab ---"
  grep -vE '^\s*(#|$)' /etc/fstab
  echo "--- USB ---"
  command -v lsusb >/dev/null && lsusb || echo "lsusb: brak"

  section "PAMIĘĆ (BASELINE)"
  free -h

  section "SIEĆ"
  ip -br a
  ip route | awk '/^default/ {print "brama:", $3, "dev", $5}'
  echo "--- DNS ---"
  resolvectl status 2>/dev/null | grep -E 'Current DNS|DNS Servers|DNSStubListener' || cat /etc/resolv.conf

  section "PORTY (podstawa rejestru)"
  ss -tulpnH | awk '{print $1, $5, $7}' | sort -u

  section "DOCKER"
  if command -v docker >/dev/null; then
    docker --version
    docker compose version
    docker info --format 'storage driver: {{.Driver}} / katalog danych: {{.DockerRootDir}}' 2>&1
    echo "--- kontenery ---"
    docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
    echo "--- sieci ---"
    docker network ls
  else
    echo "docker: NIEZAINSTALOWANY"
  fi

  section "ŚCIEŻKI HOMELABA"
  for p in /opt/homelab /srv/homelab/data /mnt/hdd /mnt/hdd/backups; do
    [ -e "$p" ] && ls -ld "$p" || echo "$p: BRAK"
  done
  [ -d /opt/homelab/.git ] && git -C /opt/homelab log --oneline -1

  section "SSH"
  sshd -T | grep -E '^(port|permitrootlogin|pubkeyauthentication|passwordauthentication|permitemptypasswords) '
  echo "--- drop-iny ---"
  ls -la /etc/ssh/sshd_config.d/ 2>/dev/null

  section "SUDO"
  grep -rn 'ALL=' /etc/sudoers /etc/sudoers.d/ 2>/dev/null | grep -v '#'

  section "CZAS"
  timedatectl

  if command -v vcgencmd >/dev/null; then
    section "ZASILANIE (Raspberry Pi)"
    vcgencmd get_throttled
    vcgencmd measure_temp
  fi

  if command -v rpi-eeprom-config >/dev/null; then
    section "BOOTLOADER / EEPROM (Raspberry Pi)"
    rpi-eeprom-config
    rpi-eeprom-update
  fi
}

collect | tee "$OUT"
printf '\nZapisano: %s\n' "$OUT"
