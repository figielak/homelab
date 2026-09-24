"""Agent push: zbiera statystyki castle i wysyla je na dashboard figielak.dev.

Kontrakt JSON: docs/services/dashboard-agent.md. Tylko stdlib.
Adresy i sekrety wylacznie ze zmiennych srodowiskowych (.env), nigdy z repo.

    python agent.py            # petla co interval_seconds
    python agent.py --dry-run  # jeden odczyt na stdout, bez wysylki i zapisu stanu
"""
import base64
import datetime
import json
import os
import re
import sys
import time
import urllib.request

CONFIG_PATH = "/app/config.json"
DATA_DIR = "/data"
STATE_PATH = os.path.join(DATA_DIR, "state.json")
LAST_OK_PATH = os.path.join(DATA_DIR, "last_ok")

GIB = 1024**3
TIMEOUT = 10


def log(msg):
    print(f"{datetime.datetime.now().isoformat(timespec='seconds')} {msg}", flush=True)


def env(name):
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"brak zmiennej {name}")
    return value


def http(url, headers=None, data=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    req.add_header("User-Agent", "homelab-dashboard-agent/1")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read()


def basic_auth(user, password):
    token = base64.b64encode(f"{user}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


# --- host ---------------------------------------------------------------


def read_cpu_times():
    with open("/proc/stat") as f:
        fields = [int(x) for x in f.readline().split()[1:]]
    idle = fields[3] + fields[4]  # idle + iowait
    return idle, sum(fields)


def collect_lab(config):
    idle1, total1 = read_cpu_times()
    time.sleep(5)
    idle2, total2 = read_cpu_times()
    busy = 1 - (idle2 - idle1) / max(total2 - total1, 1)

    meminfo = {}
    with open("/proc/meminfo") as f:
        for line in f:
            key, value = line.split(":", 1)
            meminfo[key] = int(value.split()[0]) * 1024
    ram_total = meminfo["MemTotal"]
    ram_used = ram_total - meminfo["MemAvailable"]

    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        temp = int(f.read()) / 1000

    with open("/proc/uptime") as f:
        uptime = float(f.read().split()[0])

    disks = []
    for disk in config["disks"]:
        st = os.statvfs(disk["path"])
        total = st.f_blocks * st.f_frsize
        used = (st.f_blocks - st.f_bfree) * st.f_frsize
        disks.append(
            {"kind": disk["kind"], "usedGb": round(used / GIB, 1), "totalGb": round(total / GIB, 1)}
        )

    lab = {
        "cpu": round(busy * 100, 1),
        "cpuTempC": round(temp, 1),
        "ramUsedGb": round(ram_used / GIB, 2),
        "ramTotalGb": round(ram_total / GIB, 2),
        "disks": disks,
        "uptimeDays": round(uptime / 86400, 2),
    }

    # Liczba kontenerow przez socket proxy Beszela (tylko GET). Awaria proxy
    # nie kasuje reszty sekcji — pole jest opcjonalne.
    try:
        _, body = http(env("DOCKER_URL").rstrip("/") + "/containers/json")
        lab["containers"] = len(json.loads(body))
    except Exception as e:
        log(f"lab.containers: {e}")

    return lab


# --- ruch sieciowy ------------------------------------------------------


def read_net_bytes(interfaces):
    rx = tx = 0
    with open("/proc/net/dev") as f:
        for line in f.readlines()[2:]:
            name, data = line.split(":", 1)
            if name.strip() in interfaces:
                cols = data.split()
                rx += int(cols[0])
                tx += int(cols[8])
    return rx, tx


def load_state():
    try:
        with open(STATE_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def save_state(state):
    tmp = STATE_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_PATH)


def collect_traffic(config, state):
    """Zwraca (sekcja, nowy_stan). Liczniki jadra zeruja sie po restarcie
    hosta, wiec sumy dzienne i laczne trzymamy w state.json."""
    rx, tx = read_net_bytes(config["interfaces"])
    today = datetime.date.today().isoformat()

    if state is None:
        state = {"since": today, "day": today, "last_rx": rx, "last_tx": tx,
                 "day_rx": 0, "day_tx": 0, "total_rx": 0, "total_tx": 0}
    else:
        state = dict(state)

    # Spadek licznika = restart hosta; wtedy licznik liczy od zera.
    d_rx = rx - state["last_rx"] if rx >= state["last_rx"] else rx
    d_tx = tx - state["last_tx"] if tx >= state["last_tx"] else tx

    if state["day"] != today:
        state["day"], state["day_rx"], state["day_tx"] = today, 0, 0

    state["day_rx"] += d_rx
    state["day_tx"] += d_tx
    state["total_rx"] += d_rx
    state["total_tx"] += d_tx
    state["last_rx"], state["last_tx"] = rx, tx

    traffic = {
        "downGbToday": round(state["day_rx"] / GIB, 2),
        "upGbToday": round(state["day_tx"] / GIB, 2),
        "downGbTotal": round(state["total_rx"] / GIB, 2),
        "upGbTotal": round(state["total_tx"] / GIB, 2),
        "totalSince": state["since"],
    }
    return traffic, state


# --- DNS (AdGuard) ------------------------------------------------------


def collect_dns():
    headers = basic_auth(env("ADGUARD_USER"), env("ADGUARD_PASSWORD"))
    _, body = http(env("ADGUARD_URL").rstrip("/") + "/control/stats", headers)
    stats = json.loads(body)

    # Przy retencji <= 7 dni AdGuard zwraca kubelki godzinowe (ostatni =
    # biezaca godzina). Przy dluzszej przechodzi na dni wyrownane do UTC,
    # czego nie da sie przeliczyc na dzien kalendarzowy w Polsce.
    if stats["time_units"] != "hours":
        raise RuntimeError("AdGuard: ustaw retencje statystyk na 7 dni")

    queries, blocked = stats["dns_queries"], stats["blocked_filtering"]
    hours_today = time.localtime().tm_hour + 1

    dns = {
        "queriesToday": sum(queries[-hours_today:]),
        "blockedToday": sum(blocked[-hours_today:]),
    }
    if len(queries) >= 168:
        dns["queriesWeek"] = sum(queries[-168:])
        dns["blockedWeek"] = sum(blocked[-168:])
    return dns


# --- uslugi (Uptime Kuma /metrics) --------------------------------------

METRIC_RE = re.compile(r"^(\w+)\{(.*)\}\s+(\S+)$")
LABEL_RE = re.compile(r'(\w+)="((?:[^"\\]|\\.)*)"')


def parse_kuma_metrics(text):
    monitors = {}
    for line in text.splitlines():
        m = METRIC_RE.match(line)
        if not m:
            continue
        name, labels, value = m.group(1), dict(LABEL_RE.findall(m.group(2))), float(m.group(3))
        mon = monitors.setdefault(labels.get("monitor_name"), {})
        if name == "monitor_status":
            mon["status"] = value
        elif name == "monitor_uptime_ratio" and labels.get("window") == "30d":
            mon["uptime30d"] = value
        elif name == "monitor_response_time_seconds" and labels.get("window") == "30d":
            mon["avg30d"] = value
    return monitors


def collect_services(config):
    _, body = http(env("KUMA_URL").rstrip("/") + "/metrics", basic_auth("", env("KUMA_API_KEY")))
    monitors = parse_kuma_metrics(body.decode())

    services = []
    for kind, names in config["services"].items():
        found = [monitors[n] for n in names if "status" in monitors.get(n, {})]
        missing = [n for n in names if n not in monitors]
        if missing:
            log(f"services.{kind}: brak monitorow {missing}")
        if not found:
            continue

        # 0 = down; 1 = up, 2 = pending (ponawianie), 3 = maintenance
        service = {"kind": kind, "up": all(m["status"] != 0 for m in found)}
        uptimes = [m["uptime30d"] for m in found if "uptime30d" in m]
        pings = [m["avg30d"] for m in found if "avg30d" in m]
        if uptimes:
            service["uptime30d"] = round(min(uptimes) * 100, 2)
        if pings:
            service["avgMs"] = round(sum(pings) / len(pings) * 1000)
        services.append(service)
    return services


# --- petla --------------------------------------------------------------


def collect(config, state):
    payload = {"v": 1}
    new_state = state

    for key, fn in (
        ("lab", lambda: collect_lab(config)),
        ("dns", collect_dns),
        ("services", lambda: collect_services(config)),
    ):
        try:
            payload[key] = fn()
        except Exception as e:
            log(f"{key}: {e}")

    try:
        payload["traffic"], new_state = collect_traffic(config, state)
    except Exception as e:
        log(f"traffic: {e}")

    payload["sentAt"] = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    return payload, new_state


def push(payload):
    headers = {"Authorization": f"Bearer {env('PUSH_TOKEN')}", "Content-Type": "application/json"}
    status, _ = http(env("PUSH_URL"), headers, json.dumps(payload).encode(), "POST")
    return status


def main():
    with open(CONFIG_PATH) as f:
        config = json.load(f)

    if "--dry-run" in sys.argv:
        payload, _ = collect(config, load_state())
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    interval = config["interval_seconds"]
    while True:
        started = time.monotonic()
        payload, state = collect(config, load_state())
        if state is not None:
            save_state(state)

        if len(payload) > 2:  # cos poza "v" i "sentAt"
            try:
                status = push(payload)
                with open(LAST_OK_PATH, "w") as f:
                    f.write(payload["sentAt"])
                # Push monitor Kumy: cisza = alert, ze agent nie wysyla.
                http(env("KUMA_PUSH_URL"))
            except Exception as e:
                log(f"push: {e}")

        time.sleep(max(interval - (time.monotonic() - started), 1))


if __name__ == "__main__":
    main()
