"""GitHub 잔디 = 풀숲. 트레이너가 걸어가다 진한 풀숲에서 야생 포켓몬과 조우해서 잡는다 (미리보기).

격자/색/이동 유틸은 generate_grid.py 재사용.
usage: python generate_poke.py <github_user> [output.svg]
"""
import sys

from poke_icons import EMOLGA_PNG, ICONS

from generate_grid import (BLOCK, CELL, DARK, LIGHT, MARGIN, NOISE, center, dist_at, face_css,
                           fetch_levels, pct, pixel_rects, pos_at, puff, route_keyframes)

TOP = 40
S = 1.5
SPAWN = 0.5
STEP = 0.11

# 트레이너 (8x12, 직접 그림)
from ash_sprite import ASH as TRAINER, ASH_LEGS_A as LEGS_A, ASH_LEGS_B as LEGS_B, ASH_PAL as TRAINER_PAL
TS = 1.0             # 지우 픽셀 크기 (14x18)


# 볼 (13x13 손 도트). 몬스터볼 / 하이퍼볼(마지막 에몽가)
_BALL_BOTTOM = ["kRRRkkkkkRrrk", "kkkkkWWWkkkkk", "kWWWkkkkkWggk", "kWWWWWWWWWWgk", ".kWWWWWWWWgk.",
                ".kgWWWWWWggk.", "..kkgggggkk..", "....kkkkk...."]
BALLS = {
    "poke": (["....kkkkk....", "..kkRRRRRkk..", ".kRHHRRRRRRk.", ".kRHRRRRRRrk.", "kRRRRRRRRRRrk"] + _BALL_BOTTOM,
             {"k": "#1e1e1e", "R": "#e3342f", "r": "#a91f1f", "H": "#ffffff", "W": "#ffffff", "g": "#c9ccd1"}),
    "ultra": (["....kkkkk....", "..kkYRRRYkk..", ".kYYRHRRRYYk.", ".kYYHRRRRYYk.", "kYYRRRRRRRYYk"] + _BALL_BOTTOM,
              {"k": "#1e1e1e", "R": "#3a3a3a", "r": "#222222", "H": "#9a9a9a", "Y": "#f5c518",
               "W": "#ffffff", "g": "#c9ccd1"}),
}
MONS = ICONS        # 게임 아이콘 도트 (왼쪽을 봄)
MS = 0.8            # 포켓몬 픽셀 크기
FINAL = "에몽가"     # 마지막 = 내 프로필 사진과 같은 에몽가
RUSTLE = 0.45       # 풀숲 부스럭
SURPRISE = 0.3      # "!"
APPEAR = 0.6        # 등장
THROW = 0.4
WOBBLE = 0.7
CAUGHT = 0.5
MAX_MONS = 6


def outlined(rows, pal, scale):
    """진한 잔디 위에서도 보이게 어두운 테두리를 두른 스프라이트."""
    dark = {ch: "#1b1f23" for ch in pal}
    edge = "".join(f'<g transform="translate({ox} {oy})" opacity=".6">{pixel_rects(rows, dark, scale)}</g>'
                   for ox, oy in ((scale, 0), (-scale, 0), (0, scale), (0, -scale)))
    return edge + pixel_rects(rows, pal, scale)


def pick_encounters(cells):
    """상하좌우로 붙은 진한 칸 덩어리 = 풀숲 하나 = 포켓몬 한 마리.
    많으면 큰 풀숲부터 MAX_MONS개. 각 풀숲에서 처음 닿는(가장 왼쪽) 칸에서 조우."""
    lv_deep = 4 if any(v == 4 for v in cells.values()) else 3
    deep = {cr for cr, v in cells.items() if v == lv_deep}
    seen, clusters = set(), []
    for start in sorted(deep):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            c, r = stack.pop()
            comp.append((c, r))
            for nb in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
                if nb in deep and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        clusters.append(sorted(comp))
    if not clusters:
        return []
    latest = max(clusters, key=lambda comp: comp[-1])
    rest = sorted((c for c in clusters if c is not latest), key=len, reverse=True)[:MAX_MONS - 1]
    chosen = sorted(rest, key=lambda comp: comp[0]) + [latest]
    return [comp[0] for comp in chosen]     # 마지막 = 가장 최근 풀숲 (에몽가)


