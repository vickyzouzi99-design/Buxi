# 卜犀 Buxi：本地运行与 GitHub 同步指南

**A little insight. A little company.**  
一点启发，一点陪伴。

更新：2026-11-07  
交付：M0/M1 本地开发版（不是四体系完整首版）

## 1. 先看这一段：最快启动

代码包已包含构建好的网页，无需先安装 Node.js、npm、FastAPI 或 Docker。
只需 Python 3.10 或以上。先不配置模型也可以用塔罗工具。

1. 解压 Buxi_Local_Starter.zip，进入其中的 Buxi 文件夹。
2. 确认此文件夹里有 start-local.bat、scripts、server、web。
3. 在此文件夹空白处右键，选择“在终端中打开”。
4. 输入：

```powershell
python --version
python scripts/local_preview.py
```

5. 保持终端打开，在浏览器访问：

**http://127.0.0.1:8080**

也可以直接双击 **start-local.bat** 启动，然后手动打开以上网址。
若 python 命令不可用，但已安装 Windows Python Launcher，可以试：

```powershell
py -3 scripts/local_preview.py
```

关闭服务：回到运行窗口按 Ctrl+C。关闭浏览器不会停止服务。

> 不要直接双击 web/dist/index.html。网页需要通过本地服务访问才能使用数据库和 API。

## 2. 第一次建议这样体验

1. 首页点击“抽一张牌”，或“探索 → 塔罗”。
2. 输入一个可选问题，选择一张牌或三张牌。
3. 点击“准备好了，抽牌”，再点击牌面揭晓。
4. 阅读本地反思提示；抽牌记录已经自动保存。
5. 进入“我的记录”，查看记录、导出 JSON，或删除记录。
6. 停止服务再启动，确认之前的记录仍在。

没有配置模型时，“请 AI 解读”和“找绯月聊聊”不能产生真实 AI 回答，
页面会明确提示需要配置。本地反思提示不会伪装成模型输出。

## 3. 当前可以做什么

| 功能 | 状态 |
| --- | --- |
| 首页、探索、朋友、记录页面 | 已实现 |
| 78 张牌、单牌和三牌、正逆位 | 已实现 |
| 翻牌、保存、再次查看 | 已实现 |
| 重试相同抽牌请求不会重抽 | 已实现并测试 |
| 本地反思提示 | 已实现，非 AI 输出 |
| AI 解读、绯月围绕牌阵聊天 | 接口已编写，需配置真实模型后验证 |
| 历史删除、数据导出 | 已实现并测试 |
| 星盘、易经、观音灵签 | 只有未开放入口，后续开发 |
| 今日星象和个性化运势 | 未实现，首页当前为编辑反思提示 |
| 独立私聊、用户自选群聊 | 未实现 |
| 长期记忆、回访、Agent 自主调用工具 | 未实现 |
| 账号、多用户和公网部署 | 未实现 |

这个阶段完成的是塔罗工具流程和本地基础架构。不要将其描述成完整 Agent 产品或正式上线版本。

## 4. 可选：配置真实 AI 解读与聊天

### 4.1 创建配置文件

在 Buxi 根目录执行：

```powershell
Copy-Item .env.example .env
notepad .env
```

填写：

```dotenv
MODEL_BASE_URL=https://你的模型服务地址/v1
MODEL_API_KEY=你自己的密钥
MODEL_NAME=供应商提供的准确模型ID
BUXI_DATA_DIR=./data
```

- 服务需支持 OpenAI-compatible 的 POST /chat/completions。
- MODEL_BASE_URL 填到 /v1 或供应商规定的兼容 API 基础路径，**不要填写完整 /chat/completions 地址**，程序会追加。
- 不同服务的路径规则可能不同，必须按实际供应商说明填写。
- MODEL_NAME 使用真实模型 ID，不是自己给模型起的名字。
- 当前请求包含 max_tokens 和 temperature，需要供应商支持这些字段。
- 本版未验证所有供应商的兼容性，也未做流式回复。
- 若系统已经设置同名环境变量，环境变量优先于 .env。
- .env 已被 .gitignore 排除，切勿上传截图或把密钥贴到 README。

保存后，在运行终端按 Ctrl+C，再执行：

```powershell
python scripts/local_preview.py
```

回到一条塔罗记录，点击“请 AI 解读”。失败时原牌阵保留，不会重抽。
“找绯月聊聊”会将当前问题、牌阵和最近对话发给所配置的模型服务。

### 4.2 关于费用与数据

模型调用费用由你的服务账户承担。未配置密钥时，本地抽牌不会产生模型费用。
数据默认保存在本机 SQLite 中，但调用远程模型时，选入请求的内容会发送给该服务。

## 5. 数据在哪里，怎样备份

默认目录：

- data/buxi.db：抽牌与关联聊天记录。
- .env：你的模型配置，不能公开。
- web/dist：已经构建的网页，删除后需要重新构建。

最简单的备份方式：

1. Ctrl+C 停止本地服务。
2. 复制整个 data 文件夹到你的备份位置。
3. 重新启动服务。

