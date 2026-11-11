# 卜犀 0.3 · 本地升级与启动

先读 **[本轮启动、迁移恢复与验收步骤](docs/run-v03.md)**。现有目录可直接运行：

```powershell
cd C:\Buxi
.\.venv\Scripts\python.exe scripts\local_preview.py
```

先关闭旧版服务，再启动。打开 http://127.0.0.1:8080 ，继续使用原内测码；无需重写`.env`。保留整个资料包目录，前端已在本机重建。以下旧版部署背景继续有效，知识检索与迁移行为以本轮文档为准。

本包包含构建好的网页，不修改前端就不必安装 Node。Python 3.10+。

## 保留旧数据

1. 关闭旧版窗口，完整复制原 `C:\Buxi` 为备份。
2. 将本包解压为新的目录，例如 `C:\Buxi_v02`，不要直接覆盖唯一的旧副本。
3. 复制旧目录中的 `.env` 与 `data` 到新目录。不要把 API Key 发给别人。
4. 检查 `.env` 的 `BUXI_DATA_DIR`：指向复制后的数据目录；推荐 `./data`。
5. 以下命令均在新目录的 PowerShell 中执行。

```powershell
cd C:\Buxi_v02
python -m pip install -r server\requirements.txt
python scripts\admin.py --create-codes 1
```

终端打印的随机字符串就是你的内测码。请保存；同一码代表同一账号，不要多人共用。

如果有旧版抽牌记录，执行一次并输入自己的内测码，把原 `local` 记录分配给自己：

```powershell
python scripts\admin.py --import-local
```

随后启动：

```powershell
python scripts\local_preview.py
```

打开 http://127.0.0.1:8080 ，输入内测码。也可双击 `start-local.bat`。
要给其他内测者创建独立身份，运行 `python scripts\admin.py --create-codes 5`。
本地地址仅本机可用；这一步不会自动把网站发布到互联网。

## AI 配置

保留你原来可用的 `MODEL_BASE_URL`、`MODEL_API_KEY`、`MODEL_NAME`。
示例采用 DeepSeek 地址，但不硬编码未经账号验证的模型名称。
更改 `.env` 后重启。未配置 AI 时，抽牌、摇签、牌义原文、记忆管理仍可用；AI 解读和消息发送禁用。
发起 AI 解读/聊天时，所选结果、最近消息和授权给该朋友的相关记忆会发送到配置的模型服务。

## 向量库

个人记忆使用 sqlite-vec，默认本地字符向量，不收费、不下载模型；它是词面相似检索，不能当成跨语言语义检索。0.3公共专业检索使用只读文件中的名称与关键词，无启动时embedding构建。
要启用语义检索，配置 OpenAI-compatible embeddings 的 `EMBEDDING_BASE_URL`（包含所需 /v1）、`EMBEDDING_API_KEY`、`EMBEDDING_MODEL`。
这会把待检索文本和明确保存的记忆发送到配置的 embedding 服务。初始化/重建公开资料索引会产生 embedding 请求。
更换 embedding 服务/模型后先重建，再重启：

```powershell
python scripts\admin.py --reindex
```

不匹配的旧向量版本不会混用。用户删除记忆时同一行中的向量一起删除；已生成的聊天需要在聊天页单独删除。

## 修改前端时

推荐按package.json使用Node 22或更高。本轮Windows的Node 16.14.0在补齐固定依赖后实际通过类型检查和构建，但npm仍有engine不匹配提示，不作为受支持版本。运行预构建网页不需要Node。

```powershell
cd web
npm.cmd install
npm.cmd run typecheck
npm.cmd run build
```

## 自行训练

参见 `training/README.md`。本包含数据准备、分组验证集、LoRA 训练及权重合并脚本，**没有已训练权重**。
模型训练不是启动网站的前置条件。不要把用户聊天/记忆当成默认训练数据。

## 远程内测部署

当前是本地可运行内测版本，并非已经上线的生产服务。公开部署需 HTTPS、正确配置 `BUXI_ALLOWED_HOSTS`、`BUXI_ALLOWED_ORIGINS`、`BUXI_SECURE_COOKIE=1`，并在反向代理配置登录限流和备份。服务内的登录限流仅在单进程内生效。所有内测者连接同一个部署，使用各自独立内测码。
