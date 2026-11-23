# video-view-auto

把「找可商用实拍素材 → 逐条核验地点 → 剪成一条短片」做成可复现的流水线。
给 DeepSeek Harness 用的 skill，也可以当一套独立的脚本工具用。

**它解决的问题**：AI 剪片最贵的不是剪辑，是**选错素材**——拿阿尔卑斯缆车冒充 Fjellheisen、拿通用温泉冒充蓝湖，片子看着挺美，客户一问地点就废。
所以这套流程把「授权」和「地点」做成两道硬闸门，过不了就不进片。

---

## 安装（作为 DSH skill）

```bash
git clone https://github.com/perryzijiexia/video-view-auto.git ~/.dsh/skills/video-view-auto
```

装好后在会话里说「用 video-view-auto 做一条冰岛挪威的介绍片」即可触发。

## 依赖

| 依赖 | 用途 | 检查 |
|---|---|---|
| `ego-browser` | 打开 Pexels 搜索页/素材页（站点挡 curl） | `ego-browser skill` |
| `ffmpeg` | 裁剪、归一化、叠化、编码 | `ffmpeg -version` |
| `python3` + `Pillow` | 生成字幕条/片名/字卡/封面 | `python3 -c "import PIL"` |
| `curl` | 下载素材 | — |

`ffmpeg` 找不到时，`build.py` 会自动回退到 `imageio_ffmpeg` 自带的二进制。

## 快速开始

```bash
mkdir -p work/raw out

# 1) 检索：搜地点名，不搜形容词
cp scripts/pexels_search.js work/pexels_search.js   # 改 QUERIES
ego-browser nodejs < work/pexels_search.js

# 2) 核验：标题里必须明确写出地点
cp scripts/pexels_meta.js work/pexels_meta.js       # 改 IDS
ego-browser nodejs < work/pexels_meta.js

# 3) 下载
bash scripts/fetch_clip.sh 4595479 raw

# 4) 字卡
cp examples/cards.example.json work/cards.json
python3 scripts/cards.py work/cards.json

# 5) 剪辑
cp examples/shots.example.json work/shots.json
python3 scripts/build.py work/shots.json --dry-run
python3 scripts/build.py work/shots.json
```

产物：`out/reel.mp4` + `out/reel_EDL.csv` + `cards/cover.jpg`。

## 目录

```
SKILL.md              给 agent 的完整流程（六阶段 + 硬规则）
references/
  licensing.md        Pexels / Mixkit / Wikimedia 授权速查与红线
scripts/
  pexels_search.js    批量搜索（ego-browser 模板）
  pexels_meta.js      抓标题核验地点
  fetch_clip.sh       按 id/URL 下载并打印规格
  cards.py            JSON → 片名/字幕条/字卡/封面 PNG
  build.py            JSON → 成片 + EDL
examples/
  shots.example.json  剪辑表样例（含 pregrade 用法）
  cards.example.json  字卡样例
```

## 两条硬规则

1. **标题不写地点 = 不用。** 缩略图再像也不算。
2. **CC BY-SA 不进商业片。** Pexels License 与 CC0 才是安全区。

其余细节见 [SKILL.md](SKILL.md) 与 [references/licensing.md](references/licensing.md)。

## License

MIT
