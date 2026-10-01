"""GitHub 잔디 그대로 + 그 위에서 마인크래프트 모험 (미리보기).

잔디 격자는 원본과 같은 위치/색(라이트·다크)으로 끝까지 유지된다.
광부가 지렁이처럼 칸을 따라 다니며 진한 칸에서 금/다이아를 캐고,
크리퍼가 뒤를 졸졸 따라온다. 맵 끝에서 대치 -> 검이 있으면 승리, 없으면 You Died!

usage: python generate_grid.py <github_user> [output.svg]
"""
import math
import re
import sys
import urllib.request

# ── 잔디 칸 텍스처: 깃허브 색 그대로, 픽셀 질감만 ─────────────
NOISE = ["01021001", "10010210", "02100102", "10201010",
         "01010201", "20100102", "01020010", "10010201"]
LIGHT = [("#ebedf0", "#eef0f2", "#e7e9ec"),
         ("#9be9a8", "#b4f0be", "#86dc95"),
         ("#40c463", "#5ad27a", "#34ad55"),
         ("#30a14e", "#3fb55e", "#278a42"),
         ("#216e39", "#2c8247", "#195a2e")]
DARK = [("#161b22", "#181e25", "#14191f"),
        ("#0e4429", "#135533", "#0a3520"),
        ("#006d32", "#0b803d", "#005a29"),
        ("#26a641", "#33b84f", "#1f8f37"),
        ("#39d353", "#52e06a", "#2fb746")]
ORES = {3: "gold", 4: "diamond"}

ITEM_PAL = {"Y": "#f5d44a", "o": "#c99a1a", "D": "#6ff5ea", "F": "#2bb5ad"}
ITEMS = {
    "gold": ["..Y..", ".YoY.", "YoYYo", ".YoY.", "..Y.."],
    "diamond": ["..D..", ".DFD.", "DFDDF", ".DFD.", "..D.."],
}

MINER_BODY = [".YYYYYY.", "YYYYYYYY", "HSSSSSSH", "SSSESSES",
              "SSSSSSSS", "BBBBBBBB", "SBBBBBBS", "SBBBBBBS", ".BBBBBB.", ".PPPPPP."]
MINER_LEGS_A = [".PP..PP.", ".KK..KK."]
MINER_LEGS_B = ["..PPPP..", "..KKKK.."]
PICKAXE = [".TTTTT.", "T..W..T", "...W...", "...W...", "...W..."]
MINER_PAL = {"Y": "#f2c230", "H": "#5a3a1e", "S": "#e8b48a", "E": "#2b2b2b",
             "B": "#3a8fd6", "P": "#3b3b7a", "K": "#3a2a1a", "W": "#8a5a2b", "T": "#b8c0c8"}
SWORD = [".D.", ".D.", ".D.", ".D.", ".D.", "WWW", ".H.", ".H."]
SWORD_PAL = {"diamond": {"D": "#6ff5ea", "W": "#2b2b2b", "H": "#7a5530"},
             "gold": {"D": "#f5d44a", "W": "#2b2b2b", "H": "#7a5530"}}
CREEPER = [".GlGGgG.", ".kkGlkk.", ".kkGGkk.", ".GgkkGl.", ".GkkkkG.", ".gkGGkG.",
           "..GlgG..", "..gGGl..", "..GGgG..", "..lGGg..", "..GgGG..", "..gGGg.."]
CREEPER_PAL = {"G": "#4fa83a", "g": "#3b8a2b", "l": "#7cc85e", "k": "#151515"}

# ── 레이아웃 / 타이밍 ─────────────────────────────────────────
CELL = 16           # 칸 간격
BLOCK = 13          # 칸 크기 (깃허브처럼 틈 3px)
MARGIN = 16
TOP = 34            # 카운터 공간
S = 1.5             # 캐릭터 픽셀 크기 (12x18)
SPAWN = 0.6
STEP = 0.11         # 한 칸 이동 시간
MINE = 0.45
GAP = 2.5           # 크리퍼가 몇 칸 뒤에서 따라오는지
FUSE = 1.3
DEATH = 3.2


