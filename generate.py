"""GitHub 잔디 -> 마인크래프트 풍 점프맵 광질 애니메이션 SVG.

커밋한 날만 블록으로 떠 있고, 광부가 첫 블록에 리스폰해서 블록을 밟고 점프하며
금/다이아를 캔다. 뒤에서는 크리퍼가 따라오다가 마지막에 터질락 말락 하다 펑.
커밋이 하나도 없으면 사망 화면(You Died! / Respawn)을 보여준다.

usage: python generate.py <github_user> [output.svg]
의존성 없음 (표준 라이브러리만 사용).
"""
import math
import re
import sys
import urllib.request

# ── 8x8 픽셀 텍스처 (직접 그린 것) ─────────────────────────────
PALETTE = {
    "a": "#8f8f8f", "b": "#7a7a7a", "c": "#a3a3a3", "d": "#6b6b6b",  # stone
    "e": "#8b5a2b", "f": "#6f4520", "g": "#a06a38", "h": "#5a3818",  # dirt
    "i": "#5fb83a", "j": "#4a9a2c", "k": "#78cc4f",                  # grass
    "Y": "#f5d44a", "o": "#c99a1a",                                  # gold
    "D": "#6ff5ea", "F": "#2bb5ad",                                  # diamond
    "p": "#b8894f", "q": "#a0743f", "r": "#7a5530",                  # planks
}
DIRT = ["efegeefh", "egeefege", "feehegef", "egefeehe",
        "hefegefe", "eegefheg", "gefeegef", "efhegeef"]
GRASS = ["ikijkiji", "jiikjiki", "iejiefji",
         "egefeehe", "hefegefe", "eegefheg", "gefeegef", "efhegeef"]
GOLD = ["aabacaab", "aYoadaca", "caYoaaba", "aadaaYob",
        "baacaYoa", "aYoabada", "abYoacaa", "aacabaab"]
DIAMOND = ["aabacaab", "abaDFaca", "caaFDaba", "aDFaacab",
           "bFDcabDa", "acaabFDa", "abdaacaa", "aacabaab"]
PLANK = ["pppqpppp", "pqppppqp", "rrrrrrrr", "ppppqppp",
         "qppppppq", "rrrrrrrr", "ppqppppp", "pppppqpp"]
BLOCKS = {1: DIRT, 2: GRASS, 3: GOLD, 4: DIAMOND}
ORES = {3: "gold", 4: "diamond"}

ITEMS = {
    "gold": ["..Y..", ".YoY.", "YoYYo", ".YoY.", "..Y.."],
    "diamond": ["..D..", ".DFD.", "DFDDF", ".DFD.", "..D.."],
}

# 광부 (8x12). 다리는 두 프레임.
MINER_BODY = [".YYYYYY.", "YYYYYYYY", "HSSSSSSH", "SSSESSES",
              "SSSSSSSS", "BBBBBBBB", "SBBBBBBS", "SBBBBBBS", ".BBBBBB.", ".PPPPPP."]
MINER_LEGS_A = [".PP..PP.", ".KK..KK."]
MINER_LEGS_B = ["..PPPP..", "..KKKK.."]
PICKAXE = [".TTTTT.", "T..W..T", "...W...", "...W...", "...W..."]
MINER_PAL = {"Y": "#f2c230", "H": "#5a3a1e", "S": "#e8b48a", "E": "#2b2b2b",
             "B": "#3a8fd6", "P": "#3b3b7a", "K": "#3a2a1a", "W": "#8a5a2b", "T": "#b8c0c8"}

# 검 (3x8). 날 색은 재료에 따라.
SWORD = [".D.", ".D.", ".D.", ".D.", ".D.", "WWW", ".H.", ".H."]
SWORD_PAL = {"diamond": {"D": "#6ff5ea", "W": "#2b2b2b", "H": "#7a5530"},
             "gold": {"D": "#f5d44a", "W": "#2b2b2b", "H": "#7a5530"}}

# 크리퍼 풍 몬스터 (8x12, 직접 그린 팬아트): 네모 머리 + 기둥 몸통, 다리 없이 꿈틀
CREEPER = [".GlGGgG.", ".kkGlkk.", ".kkGGkk.", ".GgkkGl.", ".GkkkkG.", ".gkGGkG.",
           "..GlgG..", "..gGGl..", "..GGgG..", "..lGGg..", "..GgGG..", "..gGGg.."]
CREEPER_PAL = {"G": "#4fa83a", "g": "#3b8a2b", "l": "#7cc85e", "k": "#151515"}

