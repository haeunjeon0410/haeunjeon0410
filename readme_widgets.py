"""README 꾸미기 위젯 (포켓몬 컨셉).

- dialog.svg : 게임 대사창 자기소개 (한 글자씩 타이핑 + 깜빡이는 ▼)
- party.svg  : 파티 화면 = 기술 스택. 언어 비율(공개 저장소 기준)이 HP/Lv가 됨

usage: python readme_widgets.py <github_user> <out_dir>
"""
import base64
import io
import json
import os
import sys
import urllib.request

from PIL import Image

from badges import BADGES

# ── 대사창 문구 (자유롭게 수정) ──────────────────────────────
DIALOG = [
    "Hi, I'm Haeun Jeon 👋",
    "Computer Science @ Sookmyung Women's University",
]

# ── 파티: 기술 -> (진화 라인 아이콘 번호들, 이 기술로 세는 GitHub 언어들) ──
# 코드 양(1등 대비)에 따라 진화: 3단계 라인은 25%/60%, 2단계 라인은 40%에서 진화
PARTY = [
    ("JavaScript", [172, 25, 26], ["JavaScript"]),       # 피츄 -> 피카츄 -> 라이츄
    ("HTML/CSS", [133, 700], ["HTML", "CSS"]),           # 이브이 -> 님피아 (예쁜 화면)
    ("C++", [137, 233, 474], ["C++", "C", "CMake"]),     # 폴리곤 -> 폴리곤2 -> 폴리곤Z
    ("Dart", [10, 11, 12], ["Dart"]),                    # 캐터피 -> 단데기 -> 버터플 (Flutter)
    ("TypeScript", [7, 8, 9], ["TypeScript"]),           # 꼬부기 -> 어니부기 -> 거북왕
    ("Python", [23, 24], ["Python"]),                    # 아보 -> 아보크 (뱀)
]


def evo_stage(hp, n):
    cuts = [0.25, 0.6] if n == 3 else [0.4]
    return sum(hp >= c for c in cuts)
ICON_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/versions/generation-vii/icons/{}.png"

W = 880
FONT = "'Galmuri11','NeoDunggeunmo','Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif"


def api(url):
    req = urllib.request.Request(url, headers={"User-Agent": "readme-widgets"})
    tok = os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def language_bytes(user):
    tot = {}
    for repo in api(f"https://api.github.com/users/{user}/repos?per_page=100"):
        for lang, n in api(repo["languages_url"]).items():
            tot[lang] = tot.get(lang, 0) + n
    return tot


def icon_image(pid, height):
    """포켓몬 아이콘 -> 4배 키운 PNG (도트 유지)."""
    raw = urllib.request.urlopen(ICON_URL.format(pid), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    im = im.crop(im.getbbox())
    big = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    buf = io.BytesIO()
    big.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    w = height * im.width / im.height
    return b64, w


def text_width(s, size):
    """대략적인 글자 폭 (한글 1em, 영문/숫자 0.6em, 공백 0.35em)."""
    w = 0.0
    for ch in s:
        if "가" <= ch <= "힣":
            w += size * 1.0
        elif ord(ch) > 0x1F000:                 # 이모지
            w += size * 1.25
        elif ch == " ":
            w += size * 0.35
        else:
            w += size * 0.6
    return w


def dialog_svg():
    size, x0, y0, lh = 17, 34, 40, 30
    h = 30 + lh * len(DIALOG) + 14
    T, t = 9.0, 0.4
    css, lines = [], []
    for i, line in enumerate(DIALOG):
        tw = text_width(line, size)
        # 한 글자씩: 클립 폭을 글자 단위로 늘림
        kf, acc = [f"0%,{t / T * 100:.2f}%{{width:0px}}"], 0.0
        for ch in line:
            t += 0.07
            acc += text_width(ch, size)
            kf.append(f"{t / T * 100:.2f}%{{width:{acc:.1f}px}}")
        kf.append(f"96%{{width:{tw + 4:.1f}px}}100%{{width:0px}}")
        css.append(f"@keyframes ty{i}{{{''.join(kf)}}}.ty{i}{{animation:ty{i} {T}s infinite steps(1,end)}}")
        y = y0 + i * lh
        lines.append(f'<clipPath id="c{i}"><rect class="ty{i}" x="{x0}" y="{y - size - 2}" width="0" height="{size + 8}"/></clipPath>'
                     f'<text x="{x0}" y="{y}" class="d" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs" '
                     f'clip-path="url(#c{i})">{line}</text>')
        t += 0.5
    style = f"""
.d{{font:700 {size}px {FONT};fill:#303038}}
.arrow{{animation:arrow .8s steps(1) infinite}}
@keyframes arrow{{0%{{opacity:1;transform:translateY(0)}}50%{{opacity:1;transform:translateY(3px)}}}}
{''.join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}rect[class^=ty]{{width:900px}}}}
"""
    ax, ay = W - 46, h - 26
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style>'
            f'<rect x="3" y="3" width="{W - 6}" height="{h - 6}" rx="10" fill="#f8f8f8" stroke="#4a5470" stroke-width="5"/>'
            f'<rect x="10" y="10" width="{W - 20}" height="{h - 20}" rx="6" fill="none" stroke="#9fb4d6" stroke-width="3"/>'
            f'{"".join(lines)}'
            f'<g class="arrow"><path d="M{ax} {ay} h14 l-7 8 z" fill="#e3342f" stroke="#7a1a16" stroke-width="1.5"/></g>'
            f'</svg>')