恢复时先停止服务，再用你的备份替换 data。不要在正在写数据库时随便复制单个数据库文件。
data 不会提交到 GitHub；导出的 JSON 可用于查看和迁移准备，本版还没有 JSON 导入功能。

## 6. 常见问题

| 现象 | 处理方式 |
| --- | --- |
| python 不是内部或外部命令 | 安装 Python 3.10+ 并勾选 PATH，或尝试 py -3 |
| 浏览器连接不上 | 检查终端是否仍在运行；地址必须是 http://127.0.0.1:8080 |
| 8080 端口已被占用 | 优先关闭你之前启动的卜犀窗口；不要随意结束不认识的进程 |
| 提示先构建网页 | 检查是否解压了完整包、web/dist 是否存在；需要重建时看第 7 节 |
| AI 尚未配置 | 检查 .env 文件名、MODEL_API_KEY 与 MODEL_NAME，重启服务 |
| 模型服务暂时不可用 | 检查基础地址、模型 ID、余额与服务兼容性；不会因此丢失原来的牌 |
| 改了源码但页面不变 | 先重新构建，再强制刷新浏览器 |
| 其他设备不能打开 | 这是预期行为，当前只监听本机，不支持公网或局域网多人访问 |

## 7. 修改前端后怎样重新构建

仅运行交付包时可以跳过这一步。开发前端时，建议安装 Node.js 22 LTS，然后：

```powershell
cd web
npm install
npm run build
cd ..
python scripts/local_preview.py
```

初次 npm install 需要网络。当前前端使用 React + TypeScript 源码和 esbuild 构建；
esbuild 只转译 TypeScript，不执行类型检查。此次未附带跨平台完整 lockfile，
应在正常网络环境安装后生成并提交 package-lock.json，后续切换到 npm ci。

本次环境使用旧版 Node 16 从已缓存依赖构建成功，但不是建议的正式开发环境。
依赖下载、升级和供应链检查需在正常开发环境继续完成。

## 8. 怎样自己同步到 GitHub

目标仓库：https://github.com/vickyzouzi99-design/Buxi.git

推荐使用 GitHub Desktop，减少命令行操作：

1. 安装并登录 GitHub Desktop。
2. File → Clone repository → URL，输入上面的地址。
3. 选择一个新的本地目录进行克隆。
4. 查看仓库已有文件；如果已经有代码，先比较，不要直接覆盖。
5. 将交付包 Buxi 文件夹内的源代码复制到克隆目录；本交付 ZIP 不包含 .git。
6. 保留仓库已有的 Git 历史，按需要合并已有 README 或其他文件。
7. 在 Changes 中检查修改，确认没有 .env、data、密钥或真实对话。
8. Commit to main（或你自己的开发分支），再 Push origin。

建议提交：

- server、web/src、scripts、tests、docs
- README.md、LOCAL_RUN.md、.env.example、.gitignore
- compose.yaml、Dockerfile、nginx.conf、构建配置

不要提交：

- .env、data、.venv、node_modules
- npm 缓存、运行日志、真实聊天和导出文件
- 开发环境临时文件

web/dist 在 .gitignore 中，GitHub 上的源码需要先 npm install 与 npm run build。
若希望别人无需 Node 即可体验，可以把此次 ZIP 或以后打好的本地包上传到 GitHub Release；
不要把数据库与密钥打包进去。

本次没有读取远端内容、没有推送到 GitHub，也没有创建线上网站。
不要使用 force push；如果 GitHub 仓库已有内容，优先保留并合并。

## 9. FastAPI 与 Docker 是后续开发路径

当前的一键本地运行使用 Python 标准库 HTTP 适配器，复用真实业务逻辑。
代码中同时提供 FastAPI API；由于开发环境无法安装 FastAPI/httpx，相关测试尚未执行。

安装后端依赖和运行 API：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r server/requirements-dev.txt
.\.venv\Scripts\python -m uvicorn server.app.main:app --host 127.0.0.1 --port 8000
```

API 文档：http://127.0.0.1:8000/docs

后续如果安装了 Docker，并已准备 .env：

```powershell
docker compose up --build -d
```

Compose 只绑定本机 8080，数据库使用持久卷。该路径当前未实际验证，
先使用第 1 节的本地运行方式即可。

## 10. 验证记录与后续顺序

本次：

- 前端生产构建成功，生成 index.html、main.js、main.css。
- 17 项测试中 15 项通过，2 项因缺少 FastAPI/httpx 跳过。
- 已通过本地 HTTP 测试：页面与资源返回、抽牌、重试去重、保存、导出、删除、未配置 AI 的错误提示。
- 已通过核心测试：78 张牌、无重复抽牌、正逆位、并发幂等、持久化、数据归属检查。
- 未进行浏览器视觉和点击自动化检查；未做真实模型调用；未做 Docker 和公网验证。

建议接下来先由你本地体验界面和塔罗流程，再修正体验细节，然后按完整方案推进
易经/灵签、星盘、群聊和记忆。详细产品方案在 docs/plan.md。
