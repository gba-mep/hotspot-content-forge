# GIF / MP4 视频生成实战（公开版）

> 小红书演示视频 / GIF / 口播视频的实战管线笔记，命令与参数均实测可用。

## 1. 环境

- **ffmpeg**（6.1.1，apt 安装）：帧序列合成 MP4 的核心，直接 subprocess 调用。
- **PIL**：逐帧画图（GIF 直出 + MP4 的帧源）。
- imageio / moviepy 2.x：拼接/剪辑/合成可用 moviepy（`concatenate_videoclips(method="compose")`），逐帧画图仍用 PIL+ffmpeg 更可控；moviepy 2.x 直接 `from moviepy import ...`，`write_videofile` 传 `logger=None` 静默。

## 2. 实测管线（全部验证通过）

1. **GIF**：PIL 画帧 →
   ```python
   frames[0].save(out, save_all=True, append_images=frames[1:],
                  duration=100, loop=0, optimize=True)
   ```
   坑：`ImageDraw.arc()` 参数是 `fill` 不是 `outline`。

2. **图片序列→MP4**：每帧存 `f%04d.png` →
   ```bash
   ffmpeg -framerate 30 -i f%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20 out.mp4
   ```
   **`-pix_fmt yuv420p` 必加**，否则部分播放器黑屏。

3. **文本→MP4**：逐句拆卡，每句淡入淡出（透明度曲线），同②合成。

4. **数据→MP4**：数据面板+数字滚动（ease-out cubic：`1-(1-p)**3`）+进度圆环，同②。

5. **单图→MP4**：Ken Burns 效果：
   ```bash
   ffmpeg -loop 1 -i 图 -vf "zoompan=z='min(zoom+0.0015,1.3)':d=90:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'" -t 3 out.mp4
   ```

6. **产品宣传演示 MP4**（竖版 720×1280/15fps）：场景线=功能选择卡→各模式界面仿真帧→结尾卡+评论区钩子；界面用 PIL 画（产品的配色/标题栏/表格网格），数据跳动用每帧重画。秒级抽帧目检每个场景至少一帧。
   偏好参考：轻亮色调（浅灰白底+白卡片）优先于深色；开场即打出第一卖点的徽章，主功能占视频前半段，次要模式降为「还有一招」；产品的隐藏功能最好在视频里演示出来。

7. **实拍感视频（图库照片+Ken Burns+字幕标签）**：嫌「模拟界面动画不真实」时的替代路线。素材用免费图库照片直链（如 Pexels 照片 `https://images.pexels.com/photos/{id}/pexels-photo-{id}.jpeg?auto=compress&cs=tinysrgb&w=1600`，curl 可直接下；**视频文件直链 404、搜索页反爬——只走照片通道**）。做法：照片按竖版裁切（重心 cy≈h*0.42）+ 每段 Ken Burns（zoom 1.0→1.18 线性）+ PIL 字幕标签 + Contrast 1.06，ffmpeg yuv420p 合成。
   **诚实边界**：图库是 generic 素材（设备型号/人种未必对题），交付时须声明局限；「真设备真现场」级素材只能实拍——直接给镜头清单（每镜头 5~10s 手机竖版：开机特写/按键/读数跳动/现场全景），拍完再剪辑加字幕节奏包装。