# ── 레이아웃 / 타이밍 ─────────────────────────────────────────
CELL = 16
MARGIN = 16
SKY = 64            # 점프 + 카운터 공간
S = 2               # 캐릭터 픽셀 크기
CHAR_H = 12 * S
INTRO = 2.2         # 블록이 다 쌓이는 시간 (그 다음 광부 리스폰)
SPAWN_PAUSE = 0.35  # 리스폰 후 잠깐 멈춤
HOP = 0.16          # 한 칸 점프 기본 시간
HOP_PER_COL = 0.05  # 빈 칸 하나당 추가 시간
LAND = 0.06         # 착지 후 잠깐 멈춤
MINE = 0.5          # 광석 캐는 시간
BRIDGE_GAP = 3      # 빈 칸이 이만큼 이상 이어지면 점프 대신 다리를 놓음
PLACE = 0.08        # 판자 놓는 시간
WALK = 0.13         # 판자 위 한 칸 걷는 시간
PLANK_LIFE = 0.9    # 크리퍼가 안 지나가는 판자가 사라지기까지
PLANK_AFTER = 0.25  # 크리퍼가 지나간 뒤 판자가 사라지기까지
OUTRO = 1.2
CREEPER_SPAWN = 0.9 # 광부 리스폰 몇 초 뒤 크리퍼 스폰
CHASE_GAP = 2       # 광부와 최소 몇 칸 떨어져 있는지
DEATH = 3.2         # 펑 이후 광부 사망 + You Died! 화면 시간
FUSE = 1.3          # 마지막에 깜빡이며 부푸는 시간
BLAST = 2.3         # 폭발 반경 (칸)


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
            run = 1  # 같은 색 가로 연속 픽셀은 하나로 합침
            while x + run < len(row) and row[x + run] == ch:
                run += 1
            out.append(f'<rect x="{x*scale:g}" y="{y*scale:g}" width="{run*scale:g}" '
                       f'height="{scale:g}" fill="{pal[ch]}"/>')
            x += run
    return "".join(out)


def pct(t, total):
    return f"{max(0.0, min(100.0, t / total * 100)):.3f}%"


def plan_route(cols, grid_top, width, weeks):
    """광부 경로 [(시간, x, y, 땅위?)], 광석 캐는 시각 {(c, r): t},
    판자 [(c, r, t)], 크리퍼가 멈출 키 인덱스, 사이클 길이."""
    stand = lambda r: grid_top + r * CELL - CHAR_H
    key, mined, planks = [], {}, []
    first = min(cols)
    px, py = MARGIN + first * CELL, stand(min(r for r, _ in cols[first]))
    key += [(0, px, py, True), (INTRO, px, py, True)]   # 첫 블록 위에 리스폰
    t = INTRO + SPAWN_PAUSE
    key.append((t, px, py, True))

    def hop(t, x0, y0, x1, y1, ncols):
        dur = HOP + HOP_PER_COL * max(0, ncols - 1)
        h = 10 + 4 * ncols + max(0, y0 - y1) * 0.6
        h = min(h, max(4.0, (y0 + y1) / 2 - 2))   # 화면 위로 안 나가게
        for i in range(1, 7):
            u = i / 6
            key.append((t + dur * u, x0 + (x1 - x0) * u,
                        y0 + (y1 - y0) * u - 4 * h * u * (1 - u), i == 6))
        return t + dur

    def bridge(t, px, py, cols_to_fill):
        # 서 있던 높이 그대로 빈 칸마다 판자를 깔고 걸어감
        row = round((py + CHAR_H - grid_top) / CELL)
        for bc in cols_to_fill:
            t += PLACE
            planks.append((bc, row, t))
            key.append((t, px, py, True))
            px = MARGIN + bc * CELL
            t += WALK
            key.append((t, px, py, True))
        return t, px

    prev_c = None
    for c in sorted(cols):
        rows = sorted(cols[c])                    # 위쪽 블록부터
        x, y = MARGIN + c * CELL, stand(rows[0][0])
        if prev_c is not None:
            if c - prev_c - 1 >= BRIDGE_GAP:
                t, px = bridge(t, px, py, range(prev_c + 1, c))
                prev_c = c - 1
            t = hop(t, px, py, x, y, c - prev_c)
            t += LAND
            key.append((t, x, y, True))
        ores = [r for r, lvl in rows if lvl in ORES]
        if ores:
            for r in ores:
                mined[(c, r)] = t + 0.15
            t += MINE
            key.append((t, x, y, True))
            if rows[0][1] in ORES:                # 발밑 광석을 캤으면
                remain = [r for r, lvl in rows if lvl not in ORES]
                if remain:                        # 아래 블록으로 떨어지거나
                    y = stand(remain[0])
                    t += 0.12
                    key.append((t, x, y, True))
                else:                             # 남은 게 없으면 발밑에 판자를 깖
                    planks.append((c, rows[0][0], t - MINE + 0.3))
        px, py, prev_c = x, y, c

    # 끝: 맵 오른쪽 끝까지 다리를 깔고 감. 더는 갈 곳이 없음
    if prev_c < weeks - 1:
        t, px = bridge(t, px, py, range(prev_c + 1, weeks))
    t += 0.15
    key.append((t, px, py, True))
    # 크리퍼는 광부 바로 한 칸 뒤까지 따라옴
    behind = [i for i, k in enumerate(key) if k[3] and k[1] <= px - CELL + 0.1]
    stop = behind[-1] if behind else 0
    return key, mined, planks, stop, t