def party_svg(user):
    """기술 스택 = 파티 화면. 코드 비율이 HP/Lv, 진화 단계는 아이콘과 EVO 점."""
    tot = language_bytes(user)
    shares = [(name, ids, sum(tot.get(l, 0) for l in langs)) for name, ids, langs in PARTY]
    shares.sort(key=lambda r: -r[2])
    total = sum(tot.values()) or 1
    best = max(n for _, _, n in shares) or 1
    cols, sw, sh, gap, top = 3, 276, 78, 10, 42
    h = top + 2 * sh + gap + 18
    slots, css = [], []
    for i, (name, ids, n) in enumerate(shares):
        x = 16 + (i % cols) * (sw + gap)
        y = top + (i // cols) * (sh + gap)
        lead = i == 0
        hp = n / best
        lv = max(1, round(5 + 95 * hp))
        bar = "#58d080" if hp > 0.5 else "#f8c030" if hp > 0.2 else "#f85838"
        stage = evo_stage(hp, len(ids))
        b64, iw = icon_image(ids[stage], 36)
        dots = "".join(f'<rect x="{x + 74 + d * 10}" y="{y + 61}" width="7" height="7" rx="3.5" '
                       f'fill="{"#e8762c" if d <= stage else "#a9b6c8"}"/>' for d in range(len(ids)))
        css.append(f".ic{i}{{animation:hop .6s steps(1) infinite;animation-delay:{-i * 0.1:.1f}s}}")
        slots.append(
            f'<rect x="{x}" y="{y}" width="{sw}" height="{sh}" rx="12" fill="{"#fbe3b0" if lead else "#e3f1fc"}" '
            f'stroke="{"#e8762c" if lead else "#2c5f94"}" stroke-width="3"/>'
            f'<ellipse cx="{x + 38}" cy="{y + 58}" rx="21" ry="5" fill="#000" fill-opacity=".12"/>'
            f'<g class="ic{i}"><image href="data:image/png;base64,{b64}" x="{x + 38 - iw / 2:.1f}" y="{y + 20}" '
            f'width="{iw:.1f}" height="36" style="image-rendering:pixelated"/></g>'
            f'<text x="{x + 74}" y="{y + 29}" class="nm">{name}</text>'
            f'<text x="{x + sw - 14}" y="{y + 29}" class="lv" text-anchor="end">Lv.{lv}</text>'
            f'<rect x="{x + 74}" y="{y + 39}" width="24" height="14" rx="3" fill="#f8b030"/>'
            f'<text x="{x + 86}" y="{y + 50}" class="hp" text-anchor="middle">HP</text>'
            f'<rect x="{x + 101}" y="{y + 40}" width="{sw - 117}" height="12" rx="6" fill="#3a3f48"/>'
            f'<rect x="{x + 103}" y="{y + 42}" width="{(sw - 121) * hp:.1f}" height="8" rx="4" fill="{bar}"/>'
            f'{dots}<text x="{x + 74 + len(ids) * 10 + 4}" y="{y + 68}" class="evo">EVO</text>'
            f'<text x="{x + sw - 14}" y="{y + 69}" class="pc" text-anchor="end">{n / total * 100:.0f}%</text>')
    style = f"""
.nm{{font:800 17px {FONT};fill:#15181e}}
.lv{{font:800 15px {FONT};fill:#15181e}}
.hp{{font:900 10px {FONT};fill:#ffffff}}
.evo{{font:800 10px {FONT};fill:#4a5470}}
.pc{{font:800 13px {FONT};fill:#2b3345}}
.tt{{font:900 16px {FONT};fill:#ffffff}}
@keyframes hop{{0%{{transform:translateY(0)}}50%{{transform:translateY(-3px)}}}}
{''.join(css)}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style>'
            f'<rect x="2" y="2" width="{W - 4}" height="{h - 4}" rx="14" fill="#3b7fb6" stroke="#1f4e7a" stroke-width="4"/>'
            f'<text x="20" y="29" class="tt">PARTY · TECH STACK</text>'
            f'{"".join(slots)}</svg>')


def contribution_days(user):
    import re
    req = urllib.request.Request(f"https://github.com/users/{user}/contributions", headers={"User-Agent": "readme-widgets"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
    days = []
    for m in re.finditer(r'<td[^>]*class="ContributionCalendar-day"[^>]*>', html):
        d = re.search(r'data-date="([^"]+)"', m.group(0))
        lv = re.search(r'data-level="(\d)"', m.group(0))
        if d and lv:
            days.append((d.group(1), int(lv.group(1)) > 0))
    return sorted(days)


def streaks(days):
    cur = best = run = 0
    for _, on in days:
        run = run + 1 if on else 0
        best = max(best, run)
    # 오늘 아직 커밋 안 했으면 어제까지의 연속을 현재 기록으로
    for _, on in reversed(days[:-1] if days and not days[-1][1] else days):
        if not on:
            break
        cur += 1
    return cur, best


TIME_TYPES = [  # (시작시, 끝시, 칭호, 포켓몬 아이콘)
    (0, 6, "새벽형 트레이너", 163),     # 부우부
    (6, 12, "아침형 트레이너", 16),     # 구구
    (12, 18, "한낮형 트레이너", 192),   # 해루미
    (18, 24, "저녁형 트레이너", 198),   # 니로우
]


def trainer_type(user):
    import datetime
    hours = [0] * 24
    for page in range(1, 11):
        try:
            items = api(f"https://api.github.com/search/commits?q=author:{user}&per_page=100&page={page}")["items"]
        except Exception:
            break
        for it in items:
            t = datetime.datetime.fromisoformat(it["commit"]["author"]["date"].replace("Z", "+00:00"))
            hours[t.astimezone(datetime.timezone(datetime.timedelta(hours=9))).hour] += 1
        if len(items) < 100:
            break
    total = sum(hours) or 1
    a, b, title, pid = max(TIME_TYPES, key=lambda tt: sum(hours[tt[0]:tt[1]]))
    return title, pid, round(sum(hours[a:b]) / total * 100), a, b


def stats_svg(user):
    cur, best = streaks(contribution_days(user))
    title, tpid, pct, a, b = trainer_type(user)
    tiles = [
        (f"{cur} days", "Current streak"),
        (f"{best} days", "Longest streak"),
        (f"{a:02d}:00–{b:02d}:00", f"Most active hours · {pct}% of commits"),
    ]
    tw, h = (W - 16 * 2 - 10 * 2) / 3, 70
    out = []
    for i, (big, small) in enumerate(tiles):
        x = 16 + i * (tw + 10)
        out.append(f'<rect x="{x:.1f}" y="8" width="{tw:.1f}" height="{h - 16}" rx="10" class="card" stroke-width="1.5"/>'
                   f'<text x="{x + tw / 2:.1f}" y="33" class="big" text-anchor="middle">{big}</text>'
                   f'<text x="{x + tw / 2:.1f}" y="52" class="sm" text-anchor="middle">{small}</text>')
    style = f"""
.card{{fill:#ffffff;stroke:#d0d7de}}.big{{font:800 21px {FONT};fill:#1f2328}}.sm{{font:700 13px {FONT};fill:#424a53}}
@media (prefers-color-scheme:dark){{.card{{fill:#0d1117;stroke:#30363d}}.big{{fill:#f0f6fc}}.sm{{fill:#c9d1d9}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style>{"".join(out)}</svg>')


# 기술 -> 체육관 배지
BADGE_OF = {"JavaScript": "marsh", "TypeScript": "cascade", "HTML/CSS": "rainbow",
            "C++": "boulder", "Dart": "soul", "Python": "earth"}


def rows_png(rows, pal, k=4):
    im = Image.new("RGBA", (len(rows[0]) * k, len(rows) * k), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch != ".":
                c = pal[ch]
                im.paste(tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,), (x * k, y * k, x * k + k, y * k + k))
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def badges_svg(user):
    """기술 스택 = 체육관 배지. 코드 비율 순."""
    tot = language_bytes(user)
    items = sorted(((name, sum(tot.get(l, 0) for l in langs)) for name, _, langs in PARTY), key=lambda x: -x[1])
    total = sum(tot.values()) or 1
    h, top, colw = 150, 46, (W - 32) / len(items)
    out = []
    for i, (name, n) in enumerate(items):
        cx = 16 + colw * (i + 0.5)
        rows, pal = BADGES[BADGE_OF[name]]
        out.append(f'<image href="data:image/png;base64,{rows_png(rows, pal)}" x="{cx - 24:.1f}" y="{top}" width="48" height="{len(rows) * 48 / 14:.1f}" '
                   f'style="image-rendering:pixelated" class="bd" />'
                   f'<text x="{cx:.1f}" y="{top + 76}" class="nm" text-anchor="middle">{name}</text>'
                   f'<text x="{cx:.1f}" y="{top + 96}" class="pc" text-anchor="middle">{n / total * 100:.0f}%</text>')
    style = f"""
.frame{{fill:#ffffff;stroke:#d0d7de}}.tt{{font:800 17px {FONT};fill:#1f2328}}
.nm{{font:800 17px {FONT};fill:#1f2328}}.pc{{font:700 15px {FONT};fill:#424a53}}
@media (prefers-color-scheme:dark){{.frame{{fill:#0d1117;stroke:#30363d}}.tt,.nm{{fill:#f0f6fc}}.pc{{fill:#c9d1d9}}}}
"""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style><rect x="1" y="1" width="{W - 2}" height="{h - 2}" rx="12" class="frame" stroke-width="1.5"/>'
            f'<text x="22" y="30" class="tt">Tech Stack</text>{"".join(out)}</svg>')


# 도감 타입 태그 (진화 라인 포켓몬의 실제 타입)
DEX_TYPE = {"JavaScript": ("ELECTRIC", "#f7c62f", "#3a2c00"), "HTML/CSS": ("FAIRY", "#ee99ac", "#4a0f22"),
            "C++": ("NORMAL", "#a8a878", "#22220e"), "Dart": ("BUG", "#a8b820", "#1f2600"),
            "TypeScript": ("WATER", "#6890f0", "#ffffff"), "Python": ("POISON", "#a040a0", "#ffffff")}


def dex_svg(user):
    """기술 스택 = 포켓몬 도감. 코드 비율 순, 아이콘은 진화 단계 반영."""
    tot = language_bytes(user)
    rows = [(name, ids, sum(tot.get(l, 0) for l in langs)) for name, ids, langs in PARTY]
    rows.sort(key=lambda r: -r[2])
    total = sum(tot.values()) or 1
    best = rows[0][2] or 1
    h = 250
    sx, sy, sw, shh = 22, 58, W - 44, h - 80          # 화면
    ew, eh = (sw - 30) / 2, 46
    out = []
    for i, (name, ids, n) in enumerate(rows):
        col, row = i % 2, i // 2
        x, y = sx + 10 + col * (ew + 10), sy + 10 + row * (eh + 6)
        b64, iw = icon_image(ids[evo_stage(n / best, len(ids))], 34)
        tname, tbg, tfg = DEX_TYPE[name]
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{ew:.1f}" height="{eh}" rx="6" class="entry"/>'
                   f'<text x="{x + 12:.1f}" y="{y + 29}" class="no">No.{i + 1:03d}</text>'
                   f'<image href="data:image/png;base64,{b64}" x="{x + 80 - iw / 2:.1f}" y="{y + 6}" width="{iw:.1f}" height="34" style="image-rendering:pixelated"/>'
                   f'<text x="{x + 108:.1f}" y="{y + 29}" class="nm">{name}</text>'
                   f'<rect x="{x + ew - 150:.1f}" y="{y + 13}" width="78" height="20" rx="10" fill="{tbg}"/>'
                   f'<text x="{x + ew - 111:.1f}" y="{y + 27.5}" class="ty" fill="{tfg}" text-anchor="middle">{tname}</text>'
                   f'<text x="{x + ew - 12:.1f}" y="{y + 29}" class="pc" text-anchor="end">{n / total * 100:.0f}%</text>')
    style = f"""
.no{{font:800 13px ui-monospace,Consolas,monospace;fill:#5c6370}}.nm{{font:800 17px {FONT};fill:#1f2328}}
.ty{{font:800 11px {FONT}}}.pc{{font:800 16px {FONT};fill:#1f2328}}.tt{{font:900 18px {FONT};fill:#ffffff}}
.entry{{fill:#ffffff;stroke:#c8d0c8;stroke-width:1.5}}
.blink{{animation:blink 1.6s steps(1) infinite}}@keyframes blink{{0%{{opacity:1}}50%{{opacity:.35}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
"""
    lights = "".join(f'<circle cx="{110 + j * 20}" cy="24" r="6" fill="{c}" stroke="#4a0d14" stroke-width="2"/>'
                     for j, c in enumerate(["#ff5a5a", "#ffd23f", "#5fce6a"]))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style>'
            f'<rect x="2" y="2" width="{W - 4}" height="{h - 4}" rx="16" fill="#d8323f" stroke="#7a1420" stroke-width="4"/>'
            f'<circle cx="46" cy="29" r="20" fill="#ffffff" stroke="#4a0d14" stroke-width="3"/>'
            f'<circle cx="46" cy="29" r="14" fill="#3d9be9" class="blink"/><circle cx="41" cy="24" r="4" fill="#d9f0ff"/>'
            f'{lights}<text x="{W - 24}" y="33" class="tt" text-anchor="end">TECH DEX</text>'
            f'<rect x="{sx}" y="{sy}" width="{sw}" height="{shh}" rx="8" fill="#e9f2e4" stroke="#2b2b2b" stroke-width="3"/>'
            f'{"".join(out)}</svg>')


def badgecase_svg(user, total_contrib):
    """활동 수치 = 체육관 배지 케이스."""
    cur, best = streaks(contribution_days(user))
    title, tpid, pct, a, b = trainer_type(user)
    items = [("marsh", f"{cur} days", "Current Streak"), ("earth", f"{best} days", "Longest Streak"),
             ("cascade", f"{a:02d}–{b:02d}h", f"Peak Hours · {pct}%"), ("soul", f"{total_contrib}", "Contributions / yr")]
    h = 96
    sw = (W - 24 * 2 - 12 * 3) / 4
    out = []
    for i, (bd, big, small) in enumerate(items):
        x = 24 + i * (sw + 12)
        rows, pal = BADGES[bd]
        out.append(f'<rect x="{x:.1f}" y="16" width="{sw:.1f}" height="{h - 32}" rx="10" fill="#1d2230" stroke="#5a6680" stroke-width="2"/>'
                   f'<image href="data:image/png;base64,{rows_png(rows, pal)}" x="{x + 12:.1f}" y="{h / 2 - 20:.1f}" width="40" '
                   f'height="{len(rows) * 40 / 14:.1f}" style="image-rendering:pixelated"/>'
                   f'<text x="{x + 64:.1f}" y="{h / 2 - 1:.1f}" class="big">{big}</text>'
                   f'<text x="{x + 64:.1f}" y="{h / 2 + 17:.1f}" class="sm">{small}</text>')
    style = f".big{{font:800 21px {FONT};fill:#ffffff}}.sm{{font:700 13px {FONT};fill:#c9d4ea}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {h}" width="{W}" height="{h}">'
            f'<style>{style}</style>'
            f'<rect x="2" y="2" width="{W - 4}" height="{h - 4}" rx="14" fill="#353c52" stroke="#1a1e2a" stroke-width="4"/>'
            f'{"".join(out)}</svg>')


def main():
    user = sys.argv[1] if len(sys.argv) > 1 else "haeunjeon0410"
    out = sys.argv[2] if len(sys.argv) > 2 else "dist"
    os.makedirs(out, exist_ok=True)
    import re
    page = urllib.request.urlopen(urllib.request.Request(f"https://github.com/users/{user}/contributions",
                                                         headers={"User-Agent": "readme-widgets"}), timeout=30).read().decode()
    m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", page)
    total_contrib = m.group(1) if m else "-"
    for name, svg in (("dialog.svg", dialog_svg()), ("stats.svg", badgecase_svg(user, total_contrib)),
                      ("party.svg", party_svg(user))):
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"{out}/{name}: {len(svg)} bytes")


if __name__ == "__main__":
    main()
