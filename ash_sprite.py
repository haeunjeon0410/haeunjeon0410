"""지우 (14x18, 2등신 치비). 오른쪽을 봄. 다리 두 프레임."""
ASH = [
    "....oooooo....",
    "...oRRRRRRo...",
    "..oRRWWGWRRo..",
    "..oRRWGGWRRRo.",
    ".oKrrrrrrrrrro",
    ".oKKSSSSSSSoo.",
    "oKKSSSSSSSSo..",
    "oKKSSESSSESo..",
    ".oKSPESSSEPo..",
    "..oSSSSsSSSo..",
    "...ooSSSSoo...",
    "..oWBBTTBBWo..",
    ".ogBBBTTBBBgo.",
    ".ogbBBTTBBbgo.",
    "..ooJJJJJJoo..",
    "...oJJjjJJo...",
]
ASH_LEGS_A = ["...oJo..oJo...", "..oZZo..oZZo.."]
ASH_LEGS_B = ["....oJooJo....", "....oZZZZo...."]
ASH_PAL = {"o": "#1a1a2e", "R": "#e3342f", "r": "#b0221f", "W": "#ffffff", "G": "#2e9e4f",
           "K": "#26262e", "S": "#f6c99a", "s": "#d9776a", "E": "#1a1a2e", "P": "#f59a9a",
           "B": "#2f6fd6", "b": "#234fa0", "T": "#2a2a2a", "g": "#3fae49",
           "J": "#3657a8", "j": "#2a4583", "Z": "#e3342f"}
for r in ASH + ASH_LEGS_A + ASH_LEGS_B:
    assert len(r) == 14, r
