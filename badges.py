"""체육관 배지 도트 (14px, 직접 그림). 관동 배지 모양을 참고한 팬아트."""
K = "#1e1e24"
BADGES = {
    "boulder": ([  # 그레이배지
        "....kkkkkk....", "...kGGGGGGk...", "..kGWGGGGGGk..", ".kGWGGGGGGGgk.", "kGWGGGGGGGGggk",
        "kGGGGGGGGGGggk", "kGGGGGGGGGgggk", "kgGGGGGGGggggk", "kggGGGGGgggggk", ".kggggggggggk.",
        "..kggggggggk..", "...kggggggk...", "....kkkkkk...."],
        {"k": K, "G": "#a9b0b8", "g": "#7d858f", "W": "#eef1f4"}),
    "cascade": ([  # 블루배지
        "......kk......", ".....kBBk.....", "....kBBBBk....", "...kBWBBBBk...", "..kBWBBBBBBk..",
        ".kBWBBBBBBbbk.", ".kBBBBBBBbbbk.", "kBBBBBBBbbbbbk", "kBBBBBBbbbbbbk", ".kBBBbbbbbbbk.",
        "..kbbbbbbbbk..", "...kkbbbbkk...", ".....kkkk....."],
        {"k": K, "B": "#5aa8f0", "b": "#2f6fc4", "W": "#e6f3ff"}),
    "soul": ([  # 핑크배지
        "..kkk....kkk..", ".kPPPk..kPPPk.", "kPWPPPkkPPPPpk", "kPWPPPPPPPPppk", "kPPPPPPPPPpppk",
        ".kPPPPPPPpppk.", "..kPPPPPpppk..", "...kPPPpppk...", "....kPpppk....", ".....kppk.....",
        "......kk......"],
        {"k": K, "P": "#f58bbd", "p": "#d0508f", "W": "#ffe3f0"}),
    "marsh": ([  # 골드배지
        "....kkkkkk....", "..kkYYYYYYkk..", ".kYYWYYYYYYyk.", ".kYWkkkkkkYyk.", "kYYkYYYYYYkyyk",
        "kYYkYYYYYYkyyk", "kYYkYYYYYYkyyk", "kYYkYYYYYYkyyk", ".kYYkkkkkkyyk.", ".kYYYYYYyyyyk.",
        "..kkyyyyyykk..", "....kkkkkk...."],
        {"k": K, "Y": "#ffd23f", "y": "#d39a14", "W": "#fff6c8"}),
    "earth": ([  # 그린배지
        "..........kk..", "........kkGGk.", "......kkGGGGk.", "....kkGGGGGGk.", "...kGGGgGGGGk.",
        "..kGGGGGgGGk..", ".kGWGGGGGgGk..", ".kGWGGGGGGgk..", "kGGGGGGGGGk...", "kgGGGGGGkk....",
        "kkgGGGkk......", "k.kkkk........"],
        {"k": K, "G": "#5fce6a", "g": "#2e8f3c", "W": "#dcffe0"}),
}
