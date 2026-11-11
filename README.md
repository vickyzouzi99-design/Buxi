# 卜犀 Buxi · 0.3 绯月阅读内测

当前功能与边界见 **[交付报告](docs/feiyue-delivery.md)**；真实检查见 **[验证记录](docs/validation-v03.md)**。已接入中文资料、引用展示、结果关联会话、刷新恢复和幂等重试。真实模型API已测试，桌面／手机浏览器仍待验收，不宣称全部验收通过。

默认资料为 `Buxi_Tarot_Knowledge_v01` 中 `0.1.0-2026-11-10` 的反思式编辑初稿，**待人工专业审核**。Tarotoo原始资料保留，旧结果不混入新版牌义。首次新启动会备份旧数据库后做增量迁移；资料包目录必须随应用保留。

本包包含预构建网页。先读 **LOCAL_RUN.md**，保留 `.env` 和旧数据库并按说明导入。不要覆盖唯一旧副本。

## 已实现

- 内测码登录、HttpOnly 会话、按账号隔离结果/记忆/聊天，CLI 创建独立内测码。
- 78 张塔罗牌：随机选一张并移除，单牌、三牌、现状/阻碍/建议；可关闭逆位。同一请求重试不重抽。
- 78张中文项目反思资料与可追溯英文依据，历史摘要与改写分开；Tarotoo独立保留用于旧结果，不与新默认牌义混用。
- 翻牌动画、12 条原创反思签文与摇签动画。星盘/易经标为准备中。
- 三位 AI 朋友独立私聊，用户选择将本次结果交给哪位朋友。
- 确认、编辑、停用、删除记忆；删除时向量一起移除。保存记录不等于授权记忆或训练。
- 公共资料按ID精确读取，一般专业问题用名称／别名／关键词检索。个人记忆保留sqlite-vec词面检索与可选语义embedding，按账号、朋友、启用状态及向量版本过滤。
- 可选进站问候，每天一次，可关闭；使用编辑文案，不读取私事，不是自主回访 Agent，无站外通知。
- 默认临时体验不加入长期记录，24小时后再次访问清理；可主动保存、导出和删除。
- 全站魔法手册主题：奶油羊皮纸、灰紫、旧金色和原创花卉星月牌背。聊天保留留白。
- 原对话修改：自然短回复、最近12条上下文、加粗显示、React 类型声明和 TypeScript 检查。

## 自行训练状态

`training/` 包含公开数据准备、按牌隔离的训练/验证集、LoRA训练及权重合并脚本。
**未执行 LoRA 训练，没有已训练权重。** 尚未选定基础模型与训练设备。样例仅用于跑通流程，不代表中文陪伴训练质量。用户数据库不参与自动训练。

## 结构

`server/app/tarot.py` 抽牌；`spreads.py` 牌阵；`policies.py` 解读规则；`personas.py` 角色；`rules.py` 原创签与兼容导出；`knowledge.py` 只读资料；`accounts.py` 身份／会话／记忆；`service.py` 结果／幂等／备份；`main.py` 认证API；`web/src` 前端；`web/public/assets/card-back.png` 原创牌背；`scripts/admin.py` 内测码／旧数据与向量索引维护。

## 检查

```sh
python -m pip install -r server/requirements-dev.txt
python -m unittest discover -s tests -v
cd web
npm install
npm run typecheck
npm run build
```

当前结果见 `docs/validation-v03.md`；`docs/validation.md` 是历史0.2记录。未配置真实模型时不会伪造AI回复。

## 外部来源

- https://github.com/jeremytarling/python-tarot ：参考随机索引取牌并移除的方法，自行实现。
- https://github.com/Tarotoo-com/tarotoo-tarot-dataset ：MIT 数据，附许可。
- https://github.com/infomofo/ts-tarot-cards ：参考牌/花色/牌阵类型分离，自行定义类型。

固定修订号见 `server/app/data/sources.json`。没有复制参考截图中的角色或卡牌图。
