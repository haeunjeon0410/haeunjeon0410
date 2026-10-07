# 마인크래프트 버전 (백업)

잔디를 마인크래프트 점프맵으로 그리는 버전. 지금 프로필에는 포켓몬 버전이 쓰이고 있고, 이건 보관용이다.

- 커밋한 날만 블록으로 쌓이고, 광부가 점프하며 금/다이아를 캔다 (공백이 길면 판자 다리)
- 크리퍼가 뒤따라오고, 다이아/금 2개 이상이면 검으로 승리, 아니면 You Died!

## 다시 쓰려면

`.github/workflows/pokemon.yml`의 생성 줄을 바꾸고, README의 그림 주소를 `minecraft-contrib.svg`로 바꾸면 된다.

```yaml
python minecraft/generate_minecraft.py ${{ github.repository_owner }} dist/minecraft-contrib.svg
```
