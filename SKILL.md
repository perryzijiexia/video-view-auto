---
name: video-view-auto
description: 从零检索可商用实拍素材、逐条核验地点、剪成 30–90 秒的产品/目的地短片，并交付素材清单、EDL 与授权说明。Use when the user asks to 找可商用视频素材、把景点/酒店/餐食拼成一条介绍片、做一分钟左右的产品短片、给旅行/目的地产品配一条实景混剪，或要求"素材 + 成片一起交付"。
whenToUse: 用户要一条由实拍素材拼成的短片（产品介绍、目的地形象、门店屏、私域转发），尤其是强调"可商用"或"必须对应实景"时。
---

# video-view-auto

把「找素材 → 核验 → 剪片 → 交付」做成一条可复现的流水线。
核心不是剪辑技巧，是**两道闸门**：授权闸门（能不能商用）和地点闸门（是不是那个地方）。

## 一句话原则

> **一个镜头 = 一个能说出名字的真实地点。**
> 说不出名字的镜头，不要放进片子；能用"同类示意"糊过去的，最后都会被打回。

---

## 阶段 0 · 先定三件事

| 要定 | 默认值 | 说明 |
|---|---|---|
| 片长 | 60–75 秒 | 12–15 镜 × 4.5–7 秒，0.6 秒叠化 |
| 画幅 | 1920×1080 / 25fps | 竖版另做，不要硬裁 16:9 |
| 落点 | 产品名 / 3 条卖点 / 价格 / 班期 | 字卡最后 3.5 秒 |

把「产品涉及的景点、体验、餐食、酒店」列成表，先标出**哪些必须实景**（地标、极光、冰川、酒店外观），哪些**可以只出现在文字里**。

---

## 阶段 1 · 检索（Pexels 为主，Wikimedia 补缺口）

Pexels 的搜索页挡 curl（403），用 ego 浏览器；下载走 `pexels.com/download/video/<id>/`，curl 可以。

```bash
cp scripts/pexels_search.js work/pexels_search.js
# 编辑 work/pexels_search.js 顶部的 QUERIES / OUT，每条查询一个 key
ego-browser nodejs < work/pexels_search.js
```

查询写法，按地点名而不是形容词：

```
hallgrimskirkja / geysir iceland / gullfoss waterfall / diamond beach iceland
jokulsarlon glacier lagoon / tromso arctic cathedral / reine lofoten
henningsvaer / lofoten winter / king crab norway / ice cave iceland
```

返回的 `slug` 自带描述（`aerial-view-of-reine-lofoten-islands-39835662`），先用 slug 粗筛，能省掉一半核验。
Pexels 没有的机位，去 Wikimedia Commons 找视频或照片：

```bash
curl -s "https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=filetype%3Avideo%20Fjellheisen&srnamespace=6&format=json"
```

---

## 阶段 2 · 核验（这一步决定片子有没有价值）

```bash
cp scripts/pexels_meta.js work/pexels_meta.js   # 填 IDS / OUT
ego-browser nodejs < work/pexels_meta.js
```

**通过标准，逐条对**：

1. 素材页标题或描述**明确写出地点**（"…Hallgrimskirkja church in Reykjavik, Iceland"）→ 可用；
2. 只写泛称（"geothermal spa"、"ice cave"、"coastal town"）→ **不用**，哪怕缩略图很像；
3. 地标可以用"地貌唯一性"兜底（亨宁斯韦尔海上球场这种全世界只有一个的）；
4. 授权：Pexels License / CC0 直接用；CC BY 要署名；**CC BY-SA 不要用在商业广告片里**（ShareAlike 会污染整条片子）。

标题骗人是常态，真实踩过的坑：

| 素材 | 标题/页面写的 | 实际是 |
|---|---|---|
| `40173857` | "stunning aerial view of … church" | 阿克雷里教堂，不是哈尔格林姆教堂 |
| `35065675` | "cityscape in winter" | 瑞典延雪平，不是雷克雅未克 |
| `6650204` | "cable car passing by" | 阿尔卑斯缆车，不是 Fjellheisen |

---

## 阶段 3 · 下载

```bash
scripts/fetch_clip.sh 4595479 raw            # Pexels id
scripts/fetch_clip.sh https://upload.wikimedia.org/.../file.webm raw
```

4K 原片一条 20–150 MB，十几条就是 1 GB 量级，先估磁盘。
下载后**必须抽帧看一眼**（首/中/尾三帧拼一张联络图），确认：

