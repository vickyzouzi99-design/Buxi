# 自行训练模型：LoRA 实验流程

> 2026-11-11：本轮只建立已有模型＋资料＋工具的评测基线，没有运行LoRA训练、下载基础模型或获取GPU。现有准备样例不等于已审核训练答案；用户聊天与记忆不自动进入训练集。真实样本与失败分析见 `docs/evaluations/review.md`，未来是否微调尚无充分证据。

这部分是可运行的训练入口，不是已完成训练的模型。当前环境没有训练用基础模型权重或 torch/transformers/peft，因此只验证了数据准备、数据分离和 Python 语法，未执行训练，也没有声称质量提升。

## 目标与数据

目标是让模型更稳定地依据资料解释、按牌位回答、保持简洁语气；不训练“预测命运准确率”。抽牌随机逻辑永远由程序执行，模型不挑牌。

`prepare.py` 从随包 Tarotoo 数据生成 156 条公开资料示例。按牌 ID 分组：66 张牌 / 132 条训练；12 张牌 / 24 条验证，正逆位不会分散到训练和验证两边。
这些是英文原文复述的流水线样例，不能代表中文陪伴、复杂解读或隐私行为的训练集。正式训练前需添加经过人工审核的中文问答、不同牌位、澄清提问和事实边界示例，并按场景隔离验证集。不要只把所有牌义背下来。
用户数据库完全不参与自动生成训练集；保存记忆不等于同意训练。

## 准备与启动

为训练使用独立 Python 环境。根据设备选择有权使用的、可在 transformers 中加载且带聊天模板的本地因果语言模型。先确认其许可、磁盘和显存需求。脚本使用 local_files_only=True，不会自动拉取大量模型文件。

```powershell
python -m pip install -r training\requirements.txt
python training\prepare.py
python training\train_lora.py --base-model C:\Models\your-chat-model --max-steps 2 --output training\smoke-output
```

两步训练仅检查流水线是否跑通，不是完成训练。正式实验去掉 `--max-steps 2`，指定审核后的 `--train` 与 `--eval` JSONL。
`train_lora.py` 只对 assistant 输出计算训练损失，屏蔽 prompt token，禁用实验跟踪上传。输出 LoRA adapter、tokenizer、验证损失及带数据哈希的训练清单。

```powershell
python training\merge_adapter.py --base-model C:\Models\your-chat-model --adapter training\output --output training\merged
```

合并后用支持该模型的 OpenAI-compatible 本地推理服务加载，把卜犀 `MODEL_BASE_URL` 指到它，例如本机 `http://127.0.0.1:8001/v1`；按该服务要求设置名称和密钥。现有 DeepSeek API 密钥不能用来训练 DeepSeek 托管模型的权重。

## 验收标准

比较基础模型与适配器在相同未见问题上的表现：牌/方向/牌位一致、引用资料准确、不编造经历、不过度确定、回答简洁、不同朋友语气区别。
验证损失只是语言建模指标，不是算命准确率。中文场景没有通过人工对照前不要替换默认模型。

来源：Hugging Face PEFT quicktour、Transformers Trainer 文档。依赖训练脚本采用 Transformers 4.x API；具体基础模型必须在选定版本中受支持。
