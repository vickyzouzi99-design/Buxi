# 卜犀 Buxi

**A little insight. A little company.**  
一点启发，一点陪伴。

看盘、抽牌、起卦、摇签，也找朋友聊聊。

## 本地运行

如果使用带 web/dist 的本地交付 ZIP，安装 Python 3.10+ 后即可：

```powershell
python scripts/local_preview.py
```

打开 **http://127.0.0.1:8080**。也可双击 start-local.bat。
不需要先配置 AI、不需要 Docker。详细步骤见 [LOCAL_RUN.md](LOCAL_RUN.md)。

从 GitHub 只获取源代码时，先用 Node.js 22 构建前端：

```powershell
cd web
npm install
npm run build
cd ..
python scripts/local_preview.py
```

## 当前状态：M0 / M1 本地开发版

已实现：响应式页面、78 张塔罗牌、单牌/三牌、正逆位、翻牌、
SQLite 存档、历史查看/删除/导出、幂等请求、服务端模型适配与绯月对话接口。

未配置模型时显示“本地反思提示”，不伪装成 AI。
真实模型调用尚未验证。将 .env.example 复制成 .env，填入供应商基础地址、密钥和模型 ID，
重启服务可尝试 AI 解读。远程模型会接收到当前问题、牌阵与最近对话。

尚未开放：星盘、易经、灵签、真实今日运势、每日一牌规则、
独立私聊、群聊、长期记忆、流式输出和自主调用工具的 Agent。
本版不含账号和多用户隔离，服务只能本机运行。

## 项目结构

| 目录 | 内容 |
| --- | --- |
| web/src | React + TypeScript 界面 |
| server/app | 抽牌、数据库、模型适配、FastAPI API |
| scripts/local_preview.py | 无第三方依赖的本地 HTTP 适配器 |
| tests | 核心、HTTP、FastAPI 测试 |
| docs/plan.md | 完整产品方案 |
| docs/validation.md | 验证结果与限制 |

构建采用 esbuild，当前未执行 TypeScript 类型检查。
FastAPI 为后端目标，标准库服务仅用于本地开发；两者复用相同业务服务。
SQLite v1 启动时初始化，后续演进需引入正式迁移管理。

## 测试与容器

```powershell
python -m unittest discover -s tests -v
```

17 项中 15 通过；2 项因缺少 FastAPI/httpx 跳过。
安装 server/requirements-dev.txt 后可运行 FastAPI 测试。

Compose/Dockerfile 已编写但未实测。见本地指南第 9 节。
不要将当前没有认证的本地版暴露公网。

## 内容与许可

牌面为原创装饰图形，未使用第三方塔罗插画；牌名为传统名称，反思短句为项目编辑内容。
尚未导入易经/签本数据或星历依赖，项目最终许可证待核实依赖后确定。
React 等第三方组件保留其原许可证；不对第三方代码主张所有权。

## GitHub

目标：https://github.com/vickyzouzi99-design/Buxi.git

当前远程连接受限，未读取、推送或覆盖仓库。用户可按 LOCAL_RUN.md 自行同步。
web/dist 不提交 Git，但可随无密钥/无数据的本地 Release 包分发。
