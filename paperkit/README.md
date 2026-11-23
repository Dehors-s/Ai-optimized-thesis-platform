# paperkit v1.1

论文项目的脚手架与检查器。**四方向只是 engineering 类型的一个示例分解，不是产品模板。**

```bash
# 素材少：只要结构（模板稿，不可投稿）
py tools/paperkit.py new --name "开题草稿" --dir projects/x1 \
  --type empirical --mode template --journal 测绘学报 --language zh

# 有数据：项目稿（必须绑定创新点）
py tools/paperkit.py new --name "某遥感论文" --dir projects/x2 \
  --type engineering --mode project --journal 测绘学报 --language zh --discipline remote_sensing
# 然后按 prompts/p7-创新点提炼.md 填 innovation.md，再做 paper_ir

py tools/paperkit.py check --dir projects/x2
py tools/paperkit.py audit --text outputs/xxx.md            # 引用 + 修辞
py tools/paperkit.py audit --text outputs/xxx.md --online   # 逐条核验文献真伪
py tools/paperkit.py terms --text outputs/xxx.md
py tools/paperkit.py profiles

# 证据库（数字/表/图/负结果，正文用 [E-0001] 引用）
py tools/evidence_store.py add   --dir projects/x2 --type number --value 0.6584 \
  --unit macro-F1 --claim "重叠导致虚高" --source-kind experiment --source-ref run-a
py tools/evidence_store.py check --dir projects/x2

# 文献库（含知网人工粘贴）
py tools/ref_store.py import-gbt --dir projects/x2 --file projects/x2/refs/inbox.txt
py tools/ref_store.py check      --dir projects/x2
```

`check` 现在包含 14 节：结构、摘要语体、分节语体、术语、数字溯源、规则、创新点、
主张、参考文献、修辞、声明、**证据**、**文献库**、**数字反查**。后四节用于堵住
“引用没引、句子空转、没有 AI 声明、数字对不上台账”这四类问题（见 `docs/16`、`docs/17`）。

配套命令：

```bash
py tools/ref_support.py add  --dir projects/x --ref R-0001 --claim "C-02" --intent support
py tools/ref_store.py export --dir projects/x --apply   # 按首次出现重编号
py tools/facts_migrate.py --dir projects/x              # facts.md -> 台账
py tools/number_check.py  --dir projects/x              # 正文数字反查
```

## 画像注册表

`paperkit/profiles/registry.json` 按「期刊 × 语言 × 学科」查画像，解析顺序：

1. journal + language + discipline；
2. journal + language；
3. language 默认（`generic_zh_*`）；
4. 都没有 → 跳过语体检查，不阻断结构检查。

未知期刊第一次使用会退回通用画像，不会因为缺 `rs_*` 而无法工作。

## 配置驱动

`project.json` 决定章节、画像与规则，检查器不再写死章节编号：

```json
{
  "paper_type": "empirical",
  "profiles": {"abstract": "rs_abstract", "method": "rs_method", "results": "rs_results", "discussion": "rs_discussion"},
  "sections": [
    {"title": "摘要", "role": "abstract"},
    {"title": "1 引言", "role": "intro"},
    {"title": "4 方法", "role": "method", "profile": "rs_method"},
    {"title": "5 实验", "role": "results", "profile": "rs_results"}
  ],
  "decomposition": {"name": "按方法组件分解", "items": []},
  "rules": {"forbidden_phrases": ["优于", "纯自研"], "required_attribution": null, "required_statements": []}
}
```

检查器按 `sections[].title` 切分正文、按 `profile` 选画像、按 `rules` 跑红线。

## 目录约定

```
project/
├── project.json      章节/画像/规则配置
├── facts.md          数字唯一来源
├── paper_ir.json     thesis / claims / evidence / decomposition
├── outline.md        章节骨架 + 段落任务单
├── manuscript.md     正文
├── checks/report.md  检查报告
├── evidence/         证据库 evidence.jsonl（数字/表/图/负结果）
├── figures/spec/     图表规格
├── refs/refs.jsonl   文献库（编号顺序 = 正文引用顺序）
└── refs/inbox.txt    知网等导出文本的粘贴区
```

不做的事：不替人定 thesis、不替人判断方法是否新、不生成无法溯源的数字。