def chase_route(key, upto):
    """크리퍼 경로: 광부 경로를 따라가되, 광부가 다음 착지점보다
    CHASE_GAP칸 이상 앞서 있을 때만 출발한다 (광부가 멈추면 같이 기다림)."""
    def miner_x(tau):
        if tau <= key[0][0]:
            return key[0][1]
        for (t0, x0, *_), (t1, x1, *_) in zip(key, key[1:]):
            if t0 <= tau <= t1:
                return x0 + (x1 - x0) * ((tau - t0) / (t1 - t0) if t1 > t0 else 1)
        return key[-1][1]

    def wait_until(tau, need):
        if key[-1][1] < need:
            return tau
        while miner_x(tau) < need:
            tau += 0.02
        return tau

    x0 = key[0][1]
    spawn = wait_until(INTRO + CREEPER_SPAWN, x0 + CHASE_GAP * CELL)
    out, d = [(0, x0, key[0][2])], spawn - INTRO
    for i, (t, x, y, ground) in enumerate(key[:upto + 1]):
        tc = t + d
        out.append((tc, x, y))
        if ground and i < upto and key[i + 1][1] != x:
            j = next(k for k in range(i + 1, len(key)) if key[k][3])
            go = wait_until(tc, key[j][1] + CHASE_GAP * CELL)
            if go > tc:
                out.append((go, x, y))
                d += go - tc
    return out, spawn


def time_at_x(route, x):
    for t, rx, _ in route:
        if rx >= x:
            return t
    return None


def puff_svg(css, cx, cy, t0, T, name, colors, n=8, spread=18):
    """리스폰/스폰 반짝이: 작은 조각들이 위로 퍼지며 사라짐."""
    out = []
    for i in range(n):
        ang = -math.pi * (i + 0.5) / n
        dx, dy = math.cos(ang) * spread, math.sin(ang) * spread - 4
        k = f"{name}{i}"
        css.append(f"@keyframes {k}{{0%,{pct(t0, T)}{{opacity:0;transform:translate(0,0)}}"
                   f"{pct(t0 + 0.03, T)}{{opacity:1}}"
                   f"{pct(t0 + 0.6, T)},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px)}}}}"
                   f".{k}{{opacity:0;animation:{k} {T:.2f}s infinite}}")
        out.append(f'<rect x="{cx - 2:.0f}" y="{cy - 2:.0f}" width="4" height="4" '
                   f'fill="{colors[i % len(colors)]}" class="{k}"/>')
    return "".join(out)


DEATH_CSS = """
.big{font:700 30px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.mid{font:600 13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.btn{animation:btn 1.2s steps(1) infinite}
@keyframes btn{0%{fill:#6f6f6f}50%{fill:#8a8fd0}}
"""


def death_screen(width, height, grid_top, score, hint=""):
    cx = width / 2
    return (
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#b00000" fill-opacity=".45"/>'
        f'<text x="{cx + 2}" y="{grid_top + 14}" text-anchor="middle" class="big" fill="#3a0000">You Died!</text>'
        f'<text x="{cx}" y="{grid_top + 12}" text-anchor="middle" class="big" fill="#ffffff">You Died!</text>'
        f'<text x="{cx}" y="{grid_top + 38}" text-anchor="middle" class="mid" fill="#ffffff">'
        f'Score: <tspan fill="#ffd84a">{score}</tspan></text>'
        f'<rect x="{cx - 80}" y="{grid_top + 54}" width="160" height="26" fill="#1a1a1a"/>'
        f'<rect x="{cx - 78}" y="{grid_top + 56}" width="156" height="22" class="btn"/>'
        f'<text x="{cx}" y="{grid_top + 71}" text-anchor="middle" class="mid" fill="#ffffff">Respawn</text>'
        + (f'<text x="{cx}" y="{grid_top + 100}" text-anchor="middle" class="t" fill="#ffffff">{hint}</text>'
           if hint else "")
    )


