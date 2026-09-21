sudo bash <<'EOF' | tee /tmp/castle-stan.txt
echo "=== ZEBRANE: $(date -Is) ==="

echo; echo "=== MODEL I SYSTEM ==="
tr -d '\0' < /proc/device-tree/model; echo
grep PRETTY_NAME /etc/os-release
uname -m; uname -r
uptime -p

echo; echo "=== UŻYTKOWNIK ==="
id figielak
getent passwd figielak
getent group docker || echo "grupa docker: BRAK"

echo; echo "=== DYSKI I BOOT ==="
lsblk -o NAME,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINT
echo "root na: $(findmnt -n -o SOURCE /)"
df -h / /mnt/hdd 2>&1
echo "--- fstab ---"
grep -vE '^\s*(#|$)' /etc/fstab
echo "--- USB ---"
lsusb

echo; echo "=== PAMIĘĆ (BASELINE) ==="
free -h

echo; echo "=== SIEĆ ==="
ip -br a
ip route | awk '/^default/ {print "brama:", $3, "dev", $5}'
echo "--- DNS ---"
resolvectl status 2>/dev/null | grep -E 'Current DNS|DNS Servers|DNSStubListener' || cat /etc/resolv.conf

echo; echo "=== PORTY (podstawa rejestru) ==="
ss -tulpnH | awk '{print $1, $5, $7}' | sort -u

echo; echo "=== DOCKER ==="
docker --version 2>&1 || echo "docker: NIEZAINSTALOWANY"
docker compose version 2>&1 || true
docker ps -a --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' 2>&1 || true
docker network ls 2>&1 || true

echo; echo "=== ŚCIEŻKI HOMELABA ==="
for p in /opt/homelab /srv/homelab/data /mnt/hdd /mnt/hdd/backups; do
  [ -e "$p" ] && ls -ld "$p" || echo "$p: BRAK"
done
[ -d /opt/homelab/.git ] && git -C /opt/homelab log --oneline -1

echo; echo "=== SSH ==="
sshd -T | grep -E '^(port|permitrootlogin|pubkeyauthentication|passwordauthentication|permitemptypasswords) '

echo; echo "=== SUDO ==="
grep -rn 'ALL=' /etc/sudoers /etc/sudoers.d/ 2>/dev/null | grep -v '#'

echo; echo "=== CZAS ==="
timedatectl

echo; echo "=== ZASILANIE ==="
vcgencmd get_throttled
vcgencmd measure_temp

echo; echo "=== BOOTLOADER / EEPROM ==="
rpi-eeprom-config
rpi-eeprom-update
EOF