8. **配 BGM**：版权红线——平台歌曲（QQ音乐/网易云等）一律不得下载使用。默认方案：**程序合成原创曲**（numpy 正弦+泛音+简易鼓点 → wave → ffmpeg libmp3lame 192k），零版权。也可用许可明确的商用库（CC0 或 CC-BY，CC-BY 须逐曲署名）。合成配方：
   - 采样率 44100；音色三档：soft（基频+八度+三度泛音）/ pluck（指数衰减）/ pad（长音+attack-release 包络）。
   - 结构：和弦铺底（pad，vol≈0.10）+ 主旋律（vol≈0.22）+ kick（120Hz 指数衰减）+ hat（噪声，隔拍）。
   - 混音用**时间片写入**：每层 note 定长数组，按 `mix[s:e] += w[:e-s]` 切片累加——直接 `mix += note(...)` 形状不等必然 broadcast 报错。
   - 归一化到 0.85 峰值 + 末尾 1.5s 线性淡出；循环拼接时首尾各裁 1s 无缝。

   情绪↔场景对照：

   | 曲目 | 用在 |
   |---|---|
   | 轻快 120BPM | 开场钩子、功能演示 |
   | 紧张 132BPM | 倒计时、翻车叙事 |
   | 治愈 92BPM | 战报、听劝更新 |
   | 稳重 84BPM（无鼓点） | 数据面板、讲解类 |
   | 胜利 128BPM | 破纪录、上线成功 |

   混入成品视频：
   ```bash
   ffmpeg -i 视频.mp4 -i 音乐.mp3 -filter_complex \
     "[1:a]aloop=loop=-1:size=2e+09,atrim=0:<视频秒数>,volume=0.25[a1];[0:a][a1]amix=inputs=2:duration=first" \
     -c:v copy -c:a aac out.mp4
   ```
   - `volume=0.25` 铁律：BGM 永远垫在主体声音之下；纯画面视频直接映射音乐流。
   - 短曲拉长用 aloop，不要重复生成。

## 3. 口播视频全自动出片（TTS→画帧→合成→混音）

> 用口播逐段时长驱动场景帧数，产出带人声+BGM 的完整竖版视频。

流程：

1. **写分镜台词表**：每场景一条口播句 + 场景标签（hook/演示/卖点/钩子结尾）。文案先过敏感词自查（帧内文字与口播都用安全词）。
2. **分段 TTS**：每场景独立合成（edge-tts）——分段才能用各段实测时长驱动该场景帧数，改单段不用重跑全片：
   ```python
   edge_tts.Communicate(句, "zh-CN-YunxiNeural", rate="+8%").save("voN.mp3")
   ```
3. **按口播时长画帧**：每场景帧数 `n = int(实测时长 * FPS)`（用 ffprobe 实测，不从预估——中文语速 ±15% 波动，预估会导致画外音被下一场景吞掉）；动态元素按 `j / max(n-1,1)` 插值，每帧先擦除再重画。
4. **合成视频**：帧序列 → `ffmpeg -framerate FPS -i f%04d.png -c:v libx264 -pix_fmt yuv420p -crf 20 out.mp4`。
5. **拼接口播**：
   ```bash
   ffmpeg -i vo0.mp3 -i vo1.mp3 … -filter_complex "[0:a][1:a]…concat=n=N:v=0:a=1[vo]" \
     -map "[vo]" -c:a libmp3lame vo_full.mp3
   ```
6. **混 BGM**：BGM `volume=-20dB` + 尾部 `afade=t=out:st=(口播总长-1.5):d=1.5` + `amix=inputs=2:duration=first` + `loudnorm=I=-16:TP=-1.5`，输出 **`.m4a`**。
7. **封装**：`ffmpeg -i video.mp4 -i audio.m4a -c:v copy -c:a copy -shortest 成品.mp4`。
8. **终检**：按场景中点抽 3–5 帧目检（文字完整/无重叠/无豆腐/无贴边），抽帧前删旧预览图。

坑位：

- **concat 滤镜必须显式 `-map "[vo]"`**——filter_complex 的具名输出不接 map 时 ffmpeg 报 unconnected output 直接失败。
- **混音输出必须纯音频容器（.m4a）+ `-vn`**——口播+mp3 两条输入会给 mp4 带进第二条流，被当视频流拒写 header。
- **逐行宽度检查，不只标题**——38pt×16 字在 720px 画布就贴边裁切；每个 `d.text()` 前都用 `d.textlength(line, font)` 对 `W-80` 校验，超了缩文案不缩字号。
- edge-tts 运行期 `insecure` 相关警告无害，忽略。
- TTS 语音文件缓存到本地后再跑后续步骤，避免重跑整片时重复请求。

音色速查（edge-tts）：

| key | 音色 | 用途 |
| --- | --- | --- |
| yunxi（默认） | zh-CN-YunxiNeural | 男·年轻，口播主力 |
| xiaoxiao | zh-CN-XiaoxiaoNeural | 女·标准 |
| yunjian | zh-CN-YunjianNeural | 男·沉稳，硬核教程 |
| xiaoyi | zh-CN-XiaoyiNeural | 女·活泼 |
| 语速 | `rate="+8%"` 起步 | 小红书节奏偏快，负值慎用 |

