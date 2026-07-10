# 显明易说 LightRAG 多方法图谱试验

- HTML: `C:\html\xianmingyishuo-graph-browser\index.html`
- JSON: `C:\html\xianmingyishuo-graph-browser\graph-data.json`
- Source GraphML: `F:\codex\runtime\lightrag-xianmingyishuo-rebuild\stable-openrouter-final\graph_chunk_entity_relation.graphml`
- Sidecar summary: `F:\codex\reports\workflow-runs\2026-06-09-xianmingyishuo-lightrag-rebuild\sidecar-index-summary.json`
- Generated at: `2026-06-18T05:48:25+08:00`

## 全量校验

- 实体节点: 3641
- 关系边: 2884
- 自动社群: 1280
- 连通分量: 1086
- 源文档: 150
- 文本块: 495
- warning chunks: 14
- quality flags: 18

## 方法横向结论

- 社群岛屿图: 推荐作为主图谱；适合 分类、查漏补缺、发现材料簇；限制：小社群会分散在外围，需要配合搜索透镜
- 主干骨架图: 推荐作为第二视图；适合 看核心概念链、中心人物/平台/主题关系；限制：不如社群图适合做细分类
- K-core 核心层图: 适合判断材料主干层级；适合 区分稳定核心概念、次核心主题和边缘材料；限制：核心层不直接等于内容主题，需要和社群图一起看
- PageRank 中心图: 适合挑关键入口节点；适合 找被多条重要关系指向的中心实体；限制：中心性高不一定代表内容分类价值高
- 全量核心-外围图: 适合总览；适合 判断中心与边缘、发现高 PageRank 实体；限制：外围节点多时会显得拥挤
- 关系矩阵图: 适合审计和异常发现；适合 看类型/社群之间哪里关系最密、哪里可能抽取异常；限制：不能直接阅读单个节点语义
- 类型环带图: 适合质量检查；适合 检查实体类型分布和类型间关系；限制：按类型而非内容聚类，分类价值弱于社群图
- 搜索邻域透镜: 适合精读时逐主题推进；适合 围绕 AI、健康、财富、预测等主题追材料链；限制：依赖检索词，不能替代全局分类

推荐主图谱：`社群岛屿图`。原因是当前目标是“显明易说”的材料分类、查漏补缺和主题簇定位，而不是单纯展示漂亮的力导向大图。

## 高关联节点

- 显明 (person, C001): degree=229, sources=83, files=62
- 显明易说 (organization, C001): degree=210, sources=155, files=76
- Wechat (organization, C004): degree=34, sources=6, files=1
- WeChat (artifact, C003): degree=30, sources=20, files=10
- AI (concept, C001): degree=28, sources=17, files=9
- 显明老师 (person, C002): degree=27, sources=9, files=6
- 亥猪 (creature, C001): degree=26, sources=7, files=7
- Artificial Intelligence (artifact, C008): degree=25, sources=15, files=11
- 黄仁勋 (person, C014): degree=22, sources=6, files=2
- Wealth (concept, C005): degree=20, sources=10, files=6
- 2026 (other, C002): degree=18, sources=20, files=13
- 2025 (event, C002): degree=18, sources=11, files=8
- Feng Shui (concept, C009): degree=16, sources=8, files=5
- Fire (concept, C006): degree=16, sources=6, files=5
- 五行 (concept, C013): degree=15, sources=4, files=3
- 老师 (person, C016): degree=15, sources=4, files=4
- Xianming (person, C017): degree=14, sources=6, files=6
- Author (person, C003): degree=14, sources=5, files=4
- WeChat Official Account (content, C010): degree=13, sources=7, files=6
- 财神 (person, C027): degree=12, sources=6, files=3
- 怀山易德 (organization, C001): degree=12, sources=10, files=9
- Liu Bang (person, C050): degree=12, sources=4, files=2
- Destiny (concept, C025): degree=12, sources=5, files=4
- Xianming Yishuo (organization, C010): degree=12, sources=8, files=8
- Wei Xin (organization, C026): degree=11, sources=1, files=1

## 主要社群

- C001 size=440: 显明 / 显明易说 / AI
- C002 size=148: 显明老师 / 2026 / 2025
- C003 size=95: WeChat / Author / Momentum
- C004 size=47: Wechat / Fate / Cognition
- C005 size=38: Wealth / Money / Wife
- C006 size=34: Fire / Heavenly Stems / Metal
- C007 size=33: 龙 / 6月好运指导！抓重点避风险，方能拥有不错收益！ / 2025年8月
- C008 size=33: Artificial Intelligence / Education / Emotion
- C009 size=28: Feng Shui / I Ching / Kang Manyuan Manor
- C010 size=25: WeChat Official Account / Xianming Yishuo / Red Packet Covers
- C011 size=24: 桃花 / 火 / 土
- C012 size=24: 清明 / 卯兔 / 巳蛇
- C013 size=24: 五行 / 十分钟学会数字能量(颠覆版) / 甲午月
- C014 size=23: 黄仁勋 / 心力 / 人工智能
- C015 size=19: 气运之子 / 雷军 / 气运系统
- C016 size=19: 老师 / Tai Sui / Anxiety
- C017 size=18: Xianming / Xibei / 致胜宝典
- C018 size=17: Extreme Yang Water / Liver / Huangdi Neijing
- C019 size=17: 立春 / 2026年 / 咬春
- C020 size=16: 宏大叙事 / 个人综合素养 / 智能制造
- C021 size=15: You / Family / Precious Metals
- C022 size=14: 努力 / 副业 / 赚钱
- C023 size=13: Logo / Four Horses / Cloud Pattern
- C024 size=13: Xiang Yu / Opportunity / Battle of Gaixia
- C025 size=13: Destiny / Second Disciple / Target Vacuum

## 使用边界

LightRAG 图谱是自动抽取结果。它适合做导航、分类、关联发现和查漏补缺；需要引用事实或判断真伪时，必须回到来源文档核验。
