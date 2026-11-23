# 双高 2026 · 论文项目

> 用 `paperkit` 的 project 模式重建：facts → outline → manuscript → checks → HTML。

## 产物

| 文件 | 内容 |
|---|---|
| `manuscript.md` | 正文（约 10,400 汉字；7 图、8 表） |
| `article.html` | 单文件 HTML（图表内嵌，直接打开） |
| `figures/fig2_framework.png` | 三层研究框架 |
| `figures/fig1_data.png` | 数据检查与漏斗 |
| `figures/fig3_probe.png` | 线上增量与噪声 |
| `figures/fig6_openset.png` | 开集判据与配额 |
| `figures/fig8_platform.png` | 配额曲线 |
| `figures/fig4_members.png` | 成员池架构 |
| `figures/fig7_attribution.png` | 配额收益 90/10 分解 |
| `facts.md` | 事实清单（所有数字的唯一来源） |
| `outline.md` | 章节骨架 |
| `paper_ir.json` | 论点、主张、证据 |
| `innovation.md` | 3 条创新点（作者接受） |
| `checks/report.md` | 自动检查报告 |

## 检查结果

- 结论：**通过**
- 摘要语体：76/100
- 分节语体：96 / 72 / 76 / 80 / 92 / 96
- 造词：0 次/千汉字
- 数字溯源：84 个数字，facts.md 缺失 0 个
- 规则：未命中禁用表述（优于/高于/纯自研/证明了/我方/队友）
- 参考文献：6 条，全部被正文引用
- 修辞：warn（对偶否定 1.75/千字，阈值 2；无证据句 27%）

## 已知警告

1. 摘要“的/百汉字”2.89，低于画像目标 3.39（warn，不影响通过）；
2. 摘要 >80 字句占 57%，高于 33.7%（warn）；
3. 中文文献 0 条（语料与归档文献均为英文）；
4. 部分数字在原文中标注“待核”，投稿前需逐条回台账；
5. P 侧 0.40 权重与 c4 族归属需合作方确认后再公开。

## 重新生成

```bash
py tools/check_project.py --dir projects/双高2026
py tools/md_to_html.py --md projects/双高2026/manuscript.md --out projects/双高2026/article.html
```

图由 `tools/make_dual_figs.py` 生成，输出到 `projects/双高2026/figures/`。