def fetch_levels(user):
    url = f"https://github.com/users/{user}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "minecraft-contrib"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    cells = {}
    for m in re.finditer(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        tag = m.group(0)
        idm = re.search(r'contribution-day-component-(\d+)-(\d+)', tag)
        lvm = re.search(r'data-level="(\d)"', tag)
        if idm and lvm:
            cells[(int(idm.group(2)), int(idm.group(1)))] = int(lvm.group(1))
    total = re.search(r'([\d,]+)\s+contributions?\s+in the last year', html)
    return cells, (total.group(1) if total else None)


def pixel_rects(rows, pal, scale=1.0):
    out = []
    for y, row in enumerate(rows):
        x = 0
        while x < len(row):
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            run = 1
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            out.append(f'<rect x="{x*scale:g}" y="{y*scale:g}" width="{run*scale:g}" '
                       f'height="{scale:g}" fill="{pal[ch]}"/>')
            x += run
    return "".join(out)


def pct(t, total):
    return f"{max(0.0, min(100.0, t / total * 100)):.3f}%"


def center(c, r):
    return MARGIN + c * CELL + BLOCK / 2, TOP + r * CELL + BLOCK / 2


def plan(cells, weeks):
    """광부 경로: 칸 중심을 잇는 꺾은선 + 시간표. 진한 칸(금/다이아)을 왼쪽부터 들름."""
    ores = sorted((c, r) for (c, r), lv in cells.items() if lv in ORES)
    cur = (0, 3)
    pts = [cur]                          # 지나가는 칸 순서
    stops = {}                           # 경로 인덱스 -> 캐는 칸
    # 같은 주 안에서는 가까운 줄부터 (지그재그)
    by_col = {}
    for c, r in ores:
        by_col.setdefault(c, []).append(r)
    order = []
    for c in sorted(by_col):
        rows = sorted(by_col[c], key=lambda r: abs(r - cur[1]))
        for r in rows:
            order.append((c, r))
            cur = (c, r)
    cur = pts[0]
    for tgt in order + [(weeks - 1, None)]:
        tc, tr = tgt
        tr = cur[1] if tr is None else tr
        while cur[0] != tc:              # 가로 먼저
            cur = (cur[0] + (1 if tc > cur[0] else -1), cur[1])
            pts.append(cur)
        while cur[1] != tr:              # 그다음 세로
            cur = (cur[0], cur[1] + (1 if tr > cur[1] else -1))
            pts.append(cur)
        if tgt[1] is not None:
            stops[len(pts) - 1] = tgt
    # 시간표: (시간, 경로상 거리[칸])
    t = SPAWN + 0.35
    timeline = [(0, 0.0), (t, 0.0)]
    mined = {}
    if 0 in stops:
        mined[stops[0]] = t + 0.1
        t += MINE
        timeline.append((t, 0.0))
    for i in range(1, len(pts)):
        t += STEP
        timeline.append((t, float(i)))
        if i in stops:
            mined[stops[i]] = t + 0.1
            t += MINE
            timeline.append((t, float(i)))
    return pts, timeline, mined, t


def pos_at(pts, d):
    """경로상 거리 d(칸)의 좌표."""
    d = max(0.0, min(d, len(pts) - 1))
    i = int(d)
    f = d - i
    (c0, r0) = pts[i]
    (c1, r1) = pts[min(i + 1, len(pts) - 1)]
    x0, y0 = center(c0, r0)
    x1, y1 = center(c1, r1)
    return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f


def dist_at(timeline, t):
    if t <= timeline[0][0]:
        return timeline[0][1]
    for (t0, d0), (t1, d1) in zip(timeline, timeline[1:]):
        if t0 <= t <= t1:
            return d0 + (d1 - d0) * ((t - t0) / (t1 - t0) if t1 > t0 else 1)
    return timeline[-1][1]


def time_at_dist(timeline, d):
    for (t0, d0), (t1, d1) in zip(timeline, timeline[1:]):
        if d0 <= d <= d1 and d1 > d0:
            return t0 + (t1 - t0) * (d - d0) / (d1 - d0)
    return None


def route_keyframes(name, pts, track, T, ox, oy, extra_times=()):
    """track: [(t, 경로거리)] -> translate + 좌우 방향 키프레임."""
    kf, face = [], []
    last_dir = 1
    for i, (t, d) in enumerate(track):
        x, y = pos_at(pts, d)
        kf.append(f"{pct(t, T)}{{transform:translate({x - ox:.1f}px,{y - oy:.1f}px)}}")
        if i + 1 < len(track):
            nx, _ = pos_at(pts, track[i + 1][1])
            if abs(nx - x) > 0.01:
                last_dir = 1 if nx > x else -1
        face.append((t, last_dir))
    css = [f"@keyframes {name}{{{''.join(kf)}100%{{transform:translate({pos_at(pts, track[-1][1])[0] - ox:.1f}px,"
           f"{pos_at(pts, track[-1][1])[1] - oy:.1f}px)}}}}"]
    return css, face


def face_css(name, face, T, width_px, override=None):
    """좌우 뒤집기 (몸 중심 기준). override: [(t, dir)] 를 뒤에 덧붙임."""
    seq = face + (override or [])
    seq.sort()
    kf, prev = [], None
    for t, d in seq:
        if d != prev:
            tr = "scaleX(1)" if d == 1 else f"translateX({width_px}px) scaleX(-1)"
            kf.append(f"{pct(t, T)}{{transform:{tr}}}")
            prev = d
    first = "scaleX(1)" if seq[0][1] == 1 else f"translateX({width_px}px) scaleX(-1)"
    return (f"@keyframes {name}{{0%{{transform:{first}}}{''.join(kf)}}}"
            f".{name}{{animation:{name} {{T}}s infinite steps(1);transform-box:view-box;transform-origin:0 0}}")


def death_screen(width, height, score):
    cx, top = width / 2, TOP + 10
    return (
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#b00000" fill-opacity=".45"/>'
        f'<text x="{cx + 2}" y="{top + 26}" text-anchor="middle" class="big" fill="#3a0000">You Died!</text>'
        f'<text x="{cx}" y="{top + 24}" text-anchor="middle" class="big" fill="#ffffff">You Died!</text>'
        f'<text x="{cx}" y="{top + 48}" text-anchor="middle" class="mid" fill="#ffffff">'
        f'Score: <tspan fill="#ffd84a">{score}</tspan></text>'
        f'<rect x="{cx - 80}" y="{top + 60}" width="160" height="24" fill="#1a1a1a"/>'
        f'<rect x="{cx - 78}" y="{top + 62}" width="156" height="20" class="btn"/>'
        f'<text x="{cx}" y="{top + 76}" text-anchor="middle" class="mid" fill="#ffffff">Respawn</text>'
    )


def puff(css, cx, cy, t0, T, name, colors, n=8, spread=14):
    out = []
    for i in range(n):
        ang = 2 * math.pi * i / n
        dx, dy = math.cos(ang) * spread, math.sin(ang) * spread
        k = f"{name}{i}"
        css.append(f"@keyframes {k}{{0%,{pct(t0, T)}{{opacity:0;transform:translate(0,0)}}"
                   f"{pct(t0 + 0.03, T)}{{opacity:1}}"
                   f"{pct(t0 + 0.55, T)},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px)}}}}"
                   f".{k}{{opacity:0;animation:{k} {T:.2f}s infinite}}")
        out.append(f'<rect x="{cx - 2:.0f}" y="{cy - 2:.0f}" width="4" height="4" '
                   f'fill="{colors[i % len(colors)]}" class="{k}"/>')
    return "".join(out)


def build_svg(cells, total, user):
    weeks = max(c for c, _ in cells) + 1
    width = weeks * CELL + MARGIN * 2
    height = TOP + 7 * CELL + 30
    css = []

    # 잔디 칸 심볼 (색은 CSS 클래스로 -> 다크 모드 자동 전환)
    defs, light_css, dark_css = [], [], []
    for lv in range(5):
        rects = "".join(f'<rect x="{x}" y="{y}" width="1" height="1" class="c{lv}{ch}"/>'
                        for y, row in enumerate(NOISE) for x, ch in enumerate(row))
        defs.append(f'<symbol id="g{lv}" viewBox="0 0 8 8">{rects}'
                    f'<rect width="8" height="8" fill="none" stroke="#1b1f23" stroke-opacity=".08" stroke-width=".3"/></symbol>')
        for k in range(3):
            light_css.append(f".c{lv}{k}{{fill:{LIGHT[lv][k]}}}")
            dark_css.append(f".c{lv}{k}{{fill:{DARK[lv][k]}}}")
    for name, rows in ITEMS.items():
        defs.append(f'<symbol id="i-{name}" viewBox="0 0 5 5">{pixel_rects(rows, ITEM_PAL)}</symbol>')

    pts, timeline, mined, t_end = plan(cells, weeks)
    D = len(pts) - 1                                   # 광부 최종 거리

    # 결말 판정
    got = {"gold": 0, "diamond": 0}
    for cr in mined:
        got[ORES[cells[cr]]] += 1
    weapon = "diamond" if got["diamond"] >= 2 else "gold" if got["gold"] >= 2 else None

    # 크리퍼: 광부 GAP칸 뒤를 그대로 따라옴. 끝에서는 한 칸 반까지 다가옴
    c_track = []
    times = sorted({t for t, _ in timeline} |
                   {tt for v in range(len(pts)) if (tt := time_at_dist(timeline, v + GAP)) is not None})
    for t in times:
        c_track.append((t, max(0.0, dist_at(timeline, t) - GAP)))
    ta = t_end + 0.1
    close = max(0.0, D - 1.3)
    c_track.append((ta + 0.4, close))
    cs = time_at_dist(timeline, GAP) or SPAWN + 0.6     # 크리퍼 스폰 시각
    f0 = ta + 0.5
    if weapon:
        craft = f0 + 0.35
        h1, h2 = craft + 0.75, craft + 1.05
        boom = None
        T = h2 + 3.0
    else:
        boom = f0 + FUSE
        T = boom + DEATH

    # 잔디 칸 (끝까지 그대로). 캐는 칸은 통통 + 반짝
    grid = []
    counter = {"gold": (width - MARGIN - 100, 8), "diamond": (width - MARGIN - 46, 8)}
    items = []
    for (c, r), lv in sorted(cells.items()):
        x, y = MARGIN + c * CELL, TOP + r * CELL
        use = f'<use href="#g{lv}" x="{x}" y="{y}" width="{BLOCK}" height="{BLOCK}"/>'
        if (c, r) in mined:
            tb = mined[(c, r)]
            n = f"m{c}_{r}"
            css.append(f"@keyframes {n}{{0%,{pct(tb, T)}{{transform:scale(1)}}{pct(tb + 0.08, T)}{{transform:scale(1.25)}}"
                       f"{pct(tb + 0.2, T)},100%{{transform:scale(1)}}}}"
                       f".{n}{{animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
            grid.append(f'<g class="{n}">{use}</g>')
            kind = ORES[lv]
            cx, cy = counter[kind]
            dx, dy = cx - x, cy - y
            fa, fb = tb + 0.12, tb + 0.8
            css.append(f"@keyframes f{n}{{0%,{pct(fa - 0.01, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(fa, T)}{{opacity:1;transform:translate(0,-8px)}}"
                       f"{pct(fb, T)}{{opacity:1;transform:translate({dx:.0f}px,{dy:.0f}px)}}"
                       f"{pct(fb + 0.05, T)},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px)}}}}"
                       f".f{n}{{opacity:0;animation:f{n} {T:.2f}s infinite}}")
            items.append(f'<use href="#i-{kind}" x="{x}" y="{y}" width="{BLOCK}" height="{BLOCK}" class="f{n}"/>')
        else:
            grid.append(use)

    # 카운터
    hud = []
    for kind, (cx, cy) in counter.items():
        hud.append(f'<use href="#i-{kind}" x="{cx}" y="{cy}" width="13" height="13"/>')
        ts = sorted(t + 0.8 for cr, t in mined.items() if ORES[cells[cr]] == kind)
        edges = [0.0] + ts + [T]
        for k in range(len(edges) - 1):
            a, b = edges[k], edges[k + 1]
            n = f"c{kind}{k}"
            if len(edges) == 2:
                kf = "0%,100%{opacity:1}"
            elif k == 0:
                kf = f"0%,{pct(b - 0.001, T)}{{opacity:1}}{pct(b, T)},100%{{opacity:0}}"
            elif k == len(edges) - 2:
                kf = f"0%,{pct(a - 0.001, T)}{{opacity:0}}{pct(a, T)},99.9%{{opacity:1}}100%{{opacity:0}}"
            else:
                kf = (f"0%,{pct(a - 0.001, T)}{{opacity:0}}{pct(a, T)},{pct(b - 0.001, T)}{{opacity:1}}"
                      f"{pct(b, T)},100%{{opacity:0}}")
            css.append(f"@keyframes {n}{{{kf}}}.{n}{{animation:{n} {T:.2f}s infinite steps(1)}}")
            hud.append(f'<text x="{cx + 17}" y="{cy + 11}" class="t {n}">×{k}</text>')

    # 이동 (스프라이트 발이 칸 중심 아래쪽에 오도록)
    sw, sh = 8 * S, 12 * S
    ox, oy = sw / 2, sh - 4
    m_css, m_face = route_keyframes("mpath", pts, timeline + [(T, D)], T, ox, oy)
    c_css, c_face = route_keyframes("cpath", pts, c_track + [(T, close)], T, ox, oy)
    css += m_css + c_css
    # 끝에서 광부는 크리퍼 쪽(뒤)으로 돌아봄
    back = -1 if pos_at(pts, close)[0] < pos_at(pts, D)[0] else 1
    css.append(face_css("mface", m_face, T, sw, [(t_end + 0.05, back)]).replace("{T}", f"{T:.2f}"))
    css.append(face_css("cface", c_face, T, sw, [(ta + 0.4, -back)]).replace("{T}", f"{T:.2f}"))

    css.append(f"@keyframes mspawn{{0%,{pct(SPAWN - 0.01, T)}{{opacity:0}}{pct(SPAWN + 0.2, T)},100%{{opacity:1}}}}")
    css.append(f"@keyframes cspawn{{0%,{pct(cs - 0.01, T)}{{opacity:0}}{pct(cs + 0.25, T)},100%{{opacity:1}}}}")
    sx, sy = center(*pts[0])
    fx_svg = puff(css, sx, sy, SPAWN, T, "ms", ["#ffffff", "#fff3a0", "#cfe8ff"])
    fx_svg += puff(css, sx, sy, cs, T, "cs", ["#7cc85e", "#4fa83a", "#cccccc"])

    # 광부 도구 / 결말 연출
    mx, my = pos_at(pts, D)
    tool = f'<g class="tool1">{pixel_rects(PICKAXE, MINER_PAL, S)}</g>'
    m_open, m_close, m_extra = "", "", ""
    ccx, ccy = pos_at(pts, close)
    if weapon:
        css.append(f"@keyframes tool1{{0%,{pct(craft + 0.5, T)}{{opacity:1}}{pct(craft + 0.51, T)},99.9%{{opacity:0}}100%{{opacity:1}}}}"
                   f".tool1{{animation:tool1 {T:.2f}s infinite steps(1)}}")
        css.append(f"@keyframes tool2{{0%,{pct(craft + 0.5, T)}{{opacity:0}}{pct(craft + 0.51, T)},99.9%{{opacity:1}}100%{{opacity:0}}}}"
                   f".tool2{{opacity:0;animation:tool2 {T:.2f}s infinite steps(1)}}")
        tool += f'<g class="tool2" transform="translate({2*S} {-1*S})">{pixel_rects(SWORD, SWORD_PAL[weapon], S)}</g>'
        css.append(f"@keyframes mwin{{0%,{pct(h2 + 1.3, T)}{{transform:translateY(0)}}"
                   f"{pct(h2 + 1.5, T)}{{transform:translateY(-8px)}}{pct(h2 + 1.7, T)},100%{{transform:translateY(0)}}}}"
                   f".mwin{{animation:mwin {T:.2f}s infinite}}")
        m_open, m_close = '<g class="mwin">', '</g>'
        # 광석 2개가 머리 위로 -> 검
        for i in range(2):
            cx, cy = counter[weapon]
            n = f"cr{i}"
            t1 = craft + i * 0.1
            css.append(f"@keyframes {n}{{0%,{pct(t1, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(t1 + 0.02, T)}{{opacity:1}}"
                       f"{pct(t1 + 0.4, T)}{{opacity:1;transform:translate({mx - cx - 6:.0f}px,{my - 30 - cy:.0f}px)}}"
                       f"{pct(t1 + 0.45, T)},100%{{opacity:0;transform:translate({mx - cx - 6:.0f}px,{my - 30 - cy:.0f}px)}}}}"
                       f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite}}")
            fx_svg += f'<use href="#i-{weapon}" x="{cx}" y="{cy}" width="12" height="12" class="{n}"/>'
        fx_svg += puff(css, mx, my - 24, craft + 0.5, T, "cf", ["#ffffff", "#fff3a0", "#cfe8ff"])
        fx_svg += puff(css, ccx, ccy - 6, h2 + 0.85, T, "cd", ["#ffffff", "#d0d0d0", "#a0a0a0"], n=10, spread=16)
        for i in range(6):
            n = f"xp{i}"
            t1 = h2 + 1.0 + i * 0.08
            css.append(f"@keyframes {n}{{0%,{pct(t1, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(t1 + 0.05, T)}{{opacity:1;transform:translate({(i % 3 - 1) * 5}px,-8px)}}"
                       f"{pct(t1 + 0.5, T)}{{opacity:1;transform:translate({mx - ccx:.0f}px,{my - ccy - 6:.0f}px)}}"
                       f"{pct(t1 + 0.55, T)},100%{{opacity:0}}}}"
                       f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite}}")
            fx_svg += (f'<rect x="{ccx - 3:.0f}" y="{ccy - 9:.0f}" width="6" height="6" '
                       f'fill="{"#b5f23c" if i % 2 else "#e6ff5a"}" stroke="#4a7a10" stroke-width="1" class="{n}"/>')
    else:
        shake = [f"0%,{pct(f0, T)}{{transform:translateX(0)}}"]
        tt, sgn = f0, 1
        while tt < boom:
            tt += 0.06
            shake.append(f"{pct(tt, T)}{{transform:translateX({sgn}px)}}")
            sgn = -sgn
        shake.append(f"{pct(boom + 0.01, T)},100%{{transform:translateX(0)}}")
        css.append(f"@keyframes mshake{{{''.join(shake)}}}.mshake{{animation:mshake {T:.2f}s infinite steps(1)}}")
        css.append(f"@keyframes mdie{{0%,{pct(boom, T)}{{transform:rotate(0);opacity:1}}"
                   f"{pct(boom + 0.35, T)}{{transform:rotate(-90deg);opacity:1}}"
                   f"{pct(boom + 0.95, T)},99.9%{{transform:rotate(-90deg);opacity:0}}100%{{transform:rotate(0);opacity:1}}}}"
                   f".mdie{{animation:mdie {T:.2f}s infinite;transform-box:fill-box;transform-origin:50% 100%}}")
        css.append(f"@keyframes mred{{0%,{pct(boom, T)}{{opacity:0}}{pct(boom + 0.05, T)},99.9%{{opacity:.6}}100%{{opacity:0}}}}"
                   f".mred{{opacity:0;animation:mred {T:.2f}s infinite steps(1)}}")
        m_extra = f'<g class="mred">{pixel_rects(MINER_BODY + MINER_LEGS_A, {k: "#ff2a2a" for k in MINER_PAL}, S)}</g>'
        m_open, m_close = '<g class="mdie"><g class="mshake">', '</g></g>'
        fx_svg += puff(css, mx, my - 6, boom + 0.9, T, "md", ["#ffffff", "#d0d0d0", "#a0a0a0"], n=10, spread=16)
        # 폭발
        colors = ["#ff9a2e", "#6e6e6e", "#ffd25a", "#8f8f8f", "#ff6a2b", "#555555"]
        for i in range(16):
            ang = 2 * math.pi * i / 16
            dist = 26 + (i * 7) % 20
            size = 6 + (i * 5) % 7
            n = f"pf{i}"
            css.append(f"@keyframes {n}{{0%,{pct(boom, T)}{{opacity:0;transform:translate(0,0) scale(.4)}}"
                       f"{pct(boom + 0.03, T)}{{opacity:1}}"
                       f"{pct(boom + 0.7, T)},100%{{opacity:0;transform:translate({math.cos(ang)*dist:.0f}px,{math.sin(ang)*dist:.0f}px) scale(1.6)}}}}"
                       f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
            fx_svg += (f'<rect x="{ccx - size/2:.0f}" y="{ccy - size/2:.0f}" width="{size}" height="{size}" '
                       f'fill="{colors[i % 6]}" class="{n}"/>')
        css.append(f"@keyframes core{{0%,{pct(boom, T)}{{opacity:0;transform:scale(.3)}}{pct(boom + 0.05, T)}{{opacity:.95;transform:scale(1.2)}}"
                   f"{pct(boom + 0.35, T)},100%{{opacity:0;transform:scale(1.8)}}}}"
                   f".core{{opacity:0;animation:core {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
        fx_svg += f'<rect x="{ccx - 12:.0f}" y="{ccy - 12:.0f}" width="24" height="24" fill="#ffc04a" class="core"/>'
        d0 = boom + 1.1
        css.append(f"@keyframes dov{{0%,{pct(d0, T)}{{opacity:0}}{pct(d0 + 0.35, T)},{pct(T - 0.3, T)}{{opacity:1}}100%{{opacity:0}}}}"
                   f".dov{{opacity:0;animation:dov {T:.2f}s infinite}}")

    miner = (
        f'<g class="mpath"><g class="mspawn">{m_open}<g class="mface">'
        f'{pixel_rects(MINER_BODY, MINER_PAL, S)}'
        f'<g class="legA" transform="translate(0 {10*S})">{pixel_rects(MINER_LEGS_A, MINER_PAL, S)}</g>'
        f'<g class="legB" transform="translate(0 {10*S})">{pixel_rects(MINER_LEGS_B, MINER_PAL, S)}</g>'
        f'<g transform="translate({7*S} {3*S})"><g class="swing">{tool}</g></g>'
        f'{m_extra}</g>{m_close}</g></g>'
    )

    # 크리퍼 깜빡임 / 퓨즈
    if boom:
        css.append(f"@keyframes fuse{{0%,{pct(f0, T)}{{transform:scale(1);opacity:1}}"
                   f"{pct(f0 + 0.3, T)}{{transform:scale(1.06)}}{pct(f0 + 0.55, T)}{{transform:scale(1)}}"
                   f"{pct(f0 + 0.85, T)}{{transform:scale(1.12)}}{pct(f0 + 1.0, T)}{{transform:scale(1.04)}}"
                   f"{pct(boom, T)}{{transform:scale(1.3);opacity:1}}"
                   f"{pct(boom + 0.01, T)},99.9%{{opacity:0}}100%{{opacity:1;transform:scale(1)}}}}")
        blinks = [(f0 + 0.1, f0 + 0.3), (f0 + 0.55, f0 + 0.75), (f0 + 0.95, f0 + 1.1), (f0 + 1.18, boom)]
        cred = ""
    else:
        kb = -6 * back * -1   # 광부 반대쪽으로 밀림
        css.append(f"@keyframes fuse{{0%,{pct(f0, T)}{{transform:translate(0,0) scale(1);opacity:1}}"
                   f"{pct(f0 + 0.3, T)}{{transform:scale(1.06)}}{pct(f0 + 0.55, T)}{{transform:scale(1)}}"
                   f"{pct(f0 + 0.85, T)}{{transform:scale(1.1)}}"
                   f"{pct(h1, T)}{{transform:translate(0,0) scale(1.1)}}"
                   f"{pct(h1 + 0.08, T)}{{transform:translate({kb}px,-3px) scale(1)}}"
                   f"{pct(h2, T)}{{transform:translate({kb}px,0) rotate(0)}}"
                   f"{pct(h2 + 0.1, T)}{{transform:translate({2*kb}px,-3px) rotate(0)}}"
                   f"{pct(h2 + 0.45, T)}{{transform:translate({2*kb}px,0) rotate(-90deg);opacity:1}}"
                   f"{pct(h2 + 0.9, T)},99.9%{{transform:translate({2*kb}px,0) rotate(-90deg);opacity:0}}"
                   f"100%{{transform:none;opacity:1}}}}")
        blinks = [(f0 + 0.1, f0 + 0.3), (f0 + 0.55, f0 + 0.75)]
        css.append(f"@keyframes cred{{0%{{opacity:0}}{pct(h1, T)}{{opacity:.65}}{pct(h1 + 0.15, T)}{{opacity:0}}"
                   f"{pct(h2, T)}{{opacity:.65}}{pct(h2 + 0.9, T)},100%{{opacity:0}}}}"
                   f".cred{{opacity:0;animation:cred {T:.2f}s infinite steps(1)}}")
        cred = f'<g class="cred">{pixel_rects(CREEPER, {k: "#ff2a2a" for k in CREEPER_PAL}, S)}</g>'
    kf = "0%{opacity:0}" + "".join(f"{pct(a, T)}{{opacity:.85}}{pct(b, T)}{{opacity:0}}" for a, b in blinks)
    css.append(f"@keyframes flash{{{kf}100%{{opacity:0}}}}")
    creeper = (
        f'<g class="cpath"><g class="cspawn"><g class="fuse"><g class="cface"><g class="crawl">'
        f'{pixel_rects(CREEPER, CREEPER_PAL, S)}'
        f'<g class="flash">{pixel_rects(CREEPER, {k: "#ffffff" for k in CREEPER_PAL}, S)}</g>{cred}'
        f'</g></g></g></g></g>'
    )

    # 범례 (깃허브와 같은 Less ~ More)
    ly = TOP + 7 * CELL + 8
    lx = width - MARGIN - 5 * 15 - 30
    legend = [f'<text x="{lx - 6}" y="{ly + 10}" text-anchor="end" class="t">Less</text>']
    legend += [f'<use href="#g{i}" x="{lx + i*15}" y="{ly}" width="{BLOCK}" height="{BLOCK}"/>' for i in range(5)]
    legend.append(f'<text x="{lx + 5*15 + 2}" y="{ly + 10}" class="t">More</text>')
    label = f"⛏ {user}" + (f" · {total} contributions" if total else "")
    legend.append(f'<text x="{MARGIN}" y="{ly + 10}" class="t">{label}</text>')

    death = (f'<g class="dov">{death_screen(width, height, total or len(mined))}</g>' if boom else "")
    style = f"""
{''.join(light_css)}
@media (prefers-color-scheme:dark){{{''.join(dark_css)}}}
.t{{font:600 11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#8b949e}}
.big{{font:700 28px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
.mid{{font:600 12px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
.btn{{animation:btn 1.2s steps(1) infinite}}
@keyframes btn{{0%{{fill:#6f6f6f}}50%{{fill:#8a8fd0}}}}
.mpath{{animation:mpath {T:.2f}s linear infinite}}
.cpath{{animation:cpath {T:.2f}s linear infinite}}
.mspawn{{opacity:0;animation:mspawn {T:.2f}s infinite}}
.cspawn{{opacity:0;animation:cspawn {T:.2f}s infinite}}
.legA{{animation:legA .3s steps(1) infinite}}
.legB{{animation:legB .3s steps(1) infinite}}
@keyframes legA{{0%{{opacity:1}}50%{{opacity:0}}}}
@keyframes legB{{0%{{opacity:0}}50%{{opacity:1}}}}
.swing{{animation:swing .25s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:50% 100%}}
@keyframes swing{{0%{{transform:rotate(-30deg)}}100%{{transform:rotate(40deg)}}}}
.fuse{{animation:fuse {T:.2f}s infinite;transform-box:fill-box;transform-origin:50% 100%}}
.flash{{opacity:0;animation:flash {T:.2f}s infinite steps(1)}}
.crawl{{animation:crawl .5s ease-in-out infinite alternate;transform-box:fill-box;transform-origin:50% 100%}}
@keyframes crawl{{0%{{transform:scale(1.03,.97)}}100%{{transform:scale(.98,1.02)}}}}
{''.join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.mpath,.cpath,.dov{{display:none}}}}
"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" shape-rendering="crispEdges">'
        f'<style>{style}</style><defs>{"".join(defs)}</defs>'
        f'{"".join(grid)}{"".join(items)}{creeper}{miner}{fx_svg}'
        f'{"".join(hud)}{"".join(legend)}{death}</svg>'
    ), T


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "haeunjeon0410"
    out = sys.argv[2] if len(sys.argv) > 2 else "grid-preview.svg"
    cells, total = fetch_levels(user)
    svg, T = build_svg(cells, total, user)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{out}: cycle={T:.1f}s")


if __name__ == "__main__":
    main()