def build_dead_svg(cells, user):
    """커밋이 하나도 없을 때: 사망 화면 패러디."""
    weeks = max(c for c, _ in cells) + 1 if cells else 53
    width = weeks * CELL + MARGIN * 2
    grid_top = SKY
    height = grid_top + 7 * CELL + 36
    grid = "".join(f'<rect x="{MARGIN + c*CELL + 1}" y="{grid_top + r*CELL + 1}" width="{CELL-2}" '
                   f'height="{CELL-2}" fill="#8b949e" fill-opacity=".18"/>'
                   for (c, r) in cells)
    cx = width / 2
    style = """
.t{font:600 11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.big{font:700 30px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.mid{font:600 13px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
.red{animation:red 3s ease-in-out infinite alternate}
@keyframes red{0%{fill-opacity:.38}100%{fill-opacity:.5}}
.btn{animation:btn 1.2s steps(1) infinite}
@keyframes btn{0%{fill:#6f6f6f}50%{fill:#8a8fd0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" shape-rendering="crispEdges"><style>{style}</style>'
        f'{grid}'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#b00000" class="red"/>'
        f'<text x="{cx + 2}" y="{grid_top + 14}" text-anchor="middle" class="big" fill="#3a0000">You Died!</text>'
        f'<text x="{cx}" y="{grid_top + 12}" text-anchor="middle" class="big" fill="#ffffff">You Died!</text>'
        f'<text x="{cx}" y="{grid_top + 38}" text-anchor="middle" class="mid" fill="#ffffff">'
        f'Score: <tspan fill="#ffd84a">0</tspan></text>'
        f'<rect x="{cx - 80}" y="{grid_top + 54}" width="160" height="26" fill="#1a1a1a"/>'
        f'<rect x="{cx - 78}" y="{grid_top + 56}" width="156" height="22" class="btn"/>'
        f'<text x="{cx}" y="{grid_top + 71}" text-anchor="middle" class="mid" fill="#ffffff">Respawn</text>'
        f'<text x="{cx}" y="{grid_top + 100}" text-anchor="middle" class="t" fill="#ffffff">'
        f'make a commit to respawn</text>'
        f'<text x="{MARGIN}" y="{height - 12}" class="t" fill="#ffffff">⛏ {user} · 0 contributions</text>'
        f'</svg>'
    )


def build_svg(cells, total, user):
    filled = {k: v for k, v in cells.items() if v > 0}
    cols = {}
    for (c, r), lvl in filled.items():
        cols.setdefault(c, []).append((r, lvl))
    weeks = max(c for c, _ in cells) + 1
    width = weeks * CELL + MARGIN * 2
    grid_top = SKY
    height = grid_top + 7 * CELL + 36

    key, mined, planks, stop, t_end = plan_route(cols, grid_top, width, weeks)
    fx, fy = key[-1][1], key[-1][2]
    if fx - key[0][1] < 2 * CELL - 0.1:
        # 길이 너무 짧으면(첫 블록이 맨 끝 근처) 크리퍼가 바로 옆 판자 위에 스폰
        cs = INTRO + CREEPER_SPAWN
        chase = [(0, fx - CELL, fy), (cs + 0.3, fx - CELL, fy)]
        planks.append((weeks - 2, round((fy + CHAR_H - grid_top) / CELL), cs - 0.1))
    else:
        chase, cs = chase_route(key, stop)
    te, ex, ey = chase[-1]
    ta = max(te, t_end) + 0.1                 # 둘 다 도착 = 대치 시작
    f0 = ta + 0.3                             # 크리퍼 깜빡이기 시작

    # 결말: 모은 광석으로 검을 만들 수 있으면 승리, 아니면 사망
    got = {"gold": 0, "diamond": 0}
    for (c, r) in mined:
        got[ORES[filled[(c, r)]]] += 1
    weapon = "diamond" if got["diamond"] >= 2 else "gold" if got["gold"] >= 2 else None
    if weapon:
        craft = f0 + 0.35                     # 광석이 머리 위로 모임
        h1, h2 = craft + 0.75, craft + 1.05   # 두 번 베기
        boom = None
        T = h2 + 3.0
    else:
        boom = f0 + FUSE
        T = boom + DEATH
    bx, by = ex + 4 * S, ey + CHAR_H - 4      # 폭발 중심 (크리퍼 몸 아래쪽)
    end = boom if boom else T - 0.3           # 남은 판자가 사라지는 시각

    defs = []
    border = ('<rect width="8" height="8" fill="none" stroke="#000" stroke-opacity=".2" '
              'stroke-width=".25"/>')
    for lvl, tex in BLOCKS.items():
        defs.append(f'<symbol id="b{lvl}" viewBox="0 0 8 8">{pixel_rects(tex, PALETTE)}{border}</symbol>')
    defs.append(f'<symbol id="plank" viewBox="0 0 8 8">{pixel_rects(PLANK, PALETTE)}{border}</symbol>')
    for name, rows in ITEMS.items():
        defs.append(f'<symbol id="i-{name}" viewBox="0 0 5 5">{pixel_rects(rows, PALETTE)}</symbol>')

    counter = {"gold": (width - MARGIN - 110, 14), "diamond": (width - MARGIN - 52, 14)}
    css, blocks, items = [], [], []

    for (c, r), lvl in sorted(filled.items()):
        x, y = MARGIN + c * CELL, grid_top + r * CELL
        drop = c * 0.03 + r * 0.02
        use = (f'<use href="#b{lvl}" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
               f'class="drop" style="animation-delay:{drop:.2f}s"/>')
        if (c, r) in mined:
            tb = mined[(c, r)]
            n = f"m{c}_{r}"
            css.append(f"@keyframes {n}{{0%,{pct(tb, T)}{{opacity:1;transform:scale(1)}}"
                       f"{pct(tb + 0.08, T)}{{transform:scale(1.15)}}"
                       f"{pct(tb + 0.25, T)},99.9%{{opacity:0;transform:scale(.2)}}100%{{opacity:1}}}}"
                       f".{n}{{animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
            blocks.append(f'<g class="{n}">{use}</g>')
            kind = ORES[lvl]
            cx, cy = counter[kind]
            dx, dy = cx - (x + 3), cy - (y + 3)
            fa, fb = tb + 0.2, tb + 0.85
            css.append(f"@keyframes f{n}{{0%,{pct(fa - 0.01, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(fa, T)}{{opacity:1;transform:translate(0,-6px)}}"
                       f"{pct(fb, T)}{{opacity:1;transform:translate({dx:.0f}px,{dy:.0f}px)}}"
                       f"{pct(fb + 0.05, T)},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px)}}}}"
                       f".f{n}{{opacity:0;animation:f{n} {T:.2f}s infinite}}")
            items.append(f'<use href="#i-{kind}" x="{x + 3}" y="{y + 3}" width="10" height="10" class="f{n}"/>')
            continue
        vx, vy = x + CELL / 2 - bx, y + CELL / 2 - by
        dist = math.hypot(vx, vy)
        if boom and dist <= BLAST * CELL:
            # 폭발 반경 안의 블록은 날아감
            n = f"x{c}_{r}"
            k = 22 / max(dist, 1)
            css.append(f"@keyframes {n}{{0%,{pct(boom, T)}{{opacity:1;transform:translate(0,0) rotate(0)}}"
                       f"{pct(boom + 0.5, T)},99.9%{{opacity:0;transform:translate({vx*k:.0f}px,{vy*k - 14:.0f}px) rotate(40deg)}}"
                       f"100%{{opacity:1;transform:none}}}}"
                       f".{n}{{animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
            blocks.append(f'<g class="{n}">{use}</g>')
        else:
            blocks.append(use)

    # 판자: 놓일 때 톡 생기고, 크리퍼가 지나간 뒤(또는 폭발 때) 떨어지며 사라짐
    for bc, br, tp in planks:
        n = f"p{bc}_{br}"
        x, y = MARGIN + bc * CELL, grid_top + br * CELL
        tpass = time_at_x(chase, x + CELL)
        if tpass is not None:
            gone = max(tpass, tp) + PLANK_AFTER
        else:
            gone = end                        # 끝에서 서 있는 판자는 결말과 함께
        css.append(f"@keyframes {n}{{0%,{pct(tp - 0.06, T)}{{opacity:0;transform:scale(.3)}}"
                   f"{pct(tp, T)}{{opacity:1;transform:scale(1)}}"
                   f"{pct(gone, T)}{{opacity:1;transform:translateY(0)}}"
                   f"{pct(gone + 0.3, T)},100%{{opacity:0;transform:translateY(10px)}}}}"
                   f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
        blocks.append(f'<use href="#plank" x="{x}" y="{y}" width="{CELL}" height="{CELL}" class="{n}"/>')

    # 카운터 숫자: 개수별 텍스트를 시간 구간마다 보이게
    hud = []
    for kind, (cx, cy) in counter.items():
        hud.append(f'<use href="#i-{kind}" x="{cx}" y="{cy}" width="12" height="12"/>')
        times = sorted(t + 0.85 for (c, r), t in mined.items() if ORES[filled[(c, r)]] == kind)
        edges = [0.0] + times + [T]
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
            hud.append(f'<text x="{cx + 16}" y="{cy + 11}" class="t {n}">×{k}</text>')

    # 이동 경로 키프레임
    for name, route in (("path", key), ("chase", chase)):
        kf = "".join(f"{pct(k[0], T)}{{transform:translate({k[1]:.1f}px,{k[2]:.1f}px)}}" for k in route)
        css.append(f"@keyframes {name}{{{kf}100%{{transform:translate({route[-1][1]:.1f}px,{route[-1][2]:.1f}px)}}}}")

    # 리스폰 / 스폰
    css.append(f"@keyframes mspawn{{0%,{pct(INTRO - 0.01, T)}{{opacity:0}}{pct(INTRO + 0.2, T)},100%{{opacity:1}}}}")
    css.append(f"@keyframes cspawn{{0%,{pct(cs - 0.01, T)}{{opacity:0}}{pct(cs + 0.25, T)},100%{{opacity:1}}}}")
    sx, sy = key[0][1] + 8, key[0][2] + CHAR_H - 4
    spawn_fx = (puff_svg(css, sx, sy, INTRO, T, "ms", ["#ffffff", "#fff3a0", "#cfe8ff"])
                + puff_svg(css, sx, sy, cs, T, "cs", ["#7cc85e", "#4fa83a", "#cccccc"]))

    css.append(f"@keyframes mturn{{0%,{pct(t_end, T)}{{transform:scaleX(1)}}"
               f"{pct(t_end + 0.01, T)},99.9%{{transform:translateX({8*S}px) scaleX(-1)}}100%{{transform:scaleX(1)}}}}"
               f".mturn{{animation:mturn {T:.2f}s infinite steps(1);transform-box:view-box;transform-origin:0 0}}")
    tool = f'<g class="tool1">{pixel_rects(PICKAXE, MINER_PAL, S)}</g>'
    extra = ""
    if weapon:
        # 검 제작: 픽셀 곡괭이가 사라지고 검이 생김
        css.append(f"@keyframes tool1{{0%,{pct(craft + 0.5, T)}{{opacity:1}}{pct(craft + 0.51, T)},99.9%{{opacity:0}}100%{{opacity:1}}}}"
                   f".tool1{{animation:tool1 {T:.2f}s infinite steps(1)}}")
        css.append(f"@keyframes tool2{{0%,{pct(craft + 0.5, T)}{{opacity:0}}{pct(craft + 0.51, T)},99.9%{{opacity:1}}100%{{opacity:0}}}}"
                   f".tool2{{opacity:0;animation:tool2 {T:.2f}s infinite steps(1)}}")
        tool += (f'<g class="tool2" transform="translate({2*S} {-1*S})">'
                 f'{pixel_rects(SWORD, SWORD_PAL[weapon], S)}</g>')
        # 승리 후 폴짝
        css.append(f"@keyframes mwin{{0%,{pct(h2 + 1.3, T)}{{transform:translateY(0)}}"
                   f"{pct(h2 + 1.5, T)}{{transform:translateY(-10px)}}{pct(h2 + 1.7, T)},100%{{transform:translateY(0)}}}}"
                   f".mwin{{animation:mwin {T:.2f}s infinite}}")
        wrap_open, wrap_close = '<g class="mwin">', '</g>'
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
        red = {ch: "#ff2a2a" for ch in MINER_PAL}
        extra = f'<g class="mred">{pixel_rects(MINER_BODY + MINER_LEGS_A, red, S)}</g>'
        wrap_open, wrap_close = '<g class="mdie"><g class="mshake">', '</g></g>'
        spawn_fx += puff_svg(css, fx + 8, fy + CHAR_H - 6, boom + 0.9, T, "md",
                             ["#ffffff", "#d0d0d0", "#a0a0a0"], n=10, spread=20)
    miner = (
        f'<g class="path"><g class="mspawn">{wrap_open}<g class="mturn">'
        f'{pixel_rects(MINER_BODY, MINER_PAL, S)}'
        f'<g class="legA" transform="translate(0 {10*S})">{pixel_rects(MINER_LEGS_A, MINER_PAL, S)}</g>'
        f'<g class="legB" transform="translate(0 {10*S})">{pixel_rects(MINER_LEGS_B, MINER_PAL, S)}</g>'
        f'<g transform="translate({7*S} {3*S})"><g class="swing">{tool}</g></g>'
        f'{extra}</g>{wrap_close}</g></g>'
    )

    # 크리퍼: 광부 바로 뒤에서 하얗게 깜빡이며 부풂
    if boom:
        css.append(f"@keyframes fuse{{0%,{pct(f0, T)}{{transform:scale(1);opacity:1}}"
                   f"{pct(f0 + 0.3, T)}{{transform:scale(1.06)}}{pct(f0 + 0.55, T)}{{transform:scale(1)}}"
                   f"{pct(f0 + 0.85, T)}{{transform:scale(1.12)}}{pct(f0 + 1.0, T)}{{transform:scale(1.04)}}"
                   f"{pct(boom, T)}{{transform:scale(1.3);opacity:1}}"
                   f"{pct(boom + 0.01, T)},99.9%{{opacity:0}}100%{{opacity:1;transform:scale(1)}}}}")
        blinks = [(f0 + 0.1, f0 + 0.3), (f0 + 0.55, f0 + 0.75), (f0 + 0.95, f0 + 1.1), (f0 + 1.18, boom)]
    else:
        # 부풀다가 첫 번째로 베이는 순간 멈춤 -> 넉백 -> 두 번째에 쓰러짐
        css.append(f"@keyframes fuse{{0%,{pct(f0, T)}{{transform:translate(0,0) scale(1);opacity:1}}"
                   f"{pct(f0 + 0.3, T)}{{transform:scale(1.06)}}{pct(f0 + 0.55, T)}{{transform:scale(1)}}"
                   f"{pct(f0 + 0.85, T)}{{transform:scale(1.1)}}"
                   f"{pct(h1, T)}{{transform:translate(0,0) scale(1.1)}}"
                   f"{pct(h1 + 0.08, T)}{{transform:translate(-6px,-3px) scale(1)}}"
                   f"{pct(h2, T)}{{transform:translate(-5px,0) rotate(0)}}"
                   f"{pct(h2 + 0.1, T)}{{transform:translate(-11px,-3px) rotate(0)}}"
                   f"{pct(h2 + 0.45, T)}{{transform:translate(-11px,0) rotate(-90deg);opacity:1}}"
                   f"{pct(h2 + 0.9, T)},99.9%{{transform:translate(-11px,0) rotate(-90deg);opacity:0}}"
                   f"100%{{transform:none;opacity:1}}}}")
        blinks = [(f0 + 0.1, f0 + 0.3), (f0 + 0.55, f0 + 0.75)]
        css.append(f"@keyframes cred{{0%{{opacity:0}}{pct(h1, T)}{{opacity:.65}}{pct(h1 + 0.15, T)}{{opacity:0}}"
                   f"{pct(h2, T)}{{opacity:.65}}{pct(h2 + 0.9, T)},100%{{opacity:0}}}}"
                   f".cred{{opacity:0;animation:cred {T:.2f}s infinite steps(1)}}")
    kf = "0%{opacity:0}" + "".join(f"{pct(a, T)}{{opacity:.85}}{pct(b, T)}{{opacity:0}}" for a, b in blinks)
    css.append(f"@keyframes flash{{{kf}100%{{opacity:0}}}}")
    white = {ch: "#ffffff" for ch in CREEPER_PAL}
    creeper = (
        f'<g class="chase"><g class="cspawn"><g class="fuse"><g class="crawl">'
        f'{pixel_rects(CREEPER, CREEPER_PAL, S)}'
        f'<g class="flash">{pixel_rects(CREEPER, white, S)}</g>'
        + (f'<g class="cred">{pixel_rects(CREEPER, {ch: "#ff2a2a" for ch in CREEPER_PAL}, S)}</g>' if not boom else "")
        + f'</g></g></g></g>'
    )

    puffs = []
    death = ""
    if weapon:
        # 모은 광석 2개가 카운터에서 머리 위로 날아와 검이 됨
        mx, my = fx + 8, fy - 10
        for i in range(2):
            cx, cy = counter[weapon]
            n = f"cr{i}"
            t1 = craft + i * 0.1
            css.append(f"@keyframes {n}{{0%,{pct(t1, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(t1 + 0.02, T)}{{opacity:1}}"
                       f"{pct(t1 + 0.4, T)}{{opacity:1;transform:translate({mx - cx - 6:.0f}px,{my - cy - 6:.0f}px)}}"
                       f"{pct(t1 + 0.45, T)},100%{{opacity:0;transform:translate({mx - cx - 6:.0f}px,{my - cy - 6:.0f}px)}}}}"
                       f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite}}")
            puffs.append(f'<use href="#i-{weapon}" x="{cx}" y="{cy}" width="12" height="12" class="{n}"/>')
        puffs.append(puff_svg(css, mx, my, craft + 0.5, T, "cf", ["#ffffff", "#fff3a0", "#cfe8ff"], n=8, spread=14))
        # 크리퍼가 연기가 되고 경험치 구슬이 광부에게
        cx0, cy0 = ex - 11 + 8, ey + CHAR_H - 8
        puffs.append(puff_svg(css, cx0, cy0, h2 + 0.85, T, "cd", ["#ffffff", "#d0d0d0", "#a0a0a0"], n=10, spread=20))
        for i in range(6):
            n = f"xp{i}"
            t1 = h2 + 1.0 + i * 0.08
            ox, oy = (i % 3 - 1) * 6, -(i // 3) * 6 - 4
            css.append(f"@keyframes {n}{{0%,{pct(t1, T)}{{opacity:0;transform:translate(0,0)}}"
                       f"{pct(t1 + 0.05, T)}{{opacity:1;transform:translate({ox}px,{oy - 8}px)}}"
                       f"{pct(t1 + 0.5, T)}{{opacity:1;transform:translate({fx + 8 - cx0:.0f}px,{fy + 10 - cy0:.0f}px)}}"
                       f"{pct(t1 + 0.55, T)},100%{{opacity:0}}}}"
                       f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite}}")
            puffs.append(f'<rect x="{cx0 - 3:.0f}" y="{cy0 - 3:.0f}" width="6" height="6" '
                         f'fill="{"#b5f23c" if i % 2 else "#e6ff5a"}" stroke="#4a7a10" stroke-width="1" class="{n}"/>')
    # 폭발: 섬광 + 연기 조각이 사방으로 (사망 엔딩만)
    colors = ["#ff9a2e", "#6e6e6e", "#ffd25a", "#8f8f8f", "#ff6a2b", "#555555"]
    for i in range(18 if boom else 0):
        ang = 2 * math.pi * i / 18 + (i % 3) * 0.2
        dist = 34 + (i * 7) % 28
        size = 8 + (i * 5) % 8
        dx, dy = math.cos(ang) * dist, math.sin(ang) * dist * 0.8 - 6
        n = f"pf{i}"
        css.append(f"@keyframes {n}{{0%,{pct(boom, T)}{{opacity:0;transform:translate(0,0) scale(.4)}}"
                   f"{pct(boom + 0.03, T)}{{opacity:1}}"
                   f"{pct(boom + 0.7, T)},100%{{opacity:0;transform:translate({dx:.0f}px,{dy:.0f}px) scale(1.6)}}}}"
                   f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
        puffs.append(f'<rect x="{bx - size/2:.0f}" y="{by - size/2:.0f}" width="{size}" height="{size}" '
                     f'fill="{colors[i % len(colors)]}" class="{n}"/>')
    if boom:
        css.append(f"@keyframes core{{0%,{pct(boom, T)}{{opacity:0;transform:scale(.3)}}"
                   f"{pct(boom + 0.05, T)}{{opacity:.95;transform:scale(1.2)}}"
                   f"{pct(boom + 0.35, T)},100%{{opacity:0;transform:scale(1.8)}}}}")
        puffs.append(f'<rect x="{bx - 14:.0f}" y="{by - 14:.0f}" width="28" height="28" fill="#ffc04a" class="core"/>')
        # 사망 화면: 펑 직후 떴다가, 다음 바퀴에서 리스폰
        d0 = boom + 1.1
        css.append(f"@keyframes dov{{0%,{pct(d0, T)}{{opacity:0}}{pct(d0 + 0.35, T)},{pct(T - 0.3, T)}{{opacity:1}}100%{{opacity:0}}}}"
                   f".dov{{opacity:0;animation:dov {T:.2f}s infinite}}")
        death = f'<g class="dov">{death_screen(width, height, grid_top, total or str(len(mined)))}</g>' 

    ly = grid_top + 7 * CELL + 14
    lx = width - MARGIN - 4 * 14 - 34
    legend = [f'<text x="{lx - 6}" y="{ly + 10}" text-anchor="end" class="t">Less</text>']
    legend += [f'<use href="#b{i}" x="{lx + (i-1)*14}" y="{ly}" width="12" height="12"/>' for i in range(1, 5)]
    legend.append(f'<text x="{lx + 4*14 + 2}" y="{ly + 10}" class="t">More</text>')
    label = f"⛏ {user}" + (f" · {total} contributions" if total else "")
    legend.append(f'<text x="{MARGIN}" y="{ly + 10}" class="t">{label}</text>')

    style = f"""
