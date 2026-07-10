# 显明易说 LightRAG 图谱 WebGL 原型

这是“第二方案”前端原型，输出目录独立于当前主版：

- 原型页面：`C:\html\xianmingyishuo-graph-browser-sigma\index.html`
- 说明文件：`C:\html\xianmingyishuo-graph-browser-sigma\README.md`
- 只读数据源：`C:\html\xianmingyishuo-graph-browser\graph-data.json`

## 实现技术

- 主渲染：Sigma.js 2.4.0 + Graphology 0.25.4，通过 CDN 加载。
- 图谱数据：默认从兄弟目录 `../xianmingyishuo-graph-browser/graph-data.json` 只读加载。
- 布局：复用数据里的预计算 `layouts`，避免浏览器端重新跑力导向布局。
- 降级：如果 Sigma.js、Graphology 或 WebGL 初始化失败，自动切到本地 Canvas 2D 渲染。

## 功能范围

- 搜索节点、描述、来源文件。
- 节点类型过滤。
- 社群过滤。
- 节点详情：类型、社群、degree、PageRank、描述、相邻关系、来源文件。
- 重置、居中、标签开关。
- 布局切换：社群岛屿、主干骨架、PageRank 中心、K-core、核心-外围、类型环带。
- 边权下限过滤。

## 运行方式

推荐从 `C:\html` 作为站点根目录启动本地服务器：

```powershell
python -m http.server 8765 --directory C:\html
```

然后打开：

```text
http://127.0.0.1:8765/xianmingyishuo-graph-browser-sigma/index.html
```

## 是否能直接打开

可以直接双击打开页面壳，但不保证自动读取数据。原因是浏览器通常会拦截 `file://` 页面用 `fetch` 读取相邻本地 JSON 文件。

直接打开时可用页面里的“本地文件降级”选择：

```text
C:\html\xianmingyishuo-graph-browser\graph-data.json
```

如果网络或 CDN 不可用，WebGL 路径不可用，页面会退到 Canvas 2D；但数据仍需通过本地服务器或文件选择器载入。

## 优点

- WebGL 渲染比主版 Canvas 更适合 3,641 节点 / 2,884 边的交互浏览。
- 复用预计算布局，首屏稳定，不在浏览器里做重计算。
- 筛选通过 Sigma reducer 完成，不需要每次重建图。
- 依赖失败时有 Canvas 2D 兜底，不会空白退出。

## 缺点和限制

- CDN 依赖存在网络可用性问题；离线环境只能使用 Canvas 降级。
- `file://` 直接打开无法稳定自动读取兄弟目录 JSON，推荐 localhost。
- Sigma 当前只做图谱浏览原型，未加入图数据库查询、向量相似性或算法侧新结果。
- 社群数量较多，社群下拉框偏长；后续可改成可搜索组合框。

## 数据边界

LightRAG 图谱是自动抽取结果，适合导航、分类、发现关联和查漏补缺。涉及事实判断时仍需回到来源文档核验。