- 画面内容与标题一致；
- 季节/天气能接受（夏季素材放进极光片会很跳）；
- 有没有水印、可识别 logo、正脸大特写；
- 有没有窗户反光、镜头脏点（缆车、船舱素材常见）。

---

## 阶段 4 · 出字卡

```bash
cp examples/cards.example.json work/cards.json    # 改文案
python3 scripts/cards.py work/cards.json          # -> cards/title.png, cap_NN.png, endcard.png
```

- 字幕条左下角：中文地名 + 英文，字号 46/22，距底 8%；
- 片名居中，字卡最后 3.5 秒；
- **默认不落品牌名**，除非用户明确要求；
- 价格/班期写死在字卡里时，交付前再核一遍当期价格。

---

## 阶段 5 · 剪

```bash
cp examples/shots.example.json work/shots.json    # 按 EDL 填 src/in/dur/caption
python3 scripts/build.py work/shots.json --dry-run   # 先看时码
python3 scripts/build.py work/shots.json             # 出片 + EDL
```

`build.py` 做的事：逐镜裁剪归一（1080p/25fps）→ 统一调色 → 0.6 秒叠化 → 叠字卡 → 垫音乐 → H.264 + AAC，并自动写 `*_EDL.csv`。

每个镜头还能单独加 `"pregrade"`，用来救季节点不对的实拍（例：把夏季缆车素材的绿色压掉）：

```json
{ "src": "raw/fjellheisen.webm", "in": 60.0, "dur": 6.5,
  "pregrade": "eq=saturation=0.55:contrast=1.08:brightness=-0.03," }
```

**统一调色是让一堆不同来源的素材变成"一支片"的关键**，默认这组参数够用：

```
eq=contrast=1.05:saturation=0.94:brightness=-0.006:gamma=1.02,
colorbalance=rs=-0.015:bs=0.025:rm=0.008:bm=0.012:rh=0.012:bh=-0.008,
vignette=PI/5
```

---

## 阶段 6 · 交付（缺一不可）

| 文件 | 作用 |
|---|---|
| `<片名>.mp4` | 成片（另出一条 crf 25 的轻量版，微信用） |
| `素材清单.md/.csv` | 每镜：素材 ID、原始规格、作者、**核验依据**、来源链接、授权 |
| `EDL.csv` | 成片时码 ↔ 素材入点，可导入 Premiere / 剪映 |
| `授权与使用说明.md` | 授权类型、限制、合规红线、存档建议 |
| `封面.jpg` / `素材总览.jpg` | 提案用 |

交付文档里必须写清楚：**哪些是实地、哪些不是**。哪怕最后全换成实地了，也要写"用什么标准验的"。

---

## 硬规则

1. **标题不写地点 = 不用**。不要用"看起来很像是"当依据。
2. **不要用 CC BY-SA** 做商业广告片的素材（整片授权会被传染）。
3. **不要出现未经授权的品牌名/logo**；片尾默认不落款。
4. **自然现象不承诺**：极光、蓝冰洞、野生动物一律写"不保证"。
5. **价格必须与当期一致**，分班期写清楚，别用"起"掩盖差价。
6. 素材只做"氛围/地点"，不做"本团实拍"的暗示。

---

## 目录约定

```
work/
  pexels_search.js   pexels_meta.js   搜索与核验脚本（复制后改常量）
  index.json         meta.json        检索与核验结果
  raw/                               原始素材
  cards.json         cards/           字卡配置与 PNG
  shots.json                         剪辑表
  _clips/                            归一化中间片
out/
  reel.mp4  reel_EDL.csv  cover.jpg
```

## 常见坑

- **ego-browser 脚本不继承环境变量、拿不到命令行参数**，配置只能写在脚本常量里，所以流程是"复制 → 改 → 跑"。
- **Pexels 的 `/download/video/<id>/` 只给最高分辨率**（常是 4K），没有参数可以要 1080p；要么下原片再转，要么接受体积。
- **`-ss` 放在 `-i` 前面**才是快速定位；抽帧核对时前后各留 0.5 秒余量。
- **xfade 要求所有输入同分辨率/同帧率/CFR**，所以每一镜必须先归一化（`build.py` 已经做了），否则会报 `current rate of 1/0 is invalid`。
- **图片生成的静帧要用 `-r 25` 显式指定帧率**，否则进 xfade 会炸。
