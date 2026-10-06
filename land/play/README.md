# 手动圈地：用键盘与电脑对战

在浏览器里控制蓝色玩家，与橙色电脑对战。游戏复用原项目的圈地规则引擎，支持内置简单电脑策略和参赛模型写出的原版 C++ bot。无需大模型账号、API Key 或 API 费用。

## 1. 安装需要的软件

| 用途 | 必需软件 |
| --- | --- |
| 与简单电脑对战 | Python 3.10+、现代浏览器 |
| 与原版 AI bot 对战 | 上述软件，加支持 C++20 的编译器；推荐 GNU GCC |
| 下载代码 | Git，或直接下载 GitHub ZIP |

不需要 Node.js，也不需要 `pip install` 任何包。

### macOS

如果已安装 Python，先执行 `python3 --version`，确认至少为 3.10；已有软件可跳过安装。

若使用 Homebrew，先按 [Homebrew 官方安装说明](https://docs.brew.sh/Installation)安装，并按安装结束的提示配置 PATH。然后在终端执行：

```bash
brew install python git
```

只玩简单电脑，到这里即可。想编译所有原版 bot，再执行：

```bash
brew install gcc
```

Mac 的系统 `g++` 通常是 Apple Clang。多数原版 bot 使用 GNU 的 `bits/stdc++.h`，应指定 Homebrew 安装的 GNU 编译器，不能只凭命令名 `g++` 判断。参见 [GCC 头文件说明](https://gcc.gnu.org/onlinedocs/libstdc++/manual/using_headers.html)。

也可以从 [Python 官网](https://www.python.org/downloads/macos/)安装 Python；简单电脑模式不要求安装 Homebrew。

### Windows

1. 从 [Python 官网](https://www.python.org/downloads/windows/)安装 Python，确认终端执行 `python --version` 或 `py --version` 能找到 Python 3.10+。下文用 `python`；如果你的命令是 `py`，将命令中的 `python` 换为 `py`。
2. 需要用 Git 下载时安装 [Git for Windows](https://git-scm.com/downloads/win)，否则可以用 ZIP。
3. 只玩简单电脑无需编译器。需要原版 bot 时，从 [w64devkit 官方 Releases](https://github.com/skeeto/w64devkit/releases)下载适合电脑的版本，解压后将整个目录放到仓库的 `tools/w64devkit/`，确认里面有 `bin/g++.exe`。这是包含 GNU C++ 编译器的工具包。

下面的 Windows 命令使用 PowerShell。这里的手动对战服务不会自动寻找 `tools/` 下的编译器，因此编译前需要显式设置 `CXX`。

### Ubuntu / Debian

只玩简单电脑：

```bash
sudo apt update
sudo apt install python3 git
```

需要编译原版 bot，再安装：

```bash
sudo apt install build-essential
```

用 `python3 --version` 确认至少为 3.10，用 `g++ --version` 确认编译器支持 C++20；较旧系统可能需要先升级软件。其他 Linux 发行版使用自己的包管理器安装 Python、Git 和 GNU GCC。

## 2. 下载项目

终端执行：

```bash
git clone https://github.com/dmcdark/meow-ai-arena.git
cd meow-ai-arena
```

也可以在仓库页面点击 **Code → Download ZIP**，解压后用终端进入解压出来的项目根目录。根目录中应能看到 `land` 文件夹。

如果已经下载，直接进入已有目录，无需再次 clone。例如本机按之前指定路径下载的项目：

```bash
cd ~/Procject/meow-ai-arena
```

以下所有命令均在项目根目录执行。

## 3. 启动网页，先玩简单电脑

macOS / Linux：

```bash
python3 land/play.py
```

Windows PowerShell：

```powershell
python land/play.py
```

终端显示本地地址后，打开浏览器访问：

<http://127.0.0.1:8765>

保持这个终端运行。关闭终端或按 Ctrl+C 会停止服务。不要直接双击 `land/play/index.html`：这个网页需要连接 Python 服务；GitHub 的 HTML 预览和 GitHub Pages 也不能运行这套 Python/C++ 服务。

1. 对手选择“简单电脑”。
2. 地图种子保持默认，或输入一个 0 到 2147483647 的整数。
3. 点击“开始新对局”。初始状态暂停，先看自己的位置和朝向。
4. 用方向键或 WASD 选择方向，按空格或点击“继续”开始。

### 如何操作与获胜

- 你是蓝色，电脑是橙色。方向键 / WASD 转向，不能直接掉头；没有新输入就继续向前。
- 从自己的领地出发画线，回到领地后，轨迹和圈住的区域成为你的领地。
- 撞墙、撞头或自己的轨迹被踩到会阵亡；回出生点，已有领地保留。
- 棋盘 40×40，600 回合后按领地格数判胜。出生点 3×3 区域受保护。
- 空格暂停 / 继续；“走一回合”方便练习；速度可选 2、4、8 回合/秒。
- 触屏可以点击方向按钮。选择对手、速度或点击游戏按钮后，焦点会回到棋盘；地图种子输入完按 Enter 或离开输入框也会回到棋盘。
- 切换到后台或离开浏览器窗口时自动暂停，已提交的一个回合可能仍会完成。
- 同一地图种子产生相同出生位置。选择对手或修改种子后，点击“开始新对局”才会应用到新对局。
- 每个服务同时维护一局，请只用一个游戏标签页。新对局会替换旧对局；闲置十分钟会清理，再操作需要重新开始。

## 4. 编译原版 AI bot

简单电脑无需这一节。原版 bot 是模型事先写好的程序，运行在本机，并不会实时向大模型提问。

**编译是单独的显式操作。启动服务、刷新网页或选择对手都不会自动编译。** 可以在另一个终端中编译，原服务继续运行。

查看所有 bot ID（macOS / Linux）：

```bash
python3 land/play.py --list-bots
```

Windows 将 `python3` 换成 `python`。ID 中的 `#` 要保留在引号内，避免被终端当成注释。

### macOS：指定 GNU GCC

安装 `brew install gcc` 后，查找实际的编译器文件名：

```bash
find /opt/homebrew/bin /usr/local/bin -name 'g++-[0-9]*' 2>/dev/null
```

例如输出 `/opt/homebrew/bin/g++-15`，先设置：

```bash
export CXX=/opt/homebrew/bin/g++-15
```

把路径替换成你实际找到的路径和版本，不要直接照抄 `15`。Apple Silicon 通常在 `/opt/homebrew/bin`，Intel Mac 通常在 `/usr/local/bin`。之后在同一个终端执行下方编译命令。

如果只想尝试 GPT-6 Astra，它使用标准 C++ 头文件，也可以用已安装的系统 Clang：

```bash
CXX=clang++ python3 land/play.py --prepare-bots 'gpt-6-astra@codex#1'
```

若 `clang++` 尚未安装，执行 `xcode-select --install` 并按提示安装 Apple Command Line Tools。其他使用 `bits/stdc++.h` 的 bot 应使用 GNU GCC。

### Linux：使用 GNU GCC

安装编译器后，在当前终端设置：

```bash
export CXX=g++
```

### macOS / Linux：编译一个或多个 bot

例如只编译 Sonnet：

```bash
python3 land/play.py --prepare-bots 'sonnet-5@claude-code#1'
```

或者一次编译全部九个参赛 bot 和两个基准对手：

```bash
python3 land/play.py --prepare-bots \
  'sonnet-5@claude-code#1' \
  'gpt-6-astra@codex#1' \
  'opus-5.5@claude-code#1' \
  'gpt-6-sol@codex#1' \
  'mimo-2.6-pro@zcode#1' \
  'kimi-k3@workbuddy#1' \
  'glm-5.3@workbuddy#1' \
  'mystery-model@zcode#1' \
  'deepseek-4.1f@workbuddy#1' \
  'anchor-greedy' \
  'anchor-random'
```

### Windows PowerShell：指定编译器并编译

如果按前面的说明放到了 `tools/w64devkit/`，在项目根目录执行：

```powershell
$env:CXX = (Resolve-Path '.\tools\w64devkit\bin\g++.exe').Path
python land/play.py --prepare-bots 'sonnet-5@claude-code#1'
```

如果工具包放在别处，将路径换成它的实际 `g++.exe` 路径。一次编译全部：

```powershell
python land/play.py --prepare-bots `
  'sonnet-5@claude-code#1' `
  'gpt-6-astra@codex#1' `
  'opus-5.5@claude-code#1' `
  'gpt-6-sol@codex#1' `
  'mimo-2.6-pro@zcode#1' `
  'kimi-k3@workbuddy#1' `
  'glm-5.3@workbuddy#1' `
  'mystery-model@zcode#1' `
  'deepseek-4.1f@workbuddy#1' `
  'anchor-greedy' `
  'anchor-random'
```

PowerShell 的续行符是反引号，反引号后不要加空格。也可以把命令写成一行。

### bot 名称对照

| 菜单 / 编译 ID | 对手 |
| --- | --- |
| `sonnet-5@claude-code#1` | Sonnet 5.5 |
| `gpt-6-astra@codex#1` | GPT-6 Astra |
| `opus-5.5@claude-code#1` | Opus 5.5 |
| `gpt-6-sol@codex#1` | GPT-6 Sol |
| `mimo-2.6-pro@zcode#1` | MiMo V2.6 Pro |
| `kimi-k3@workbuddy#1` | Kimi K3 |
| `glm-5.3@workbuddy#1` | GLM 5.3 |
| `mystery-model@zcode#1` | Spacebunny / MiniMax M3.1 Flash |
| `deepseek-4.1f@workbuddy#1` | DeepSeek V4.1 Flash |
| `anchor-greedy` | greedy 基准 |
| `anchor-random` | random 基准 |

## 5. 在网页选择已编译 bot

1. 等终端显示编译成功和可执行文件路径。编译产物位于 `land/.build/human-play/`，不会提交到 Git。
2. 如果服务未运行，按第 3 节启动；如果已经运行，只需刷新网页。
3. 对手菜单中找到编译好的 bot，其名称不再带“未编译”。
4. 点击“开始新对局”，选好方向，按空格开始。

服务使用原裁判通信协议和时限：首回合 2000ms，后续每回合 50ms，另有原裁判容差。双方行动同时交给原引擎结算。bot 崩溃或累计十次超时 / 无效回复会判负。暂停不推进回合，也不请求 bot 的下一步；利用真实时间决策的 bot，在慢速手动对战中的效果可能与正式自动赛略有差异。

## 6. 常见问题

| 情况 | 处理方法 |
| --- | --- |
| `python3` / `python` 找不到 | 安装 Python，重新打开终端；Windows 可尝试 `py` |
| 网页打不开 / 连接失败 | 确认启动命令仍在运行，用浏览器访问它输出的 `http://127.0.0.1:…` 地址 |
| 8765 端口被占用 | 用 `python3 land/play.py --port 8766`，访问 <http://127.0.0.1:8766>；Windows 用 `python` |
| `g++` 找不到 | 安装编译器，按第 4 节配置 `CXX` |
| `bits/stdc++.h` 找不到 | 多数 bot 需要 GNU GCC/libstdc++；Mac 请使用 Homebrew 的版本化 GNU `g++` |
| 菜单仍显示“未编译” | 确认编译成功，且编译与服务使用同一个项目目录；刷新网页 |
| bot 编译报错 | 检查完整错误输出，确认编译器支持 C++20；服务不会隐藏编译错误 |
| 对局过期 / 回合不同步 | 只保留一个游戏标签页，点击“开始新对局” |
| 方向键操作了页面控件 | 完成选择或种子编辑后会回到棋盘；也可点击棋盘后操作 |

服务仅监听本机 `127.0.0.1`，用于本地游戏。不要把这个启动方式用作公网部署。

## 7. 向原项目提交 Pull Request

这一功能涉及 `land/play.py`、`land/play/` 和 README 入口，提交时需要一起包含这些文件。不要提交 `.build` 编译产物。

在 fork 创建功能分支、提交并推送（如果已有对应分支和提交，无需重复）：

```bash
git switch -c human-play
git add README.md land/README.md land/play.py land/play/index.html land/play/README.md
git commit -m "Add browser-based human vs computer land game"
git push -u origin human-play
```

到原仓库的 [Pull Requests 页面](https://github.com/chen-006/meow-ai-arena/pulls)，点击 **New pull request → compare across forks**，选择：

- **base repository**：`chen-006/meow-ai-arena`；**base**：`main`。
- **head repository**：你的 fork（例如 `dmcdark/meow-ai-arena`）；**compare**：`human-play`。

确认差异只有这次功能，然后填写标题、功能说明、安装 / 使用步骤链接和实际验证情况。没有运行过的测试或编译，应如实标注。可以先创建 Draft PR，再在验证后标记 ready for review。PR 是请求原作者审查并合并，是否合并由原项目维护者决定。

已有 GitHub CLI 且已登录的用户，也可以在推送后执行：

```bash
gh pr create --repo chen-006/meow-ai-arena --base main --head dmcdark:human-play --draft --title 'Add browser-based human vs computer land game' --body-file PR_BODY.md
```

`PR_BODY.md` 是你事先准备的说明文件，可放在项目之外，不必提交。参见 [GitHub 官方：从 fork 创建 PR](https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request-from-a-fork)。