时长规律：口播语速 +8% 约为 4.5 字/秒，18 字台词 ≈ 4s；要 30s 视频写 130 字左右的台词表。帧数=口播秒数×FPS，视频总长自动等于口播总长（BGM 用 duration=first 跟随）。

## 4. 参数速查与坑位

- crf 20=高清，23=默认，28=小文件；时长=帧数/帧率。
- **中文帧图必用 NotoSansCJK 字体**。CJK 字体铁律：NotoSansCJK/SerifCJK 的一切 `.ttc` 必须 `ImageFont.truetype(path, sz, index=2)`（SC 简体面）——不传 index 默认 0 是**日文面**，「门/关/复/画」等字骨架变形；务必显式传 `index=2`。
- **NotoSansCJK 无 emoji 字形**：☕ 等 emoji 必出豆腐块，用纯文字或自绘图形替代。
- MP4 比 GIF 小一个量级，能 MP4 不 GIF；GIF>500KB 降帧率。
- 中文文件名 ffmpeg 支持，但帧序列模板 `%04d` 必须纯 ASCII 路径。
- **从成品 MP4 抽帧目检更稳**：`ffmpeg -ss <秒> -i 成品.mp4 -frames:v 1 预览图.png`，省得保留帧目录。
- **精确抽帧把 `-ss` 放在 `-i` 之后**：放前面是快速定位，落到最近关键帧，抽到的不是你要的秒，会把已修好的场景误判没修。
- **抽帧前先删旧预览图**：ffmpeg 遇同名文件交互问 Overwrite? 直接退出，留下旧图——复查一张没更新的帧会把已修好的 bug 当没修；抽帧后按 `秒数×fps` 对帧号，确认抽到的是目标场景。
- **动态文字/进度条每帧必须先用背景色矩形擦除再重画**：PIL 帧是独立位图，但同帧内多次 draw.text 同位置会叠加；且若在 img.copy() 上叠画而底图残留旧字，整段出现重影（百分比 100% 叠成 0%+100%）。

## 5. 尺寸规范

- **小红书笔记视频必须 1080P 及以上**（平台会对低分辨率视频提示影响观看时长）；720×1280 源帧用 `fr.resize((1080,1920), Image.LANCZOS)` 1.5x 重采样后存帧再合成，文字边缘无损感，不用 ffmpeg scale。
- 3:4=1242×1660；横版 16:9=1280×720。

## 6. 发布前文案自查

- 宣传视频/海报的**帧内文字也是审核对象**（笔记会因视频文案被拒）：合成前对脚本 grep 敏感词清零，伪装/骗/老板类词换「特效/整蛊朋友/摸鱼神器」；改完重跑脚本再 grep 一次，逐场景 patch 时容易漏最后一处。
- 时长加长的需求落在场景帧数上（`n=int(秒*FPS)`），不是尾部冻结。

## 7. 火柴人风格管线（stick-explainer）

- 配色：paper `#F3F0EA` / ink `#24242C` / accent `#EB4A2A`（只用一个强调色）/ mute `#9C978C`；火柴人=头纸色圆盘+墨环、四肢单曲线（二次贝塞尔、关节作控制点）、round caps。
- **坑1**：贝塞尔公式把控制点/终点写反（`2(1-t)t*p2 + t²*p1`）→ 所有曲线提前在控制点收笔。正确：`2(1-t)t*控制点 + t²*终点`。握手点必须落在两人之间的空档且在肩上方，肩部坐标从骨架算，勿硬编码。
- **坑2**：文字滑入函数对 p≤0 必须提前 return——负 p 时插值出负 RGB 通道，PIL 截断成**青色鬼影字**。
- 人数条形图（链条长度=数据）+ 握手成线（一曲线从肩到肩）是两个最出效果的 native moves。
- 盲调三帧不如单帧调试：抽 p=1 的静态调试帧看坐标，一次到位。

## 8. 流程（SOP）

明确需求（尺寸/时长/内容源）→ 选管线（§2）→ PIL 画帧 → ffmpeg 合成 → 验证 rc=0+文件大小 → 抽帧终检 → 交付。

