"""GitHub Actions 每 3 小時執行一次：抓 Open-Meteo 的預報，存成網站上的共用檔案。

用法：python3 tools/fetch_forecast.py 輸出資料夾
- 把 index.html 複製到輸出資料夾
- 抓天氣（16 天）、空氣品質（7 天）、系集預報（10 天），寫成 forecast.json、ensemble.json
- 抓失敗的話，改用網站上目前那一份（不會變成空的）

檢查點的座標用跟網頁一樣的方法，從 index.html 裡的 ROUTE_PTS、CHECKPOINTS 算出來，
所以改路線之後不用改這個程式。只用 Python 內建的功能，不用另外安裝套件。
"""
import json
import math
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request

SITE_URL = os.environ.get("SITE_URL", "https://azchen2002.github.io/bike-south/")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GROUP_SIZE = 4


def log(msg):
    print(msg, flush=True)


# ---------- 從 index.html 算出檢查點座標（跟網頁的 distKm、pointAtKm 一樣） ----------
def read_points(html):
    route = json.loads(re.search(r"const ROUTE_PTS = (\[\[.*?\]\]);", html, re.S).group(1))
    cp_block = re.search(r"const CHECKPOINTS = \[(.*?)\];", html, re.S).group(1)
    cp_kms = [float(x) for x in re.findall(r"km:\s*([\d.]+)", cp_block)]
    ens_raw = re.search(r"const ENS_CPS = \[(.*?)\];", html).group(1)

    def dist_km(a, b):
        p1, p2 = math.radians(a[0]), math.radians(b[0])
        dp, dl = p2 - p1, math.radians(b[1] - a[1])
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(h))

    cum = [0.0]
    for i in range(1, len(route)):
        cum.append(cum[-1] + dist_km(route[i - 1], route[i]))
    cp_kms[-1] = cum[-1]

    def point_at_km(km):
        i = 0
        while i < len(cum) - 2 and cum[i + 1] < km:
            i += 1
        seg = (cum[i + 1] - cum[i]) or 1
        f = min(1, max(0, (km - cum[i]) / seg))
        a, b = route[i], route[i + 1]
        return [round(a[0] + (b[0] - a[0]) * f, 4), round(a[1] + (b[1] - a[1]) * f, 4)]

    points = [point_at_km(km) for km in cp_kms]
    last = len(points) - 1
    ens_idx = [last if x.strip() == "LAST_CP" else int(x) for x in ens_raw.split(",")]
    return points, ens_idx


# ---------- 抓資料 ----------
def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "bike-south-forecast (GitHub Actions)"})
    with urllib.request.urlopen(req, timeout=90) as res:
        text = res.read().decode("utf-8")
    # 有時候資料裡會混進 nan、inf，換成 null
    return json.loads(re.sub(r"-?\b(nan|NaN|inf|Infinity)\b", "null", text))


def fetch_groups(base, extra, points, group_size):
    out = []
    for i in range(0, len(points), group_size):
        group = points[i:i + group_size]
        params = {
            "latitude": ",".join(f"{p[0]:.4f}" for p in group),
            "longitude": ",".join(f"{p[1]:.4f}" for p in group),
            "timezone": "Asia/Taipei",
            **extra,
        }
        url = base + "?" + urllib.parse.urlencode(params)
        for attempt in range(3):
            try:
                r = get_json(url)
                out.extend(r if isinstance(r, list) else [r])
                break
            except Exception as e:
                code = getattr(e, "code", None)
                log(f"  第 {i // group_size + 1} 組失敗（{code or e}），第 {attempt + 1} 次")
                if code == 400 or attempt == 2:
                    raise
                time.sleep(20 * (attempt + 1))
        time.sleep(2)  # 慢慢抓，不要一次打太多
    return out


def previous(name):
    """抓不到新的，就用網站上目前那一份"""
    try:
        old = get_json(SITE_URL + name + "?t=" + str(int(time.time())))
        log(f"  改用網站上目前的 {name}（{time.strftime('%m/%d %H:%M', time.localtime(old['generatedAt'] / 1000))} 抓的）")
        return old
    except Exception as e:
        log(f"  網站上也沒有可用的 {name}（{e}）")
        return None


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else "site"
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(ROOT, "index.html")
    shutil.copy(html_path, os.path.join(out_dir, "index.html"))
    points, ens_idx = read_points(open(html_path, encoding="utf-8").read())
    now_ms = int(time.time() * 1000)
    log(f"{len(points)} 個檢查點，系集預報用第 {ens_idx} 個")

    # 天氣 + 空氣品質
    forecast = None
    try:
        data = fetch_groups("https://api.open-meteo.com/v1/forecast", {
            "hourly": "temperature_2m,apparent_temperature,precipitation_probability,precipitation,"
                      "wind_speed_10m,wind_direction_10m,wind_gusts_10m",
            "daily": "sunrise,sunset", "forecast_days": "16", "wind_speed_unit": "kmh",
        }, points, GROUP_SIZE)
        try:
            air = fetch_groups("https://air-quality-api.open-meteo.com/v1/air-quality",
                               {"hourly": "us_aqi", "forecast_days": "7"}, points, GROUP_SIZE)
        except Exception as e:
            log(f"空氣品質抓不到（{e}），先不放")
            air = None
        forecast = {"generatedAt": now_ms, "points": points, "data": data, "air": air}
        log("天氣預報：抓到新的")
    except Exception as e:
        log(f"天氣預報抓不到（{e}）")
        forecast = previous("forecast.json")

    # 系集預報
    ensemble = None
    ens_points = [points[i] for i in ens_idx]
    for model in ["ecmwf_ifs025", "gfs_seamless"]:
        try:
            lst = fetch_groups("https://ensemble-api.open-meteo.com/v1/ensemble", {
                "hourly": "wind_speed_10m,wind_direction_10m", "models": model,
                "forecast_days": "10", "wind_speed_unit": "kmh",
            }, ens_points, 1)
            ensemble = {"generatedAt": now_ms, "points": ens_points, "ens": {"model": model, "list": lst}}
            log(f"系集預報：抓到新的（{model}）")
            break
        except Exception as e:
            log(f"系集預報 {model} 抓不到（{e}）")
    if ensemble is None:
        ensemble = previous("ensemble.json")

    for name, obj in [("forecast.json", forecast), ("ensemble.json", ensemble)]:
        if obj:
            with open(os.path.join(out_dir, name), "w", encoding="utf-8") as f:
                json.dump(obj, f, separators=(",", ":"), ensure_ascii=False)
            log(f"寫出 {name}（{os.path.getsize(os.path.join(out_dir, name)) // 1024} KB）")


if __name__ == "__main__":
    main()
