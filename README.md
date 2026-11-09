# 卜犀 Buxi · 0.2 私密内测版

本包包含预构建网页。先读 **LOCAL_RUN.md**，保留 `.env` 和旧数据库并按说明导入。不要覆盖唯一旧副本。

## 已实现

- 内测码登录、HttpOnly 会话、按账号隔离结果/记忆/聊天，CLI 创建独立内测码。
- 78 张塔罗牌：随机选一张并移除，单牌、三牌、现状/阻碍/建议；可关闭逆位。同一请求重试不重抽。
- Tarotoo 完整逐牌正逆位资料，中文牌名、英文原文及来源版本；AI 依据资料进行中文解读。未声称已完成人工中文译校。
- 翻牌动画、12 条原创反思签文与摇签动画。星盘/易经标为准备中。
- 三位 AI 朋友独立私聊，用户选择将本次结果交给哪位朋友。
- 确认、编辑、停用、删除记忆；删除时向量一起移除。保存记录不等于授权记忆或训练。
- sqlite-vec 余弦检索，公共知识和个人记忆分表；默认本地词面向量，可配置外部语义 embedding。按账号、朋友、启用状态和向量版本过滤候选。
- 可选进站问候，每天一次，可关闭；使用编辑文案，不读取私事，不是自主回访 Agent，无站外通知。
- 默认临时体验不加入长期记录，24小时后再次访问清理；可主动保存、导出和删除。
- 全站魔法手册主题：奶油羊皮纸、灰紫、旧金色和原创花卉星月牌背。聊天保留留白。
- 原对话修改：自然短回复、最近12条上下文、加粗显示、React 类型声明和 TypeScript 检查。

## 自行训练状态

`training/` 包含公开数据准备、按牌隔离的训练/验证集、LoRA训练及权重合并脚本。
**未执行 LoRA 训练，没有已训练权重。** 尚未选定基础模型与训练设备。样例仅用于跑通流程，不代表中文陪伴训练质量。用户数据库不参与自动训练。

## 结构

`server/app/tarot.py` 抽牌；`rules.py` 牌阵/解读/朋友/签文；`data/tarotoo.json` 固定资料；`accounts.py` 身份/记忆/向量检索；`vectors.py` 向量生成；`main.py` 统一认证API；`web/src` 前端；`web/public/assets/card-back.png` 原创牌背；`scripts/admin.py` 内测码/旧记录导入/重建索引。

## 检查

```sh
python -m pip install -r server/requirements-dev.txt
python -m unittest discover -s tests -v
cd web
npm install
npm run typecheck
npm run build
```

实际结果见 `docs/validation.md`；未配置真实模型时不会伪造AI回复。

## 外部来源

- https://github.com/jeremytarling/python-tarot ：参考随机索引取牌并移除的方法，自行实现。
- https://github.com/Tarotoo-com/tarotoo-tarot-dataset ：MIT 数据，附许可。
- https://github.com/infomofo/ts-tarot-cards ：参考牌/花色/牌阵类型分离，自行定义类型。

固定修订号见 `server/app/data/sources.json`。没有复制参考截图中的角色或卡牌图。