def build_svg(cells, total, user):
    weeks = max(c for c, _ in cells) + 1
    width = weeks * CELL + MARGIN * 2
    height = TOP + 7 * CELL + 30
    css, fx = [], []

    # 풀숲 칸 심볼 (원본 색, 라이트/다크)
    defs, light_css, dark_css = [], [], []
    for kind, (brows, bpal) in BALLS.items():
        defs.append(f'<symbol id="ball-{kind}" viewBox="0 0 13 13">{pixel_rects(brows, bpal)}</symbol>')
    for lv in range(5):
        rects = "".join(f'<rect x="{x}" y="{y}" width="1" height="1" class="c{lv}{ch}"/>'
                        for y, row in enumerate(NOISE) for x, ch in enumerate(row))
        defs.append(f'<symbol id="g{lv}" viewBox="0 0 8 8">{rects}'
                    f'<rect width="8" height="8" fill="none" stroke="#1b1f23" stroke-opacity=".08" stroke-width=".3"/></symbol>')
        for k in range(3):
            light_css.append(f".c{lv}{k}{{fill:{LIGHT[lv][k]}}}")
            dark_css.append(f".c{lv}{k}{{fill:{DARK[lv][k]}}}")

    # 경로: (0,3)에서 출발 -> 조우 칸들 -> 오른쪽 끝
    enc = pick_encounters(cells)
    pool = [m for m in MONS if m != "에몽가"]
    mon_of = {e: ("에몽가" if i == len(enc) - 1 else pool[i % len(pool)]) for i, e in enumerate(enc)}
    cur, pts, stops = (0, 3), [(0, 3)], {}
    for tgt in enc + [(weeks - 1, None)]:
        tc, tr = tgt[0], cur[1] if tgt[1] is None else tgt[1]
        while cur[0] != tc:
            cur = (cur[0] + (1 if tc > cur[0] else -1), cur[1])
            pts.append(cur)
        while cur[1] != tr:
            cur = (cur[0], cur[1] + (1 if tr > cur[1] else -1))
            pts.append(cur)
        if tgt[1] is not None:
            stops[len(pts) - 1] = tgt

    # 시간표
    t = SPAWN + 0.3
    timeline = [(0, 0.0), (t, 0.0)]
    events = []                                   # (조우 칸, 시작 시각)
    rustles = {}                                  # 밟고 지나가는 진한 칸 -> 시각
    for i in range(1, len(pts)):
        t += STEP
        timeline.append((t, float(i)))
        if cells.get(pts[i], 0) >= 3:
            rustles.setdefault(pts[i], t)
        if i in stops:
            events.append((stops[i], t))
            t += RUSTLE + SURPRISE + APPEAR + THROW + WOBBLE + CAUGHT
            timeline.append((t, float(i)))
    t_end = t
    T = t_end + 1.6

    # 풀숲 칸: 부스럭(흔들림 + 잎사귀)
    grid = []
    for (c, r), lv in sorted(cells.items()):
        x, y = MARGIN + c * CELL, TOP + r * CELL
        use = f'<use href="#g{lv}" x="{x}" y="{y}" width="{BLOCK}" height="{BLOCK}"/>'
        if (c, r) in rustles:
            t0 = rustles[(c, r)]
            dur = RUSTLE if (c, r) in mon_of else 0.3
            n = f"r{c}_{r}"
            kf, tt, sgn = [f"0%,{pct(t0, T)}{{transform:translateX(0)}}"], t0, 1
            while tt < t0 + dur:
                tt += 0.05
                kf.append(f"{pct(tt, T)}{{transform:translateX({sgn * 1.5}px)}}")
                sgn = -sgn
            kf.append(f"{pct(t0 + dur + 0.01, T)},100%{{transform:translateX(0)}}")
            css.append(f"@keyframes {n}{{{''.join(kf)}}}.{n}{{animation:{n} {T:.2f}s infinite steps(1)}}")
            grid.append(f'<g class="{n}">{use}</g>')
            cx, cy = center(c, r)
            fx.append(puff(css, cx, cy - 4, t0, T, f"lf{c}_{r}", ["#2fb746", "#86dc95", "#195a2e"], n=5, spread=9))
        else:
            grid.append(use)

    # 조우 연출
    counter_x, counter_y = width - MARGIN - 40, 12
    caught_times = []
    for k, ((c, r), t0) in enumerate(events):
        name = mon_of[(c, r)]
        rows, pal = MONS[name]
        tx, ty = center(c, r)
        side = 1 if c < weeks - 1 else -1
        mx, my = tx + side * CELL, ty                 # 몬스터는 옆 칸에 나타남
        t_ex = t0 + RUSTLE                            # "!"
        t_ap = t_ex + SURPRISE                        # 등장
        t_th = t_ap + APPEAR                          # 볼 던짐
        t_in = t_th + THROW                           # 볼에 들어감
        t_ok = t_in + WOBBLE                          # 잡았다!
        t_go = t_ok + CAUGHT                          # 다음으로
        caught_times.append(t_ok + 0.5)
        sc = MS
        mw, mh = len(rows[0]) * sc, len(rows) * sc
        if name == FINAL:                         # 원본 그림을 다른 포켓몬 높이에 맞춤
            mh = sum(len(MONS[m][0]) for m in pool) / len(pool) * MS * 1.05
            mw = mh * EMOLGA_PNG[1] / EMOLGA_PNG[2]
        # "!" 말풍선
        n = f"ex{k}"
        css.append(f"@keyframes {n}{{0%,{pct(t_ex, T)}{{opacity:0}}{pct(t_ex + 0.01, T)},{pct(t_ap + 0.3, T)}{{opacity:1}}"
                   f"{pct(t_ap + 0.31, T)},100%{{opacity:0}}}}.{n}{{opacity:0;animation:{n} {T:.2f}s infinite steps(1)}}")
        bx, by = round(tx), round(ty)           # 말풍선과 "!"를 같은 기준점에서 배치 (가운데 정렬)
        # 테두리는 선 대신 픽셀 칸으로 (반 픽셀 겹침 없음). 안쪽 8x11, 느낌표 위아래 여백 2px
        fx.append(f'<g class="{n}"><rect x="{bx - 5}" y="{by - 33}" width="10" height="13" fill="#222222"/>'
                  f'<rect x="{bx - 4}" y="{by - 32}" width="8" height="11" fill="#ffffff"/>'
                  f'<rect x="{bx - 1}" y="{by - 30}" width="2" height="4" fill="#e3342f"/>'
                  f'<rect x="{bx - 1}" y="{by - 25}" width="2" height="2" fill="#e3342f"/></g>')
        # 몬스터: 풀숲에서 쏙 -> 볼에 빨려 들어감
        n = f"mon{k}"
        css.append(f"@keyframes {n}{{0%,{pct(t_ap, T)}{{opacity:0;transform:translateY(8px) scale(.6)}}"
                   f"{pct(t_ap + 0.15, T)}{{opacity:1;transform:translateY(-4px) scale(1.05)}}"
                   f"{pct(t_ap + 0.3, T)},{pct(t_in, T)}{{opacity:1;transform:translateY(0) scale(1)}}"
                   f"{pct(t_in + 0.15, T)},100%{{opacity:0;transform:translateY(0) scale(.1)}}}}"
                   f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:50% 100%}}")
        # 아이콘은 이미 테두리가 있고 왼쪽을 봄 -> 트레이너가 오른쪽에 있으면 뒤집기
        flip = f' transform="translate({mw:.1f} 0) scale(-1 1)"' if side == -1 and name != FINAL else ""
        fx.append(f'<g transform="translate({mx - mw/2:.1f} {my - mh + 5:.1f})"><g class="{n}"><g{flip}>'
                  + (f'<image href="data:image/png;base64,{EMOLGA_PNG[0]}" width="{mw:.1f}" height="{mh:.1f}"/>'
                     if name == FINAL else pixel_rects(rows, pal, sc))
                  + '</g></g></g>')
        # 볼: 던짐(포물선) -> 흔들흔들 -> 카운터로
        n = f"bl{k}"
        dx, dy = mx - tx, my - ty
        arc = "".join(f"{pct(t_th + THROW * u / 4, T)}{{opacity:1;transform:translate({dx * u / 4:.1f}px,{dy * u / 4 - 14 * (u / 4) * (1 - u / 4) * 4:.1f}px) rotate({u * 90}deg)}}"
                      for u in range(5))
        wob = "".join(f"{pct(t_in + 0.1 + j * 0.15, T)}{{transform:translate({dx:.1f}px,{dy:.1f}px) rotate({(-1) ** j * 20}deg)}}"
                      for j in range(4))
        css.append(f"@keyframes {n}{{0%,{pct(t_th - 0.01, T)}{{opacity:0;transform:translate(0,0)}}{arc}{wob}"
                   f"{pct(t_ok, T)}{{opacity:1;transform:translate({dx:.1f}px,{dy:.1f}px) rotate(0)}}"
                   f"{pct(t_ok + 0.45, T)}{{opacity:1;transform:translate({counter_x - tx:.0f}px,{counter_y - ty:.0f}px)}}"
                   f"{pct(t_ok + 0.5, T)},100%{{opacity:0;transform:translate({counter_x - tx:.0f}px,{counter_y - ty:.0f}px)}}}}"
                   f".{n}{{opacity:0;animation:{n} {T:.2f}s infinite;transform-box:fill-box;transform-origin:center}}")
        kind = "ultra" if name == FINAL else "poke"
        fx.append(f'<g transform="translate({tx - 5:.0f} {ty - 5:.0f})"><use href="#ball-{kind}" width="10" height="10" class="{n}"/></g>')
        big = name == FINAL
        fx.append(puff(css, mx, my, t_ok, T, f"ok{k}", ["#fff3a0", "#ffffff", "#ffd84a"],
                       n=14 if big else 6, spread=22 if big else 10))

    # 잡은 수 카운터
    hud = [f'<use href="#ball-poke" x="{counter_x}" y="{counter_y - 1}" width="13" height="13"/>']
    edges = [0.0] + caught_times + [T]
    for k in range(len(edges) - 1):
        a, b = edges[k], edges[k + 1]
        n = f"cnt{k}"
        if k == 0:
            kf = f"0%,{pct(b - 0.001, T)}{{opacity:1}}{pct(b, T)},100%{{opacity:0}}"
        elif k == len(edges) - 2:
            kf = f"0%,{pct(a - 0.001, T)}{{opacity:0}}{pct(a, T)},99.9%{{opacity:1}}100%{{opacity:0}}"
        else:
            kf = f"0%,{pct(a - 0.001, T)}{{opacity:0}}{pct(a, T)},{pct(b - 0.001, T)}{{opacity:1}}{pct(b, T)},100%{{opacity:0}}"
        css.append(f"@keyframes {n}{{{kf}}}.{n}{{animation:{n} {T:.2f}s infinite steps(1)}}")
        hud.append(f'<text x="{counter_x + 16}" y="{counter_y + 10}" class="t {n}">×{k}</text>')

    # 트레이너 이동
    sw, sh = 14 * TS, 18 * TS
    t_css, t_face = route_keyframes("tpath", pts, timeline + [(T, float(len(pts) - 1))], T, sw / 2, sh - 4)
    css += t_css
    css.append(face_css("tface", t_face, T, sw).replace("{T}", f"{T:.2f}"))
    css.append(f"@keyframes tspawn{{0%,{pct(SPAWN - 0.01, T)}{{opacity:0}}{pct(SPAWN + 0.2, T)},100%{{opacity:1}}}}")
    css.append(f"@keyframes tjump{{0%,{pct(t_end + 0.1, T)}{{transform:translateY(0)}}{pct(t_end + 0.3, T)}{{transform:translateY(-8px)}}"
               f"{pct(t_end + 0.5, T)},100%{{transform:translateY(0)}}}}")
    sx, sy = center(*pts[0])
    fx.append(puff(css, sx, sy, SPAWN, T, "sp", ["#ffffff", "#fff3a0", "#cfe8ff"]))
    trainer = (
        f'<g class="tpath"><g class="tspawn"><g class="tjump"><g class="tface">'
        f'<g class="legA" transform="translate(0 {16*TS})">{pixel_rects(LEGS_A, TRAINER_PAL, TS)}</g>'
        f'<g class="legB" transform="translate(0 {16*TS})">{pixel_rects(LEGS_B, TRAINER_PAL, TS)}</g>'
        f'{pixel_rects(TRAINER, TRAINER_PAL, TS)}'
        f'</g></g></g></g>'
    )

    ly = TOP + 7 * CELL + 8
    lx = width - MARGIN - 5 * 15 - 30
    legend = [f'<text x="{lx - 6}" y="{ly + 10}" text-anchor="end" class="t">Less</text>']
    legend += [f'<use href="#g{i}" x="{lx + i*15}" y="{ly}" width="{BLOCK}" height="{BLOCK}"/>' for i in range(5)]
    legend.append(f'<text x="{lx + 5*15 + 2}" y="{ly + 10}" class="t">More</text>')
    label = f"{user}" + (f" · {total} contributions" if total else "")
    legend.append(f'<text x="{MARGIN}" y="{ly + 10}" class="t">{label}</text>')

    style = f"""
{''.join(light_css)}
@media (prefers-color-scheme:dark){{{''.join(dark_css)}}}
.t{{font:600 11px ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;fill:#8b949e}}
.dl{{font:700 12px 'Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif;fill:#222222}}
.tpath{{animation:tpath {T:.2f}s linear infinite}}
.tspawn{{opacity:0;animation:tspawn {T:.2f}s infinite}}
.tjump{{animation:tjump {T:.2f}s infinite}}
.legA{{animation:legA .3s steps(1) infinite}}
.legB{{animation:legB .3s steps(1) infinite}}
@keyframes legA{{0%{{opacity:1}}50%{{opacity:0}}}}
@keyframes legB{{0%{{opacity:0}}50%{{opacity:1}}}}
{''.join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.tpath{{display:none}}}}
"""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" shape-rendering="crispEdges">'
        f'<style>{style}</style><defs>{"".join(defs)}</defs>'
        f'{"".join(grid)}{trainer}{"".join(fx)}{"".join(hud)}{"".join(legend)}</svg>'
    ), T


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "haeunjeon0410"
    out = sys.argv[2] if len(sys.argv) > 2 else "poke-preview.svg"
    cells, total = fetch_levels(user)
    svg, T = build_svg(cells, total, user)
    with open(out, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"{out}: cycle={T:.1f}s")


if __name__ == "__main__":
    main()
