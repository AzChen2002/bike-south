"""從 GPX 產生 index.html 裡的 ROUTE_PTS 和 CHECKPOINTS。

用法：python3 tools/prep_route.py 路線.gpx route.json
- 從最接近南寮漁港的點開始截取到 GPX 終點
- 用 Ramer–Douglas–Peucker 簡化點數（容許誤差約 15 公尺）
- 把簡化後的路線寫進 route.json（貼到 index.html 的 ROUTE_PTS）
- 印出每 ~20 km 一個檢查點，以及最近的鄉鎮名稱（貼到 CHECKPOINTS）
"""
import re, sys, math, json
txt = open(sys.argv[1], encoding="utf-8").read()
pts = [(float(a), float(b)) for a, b in re.findall(r'<trkpt lat="([-\d.]+)" lon="([-\d.]+)"', txt)]
def hav(p, q):
    R = 6371.0; la1, lo1, la2, lo2 = map(math.radians, (*p, *q))
    a = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*R*math.asin(math.sqrt(a))
# 去掉重複點
dedup = [pts[0]]
for p in pts[1:]:
    if p != dedup[-1]: dedup.append(p)
pts = dedup
NANLIAO = (24.8484, 120.9257)  # 南寮漁港
si = min(range(len(pts)), key=lambda k: hav(pts[k], NANLIAO))
print("start idx", si, pts[si], "dist to 南寮 %.2f km" % hav(pts[si], NANLIAO))
route = pts[si:]
def length(r): return sum(hav(r[i-1], r[i]) for i in range(1, len(r)))
print("trimmed km %.1f, points %d" % (length(route), len(route)))
# Ramer–Douglas–Peucker（用平面近似）
def rdp(points, eps):
    keep = [False]*len(points); keep[0] = keep[-1] = True
    stack = [(0, len(points)-1)]
    k = math.cos(math.radians(24))
    def d(p, a, b):
        x, y = (p[1]-a[1])*k, p[0]-a[0]; bx, by = (b[1]-a[1])*k, b[0]-a[0]
        L = bx*bx + by*by
        if L == 0: return math.hypot(x, y)
        t = max(0, min(1, (x*bx + y*by)/L))
        return math.hypot(x - t*bx, y - t*by)
    while stack:
        s, e = stack.pop(); dmax, idx = 0, None
        for i in range(s+1, e):
            dd = d(points[i], points[s], points[e])
            if dd > dmax: dmax, idx = dd, i
        if idx is not None and dmax > eps:
            keep[idx] = True; stack += [(s, idx), (idx, e)]
    return [p for p, kk in zip(points, keep) if kk]
simp = rdp(route, 0.00015)
print("simplified points %d, km %.1f" % (len(simp), length(simp)))
json.dump([[round(a, 5), round(b, 5)] for a, b in simp], open(sys.argv[2], "w"), separators=(",", ":"))
# 每 ~20 km 一個檢查點，標上最近的鄉鎮
towns = {"南寮":(24.848,120.926),"香山":(24.776,120.913),"竹南":(24.686,120.877),"後龍":(24.612,120.786),"白沙屯":(24.555,120.708),"通霄":(24.489,120.677),"苑裡":(24.441,120.649),"大甲":(24.348,120.623),"大安":(24.346,120.586),"清水":(24.268,120.570),"梧棲":(24.255,120.531),"龍井":(24.193,120.546),"伸港":(24.157,120.483),"線西":(24.130,120.466),"鹿港":(24.057,120.434),"福興":(24.040,120.405),"芳苑":(23.925,120.320),"大城":(23.855,120.321),"麥寮":(23.754,120.252),"台西":(23.703,120.197),"四湖":(23.637,120.226),"口湖":(23.586,120.185),"東石":(23.459,120.154),"布袋":(23.378,120.166),"北門":(23.268,120.126),"將軍":(23.199,120.157),"七股":(23.140,120.098),"安南":(23.047,120.185),"台南":(22.993,120.205),"茄萣":(22.906,120.183),"永安":(22.819,120.225),"彌陀":(22.783,120.247),"梓官":(22.760,120.267),"左營":(22.687,120.307)}
cum = [0.0]
for i in range(1, len(simp)): cum.append(cum[-1] + hav(simp[i-1], simp[i]))
total = cum[-1]
n = round(total / 20)
out = []
for j in range(n+1):
    target = total * j / n
    i = min(range(len(simp)), key=lambda k: abs(cum[k]-target))
    p = simp[i]
    name, dist = min(((t, hav(p, c)) for t, c in towns.items()), key=lambda x: x[1])
    out.append((round(cum[i], 1), p, name, round(dist, 1)))
for o in out: print(o)
