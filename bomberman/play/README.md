# 手动炸弹人：人类 vs 电脑

浏览器控制蓝色玩家，与橙色电脑单挑。复用原 `workspace/engine/engine.py` 规则和 `arena.py` 的原版 bot 通信接口，不需要大模型 API。

## 1. 安装环境、下载项目

- 简单电脑：Python 3.10+ 和现代浏览器，无需额外 Python 包，也不需要编译器。
- 原版 AI bot：再准备支持 C++20 的编译器，推荐 GNU GCC。原版 bot 与圈地 bot 是不同程序，需要分别编译。
- 下载：使用 Git clone 或 GitHub 的 Code → Download ZIP。

macOS、Windows、Linux 的详细安装步骤见 [环境安装说明](../../land/play/README.md#1-安装需要的软件)。如果已为圈地安装 Python / GNU GCC，可直接复用。

```bash
git clone https://github.com/dmcdark/meow-ai-arena.git
cd meow-ai-arena
```

已下载则进入现有项目根目录；以下命令都在根目录执行。

## 2. 启动简单电脑对战

macOS / Linux：

```bash
python3 bomberman/play.py
```

Windows PowerShell：

```powershell
python bomberman/play.py
```

打开 <http://127.0.0.1:8767>，选择“简单电脑”，点击“开始新对局”，按空格开始。

默认端口与圈地不同，可同时开启两个服务。保持启动终端运行；Ctrl+C 停止。端口被占用时用 `--port 8768` 并打开终端输出的新地址。不要双击 HTML 文件，也不能通过 GitHub Pages 直接运行 Python/C++ 游戏服务。

## 3. 操作与规则

| 操作 | 按键 / 页面按钮 |
| --- | --- |
| 移动 | 方向键 / WASD；按住连续走，松开停留，快速点按预约走一格 |
| 放炸弹 | E 或“放炸弹”按钮，预约下一回合放弹；执行前再次按 E / 点击可取消 |
| 暂停 / 继续 | 空格或“暂停 / 继续”按钮 |
| 逐回合 | 暂停时点击“走一回合”；先点方向预约一步，再执行；没有方向输入则等待 |
| 调速 | 1、2、4 回合/秒 |
| 重开 / 换对手 | 选择对手或地图种子后，点击“开始新对局” |

触屏方向按钮支持按住移动和点按走一格。设置或点击按钮后焦点回棋盘；地图种子编辑完按 Enter 或离开输入框也会回棋盘。切换到后台或离开窗口会暂停并清除按键；已提交的一个回合可能仍会完成。

与圈地不同，方向可以直接反向，也不会自动一直往前走。按 E 只预约一次放弹，不会持续放。放弹与移动可以在同回合执行：**先在移动前位置放弹，再移动**。已经提交的回合无法取消，其后输入用于下一回合。

- 单挑棋盘 13×13。墙不可破坏，箱子可炸毁。
- 每人最多 2 颗炸弹在场；4 回合后引爆，十字射程 3 格；墙、箱子和其他炸弹会阻挡射线，炸弹可连锁引爆。
- 火焰在爆炸回合和下一回合都有效。炸弹上的数字是距离引爆行动回合数；数字 0 表示下一步结算时引爆。
- 被火焰击中或站在新缩圈墙上会淘汰，没有复活。碰墙或箱子时原地停留，不会因此淘汰。
- 行动回合 150 首次缩圈，此后每 20 回合缩一层；最多 300 回合。缩圈先于移动，不能在被覆盖的同回合才逃出。
- 存活人数不超过 1 或到达上限时结束。按原规则的“生存分 + 0.5 × 击杀份额”判胜，不单纯按最后存活者判胜。

简单电脑会尝试靠近箱子 / 对手、放弹和寻找逃生路线。它使用原引擎预测已有炸弹的爆炸、连锁和缩圈，但不预测你未来的移动或新放的炸弹，是入门策略，不保证总能避险。

## 4. 编译原版 AI bot

启动网页服务不会编译。请另开终端，在项目根目录显式编译；可以先只编译一个对手。

查看 ID：

```bash
python3 bomberman/play.py --list-bots
```

### macOS

如果尚未安装 GNU GCC：

```bash
brew install gcc
```

安装 Homebrew 等前置步骤见第 1 节链接。查找实际 GNU 编译器：

```bash
find /opt/homebrew/bin /usr/local/bin -name 'g++-[0-9]*' 2>/dev/null
```

假设找到 `/opt/homebrew/bin/g++-15`，在当前终端设置并编译（路径与版本须换成实际值）：

```bash
export CXX=/opt/homebrew/bin/g++-15
python3 bomberman/play.py --prepare-bots gpt-6-astra
```

Astra 和多数 bot 使用标准头文件，也可尝试已有的 Apple Clang：

```bash
CXX=clang++ python3 bomberman/play.py --prepare-bots gpt-6-astra
```

Opus 和 DeepSeek 使用 `bits/stdc++.h`，应使用 GNU GCC/libstdc++。无需改动封存的 bot 源码。

### Linux

安装支持 C++20 的 GNU GCC 后：

```bash
CXX=g++ python3 bomberman/play.py --prepare-bots gpt-6-astra
```

### Windows PowerShell

将 w64devkit 放到仓库 `tools/w64devkit/`，指定其编译器：

```powershell
$env:CXX = (Resolve-Path '.\tools\w64devkit\bin\g++.exe').Path
python bomberman/play.py --prepare-bots gpt-6-astra
```

如果放在别处，把路径换成实际 `g++.exe` 路径。如果 Python 命令是 `py`，将 `python` 替换为 `py`。

### 一次编译全部对手

设置好 `CXX` 后，在同一个终端执行这一行；Windows 将 `python3` 换为 `python`：

```bash
python3 bomberman/play.py --prepare-bots gpt-6-astra opus-5.5 gpt-6-sol deepseek-v4.1-flash kimi-k3 qwen-3.8-max glm-5.3 doubao-seed-2.1 mimo-v2.6-pro baseline
```

`baseline` 是项目提供的 C++ 基准；“简单电脑”是网页服务内置的 Python 策略，两者不同。编译产物存放在 `bomberman/.build/human-play/`，Git 会忽略它。

## 5. 选择 bot 开始游戏

编译成功后，启动服务（已经启动则保持运行），**刷新网页**。在对手菜单选择名称不带“未编译”的 bot，开始新对局即可。未编译选项会提示对应命令，不会自动触发编译。

原版 bot 使用正式协议和时限：首回合 2000ms，此后每回合 50ms。任何一次超时、退出或无效回复即淘汰，仍由原引擎完整结算该回合，可能与其他玩家同回合淘汰。暂停不请求 bot 下一步；利用真实时间决策的 bot，慢速手动对战表现可能与自动赛不同。

## 常见问题

- 网页无法连接：确认服务运行，打开终端输出的本地地址。炸弹人默认是 **8767**，圈地是 **8765**。
- bot 找不到 `bits/stdc++.h`：使用 GNU GCC，并确认 `CXX` 指向 GNU 编译器。
- 仍显示未编译：检查编译是否成功，编译和服务是否使用同一项目目录，刷新页面。
- 炸弹没有放下：请求在下一回合执行；脚下已有炸弹或容量已满时，原规则会拒绝放置。暂停时先预约，再走一回合。
- 回合不同步 / 对局过期：每个服务只支持一个游戏标签页和一局；开始新局替换旧局，闲置十分钟后清理。

服务只监听本机 `127.0.0.1`，用于本地游戏；本版仅支持人类与一个电脑单挑。
