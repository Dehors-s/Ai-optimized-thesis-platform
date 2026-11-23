# paper-figure-pipeline

面向中文工程论文的“论证 + 图表”流水线：把论文拆成事实台账、章节骨架、主张与证据，再用可复用的面板模板、拼装器和 lint 生成图表。

当前仓库包含两层能力：

1. **论文流水线**：`facts.md → outline.md → paper_ir.json → manuscript.md → checks/`
2. **图表流水线**：`paneltemplates → panelkit → layout lint → SVG 架构图`

---

## 当前样例：双高 2026 论文

`projects/双高2026/` 是一次完整跑通的样例：

- 正文 `manuscript.md`：约 10,400 汉字，8 图、8 表；
- `article.html`：可直接打开的单文件 HTML；
- `checks/report.md`：自动检查 **通过**（摘要语体 76、分节 72—96、造词 0/千字、数字溯源 84/84）；
- `figures/fig5_snmsu.png`：SN-MSU 架构图（SVG 源 + 3D 特征块 + 模块放大）。

论文主题：高光谱双高遥感影像精细分类的流程化实践。四条主线：数据样本分析、数据预处理、异构模型骨干、训练后处理。

---

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 检查论文项目
python tools/check_project.py --dir projects/双高2026

# 生成 HTML
python tools/md_to_html.py --md projects/双高2026/manuscript.md --out projects/双高2026/article.html

# 图表模板 lint
python tools/template_lint.py --all

# 拼装层 lint / 渲染
python tools/panelkit.py lint --layout figures/repro/MTDL_layout.json
python tools/panelkit.py compose --layout figures/repro/MTDL_layout.json --out figures/repro/MTDL_panelkit

# SN-MSU 架构图（SVG → PNG）
python tools/make_snmsu_svg.py
```

> `make_snmsu_svg.py` 用无头 Edge 渲染，Windows 默认路径为
> `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`；其他平台可改成 Chrome/Chromium。

---

## 目录

| 路径 | 内容 |
|---|---|
| `docs/` | 方法论：语体标定、证据库、引用、图表语法、复刻、部件化、经验台账、顶刊差距 |
| `projects/双高2026/` | 当前论文项目：facts / outline / IR / manuscript / figures / checks |
| `tools/` | 论文检查、图表模板、拼装、lint、SVG 架构图、语料统计 |
| `paperkit/` | 模板、画像注册表、版式模板 JSON |
| `prompts/` | 立骨、搭架、行文、精修、成图、审稿等提示词 |
| `assets/icons/` | Tabler 图标（MIT），用于架构图 |
| `figures/repro/` | 复刻与模板验收的示例产物 |
| `spec/` | PaperIR schema |

---

## 设计原则

- **数字只有一个来源**：正文数字必须能在 `facts.md` 找到；
- **正文与图表分离**：图先按“文章角色”选型，再选模板；
- **部件化**：复合图 = 语义部件 × 拼装，不让一张图写 400 行；
- **可检查**：模板 lint、拼装 lint、语体检查、数字溯源、引用核验；
- **不夸大**：不宣称优于对照、不把缺陷利用写成方法创新、不编造文献。

---

## 仓库边界

本仓库**不包含**：

- 竞赛原始影像、标注、权重（数百 GB）；
- P 侧/合作方的模型权重与私有数据；
- 未公开的论文投稿文件。

只保留可复现的代码、事实台账、正文、图表脚本与检查报告。

---

## 路线图

- [x] 论文项目流水线与检查
- [x] 面板模板 + 拼装 + lint
- [x] 研究框架图、成员池图、SN-MSU 架构图
- [ ] 研究区/数据覆盖图（需坐标）
- [ ] 定性分类结果图（需分类栅格）
- [ ] SOTA 对比与显著性检验（需重训基线）
- [ ] DOCX/PDF 投稿排版