.t{{font:600 11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#8b949e}}
.drop{{animation:drop {T:.2f}s infinite both;transform-box:fill-box}}
@keyframes drop{{0%{{transform:translateY(-70px);opacity:0}}{pct(0.35, T)}{{transform:translateY(0);opacity:1}}
{pct(0.43, T)}{{transform:translateY(-3px)}}{pct(0.5, T)}{{transform:translateY(0)}}{pct(T - 0.5, T)}{{opacity:1}}100%{{transform:translateY(0);opacity:0}}}}
.path{{animation:path {T:.2f}s linear infinite}}
.chase{{animation:chase {T:.2f}s linear infinite}}
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
.core{{opacity:0;animation:core {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}
{DEATH_CSS}
{"".join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.path,.chase{{display:none}}}}
"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" shape-rendering="crispEdges">'
        f'<style>{style}</style><defs>{"".join(defs)}</defs>'
        f'{"".join(blocks)}{"".join(items)}{creeper}{miner}{spawn_fx}{"".join(puffs)}'
        f'{"".join(hud)}{"".join(legend)}{death}</svg>'
    ), T


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "haeunjeon0410"
    out = sys.argv[2] if len(sys.argv) > 2 else "minecraft-contrib.svg"
    cells, total = fetch_levels(user)
    if not cells:
        sys.exit("잔디 데이터를 못 가져왔어요 (아이디 확인)")
    if any(cells.values()):
        svg, T = build_svg(cells, total, user)
        info = f"{sum(1 for v in cells.values() if v)} blocks, total={total}, cycle={T:.1f}s"
    else:
        svg, info = build_dead_svg(cells, user), "no contributions -> You Died!"
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{out}: {info}")


if __name__ == "__main__":
    main()
