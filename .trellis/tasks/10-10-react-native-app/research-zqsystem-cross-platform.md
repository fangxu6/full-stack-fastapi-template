# 参考调研：zqsystem（存量系统）的 Web / App 跨端实现

调研对象：`D:\Workspace\sts\zqsystem`（只读分析，未修改）
调研目的：为本仓库"长期跨端开发方案"提供存量系统的正/反例证据。
结论状态：**该系统的技术栈不可迁移，但其分层判断与失败模式有直接参考价值。**

## 1. 系统形态

- 根 `pom.xml`（29 KB）为多模块 Maven 工程，约 50 个模块（`zq-web`、`zq-stock`、`zq-user`、`zq-market`、`zq-riskcontrol`、`xiancai-*`、`ib-agent`、`ctpAgent` 等）。
- 后端为 Java Spring MVC（`zq-web/src/main/java/com/zhuanqian/web/controller/**`）。
- 前端不是独立工程，而是作为静态资源挂在 `zq-web/src/main/webapp/` 下。
- **不是 Git 仓库**（`git log` → fatal: not a git repository），无法用提交历史判断演进。

## 2. 用户分析的核验结果（全部属实）

### 2.1 App 端 = Cordova 混合方案（WebView 容器）

- `js/mobileApp/app.js:17` `require.config({...})` —— RequireJS 模块管理，`baseUrl` 在 `/js/mobileApp` 与 `/js/mobileApp/dist` 间按 debug 切换。
- `js/mobileApp/app.js:22` `"backbone": debug?lib+"backbone":libJs`
- `js/mobileApp/app.js:24` `"jquery": debug?lib+"zepto.min":libJs`（**Zepto 被别名为 jquery**）
- `js/mobileApp/app.js:126` `backbone: {...}` 配置；`app.js:149` `require(['backbone','virtualDom','cookie'], ...)`
- Cordova 插件：`js/mobileApp/lib/cordova_android-0.0.9.js`，被 `views/distributionUnitView.js`、`views/findPasswordView.js`、`views/openAccountProcedureView.js`、`views/rechargePageView.js` 引用。
- 构建：`js/mobileApp/build.js:104-127`，RequireJS optimizer 把 `backbone/underscore/jquery/md5/cookie/swiper/mdatetimer` 打进 `libJs`，其余按 `utilsJs` / `viewsJs` / `modelsJs` 分块，并用超长 `exclude` 列表避免重复打包。

### 2.2 Web 端 = 多个相互独立的前端项目

`js/mobileApp/../前端项目日志.txt` 记录了项目清单：

- 维护中（10 个）：`express-client`、`generationMobile`、`generationPC`、`iwin`、`managementPlatform`(B端)、`mobileApp`、`niuqiClient`(PC 客户端)、`niuqiH5`、`officialWeb`、`systemPlatform`(P端)
- 确认废弃（4 个）：`admin`、`javascript`、`mobile`、`model`
- 不维护（2 个）：`niuqiPC`、`weChatApp`
- 未知项目（2 个）：`niuqiStockBaPC`、`iWinBroker`

对应目录同样是分裂的：`template/` 下 18+ 个项目模板目录，`js/` 下 19 个项目脚本目录。

- 各端页面自带资源，不共享：`template/generationPC/recharge.vm:7-9` 直接加载 `/css/generationPC/recharge.css`、`/js/lib/jquery-1.11.3.min.js`、`/js/lib/jquery.md5.js`。
- 前端工具链是 2016 年前后的：`webapp/package.json` 依赖 `gulp@^3.9.0`、`webpack@^1.13.1`、`node-sass@^3.10.1`、`requirejs@^2.1.22`、`velocityjs@^0.9.2`。

### 2.3 跨端复用 = 仅后端 HTTP 接口

用户举证的四处调用，已逐行核验：

| 接口 | App 侧 | Web 侧 |
|---|---|---|
| `/stockTrade/queryOrderList` | `js/mobileApp/models/orderCancelModel.js:36` | `js/officialWeb/distribution.js:2287` |
| `/h5/userInfo` | `js/mobileApp/models/userInfoModel.js:386` | `js/officialWeb/userAccountModel.js:52` |

- 两端各自用 `$.ajax({url:..., type:"get", dataType:"json"})` 直连，**各自解析各自响应**（`res.result === 1` / `res.result == 1` 判定都不统一）。
- 后端没有为端做区分：`/h5/userInfo` 还被 `js/niuqiMessage/models/chatModel.js:21` 第三个前端复用。
- **没有共享的前端类型定义、没有共享的校验层、没有共享的权限语义层、没有共享的 UI 组件包。**

### 2.4 端内复用是存在的（但只在端内）

- App 内：RequireJS 模块划分 + Velocity 片段复用 —— `template/mobileApp/transaction.vm:13` `#parse("mobileApp/commonTransactionPanel.vm")`，买入/卖出面板复用同一片段。
- Web 内：Velocity 布局片段复用，例如多个页面复用 `template/layout/myFund.vm`（`template/financialBills.vm:1`）。
- 即：**复用单元是"端内"，不是"跨端"。**

### 2.5 存在按 User-Agent 分流

`zq-web/src/main/java/com/zhuanqian/web/controller/niuqiPC/NiuqiPCController.java:841-845`：

```java
@RequestMapping(value = "/downloadPage", method = RequestMethod.GET)
public String appDownloadPage(HttpServletRequest request) {
    boolean mobileFlag = MobileAndPcAdapterUtil.check(request.getHeader("User-Agent"));
    return (mobileFlag ? "/generationMobile/downloadPage" : "/generationPC/downloadPage");
}
```

同一 URL 按 UA 返回两套完全不同的模板 —— 反证"一份页面同时适配所有端"在该系统里没有成立，最终退化为按端分流。

## 3. 可参考的部分

| # | 可参考的点 | 对本方案的映射 |
|---|---|---|
| R-a | **后端契约是唯一长期稳定的跨端共享层**：`/stockTrade/queryOrderList`、`/h5/userInfo` 被 2~3 个前端长期共用而未腐化 | 直接支撑 Q1 选 A：把"事实上的接口共享"升级为**显式契约共享**（`packages/contract`，本项目已有 OpenAPI 生成物，比它更强） |
| R-b | **按端独立前端在工程上可持续**：一个团队长期维护 10+ 个独立前端 | 支撑"两端两套 UI"作为长期形态成立，即 Q1-A 的可行性有历史证据 |
| R-c | **端内复用必须显式化**：App 用 RequireJS 模块 + Velocity `#parse`，Web 用 `layout/*.vm` | 对应本仓库：Web 用 `frontend/src/shared/*`，App 需要自己的 `shared/*`；**不要指望跨端复用 UI** |
| R-d | **按端分流需要一个显式决策点**：UA 分流说明"哪些能力上哪个端"是必须被显式决定的 | 对应本方案 R5 / Q5：需要"功能上端策略"规格 |
| R-e | **"一套代码适配所有端"在真实系统里会退化** | 是 Q1 选 B（react-native-web 单代码库）的风险证据 |

## 4. 不可参考 / 反面教材

| # | 不可参考的点 | 原因 |
|---|---|---|
| N-a | **Cordova 混合（WebView 容器）** | 本任务已明确选 React Native 原生渲染；且该栈为 2016 年技术 |
| N-b | **RequireJS / Backbone / Zepto / jQuery 1.11 / Velocity 服务端模板** | 与 React 19 + Vite + TanStack Router（SPA）与 RN 生态完全不同 |
| N-c | **"共享接口但两端各写一遍解析/校验"** | 这是**未治理的重复**：`userInfoModel.js` 与 `userAccountModel.js` 各有一份 `/h5/userInfo` 处理逻辑，连 `result === 1` 判定都不统一。本方案必须把"共享接口"升级为"共享契约 + 共享领域语义" |
| N-d | **前端项目数量无限增长** | 10 个维护中 + 4 个已废弃 + 2 个不维护 + 2 个"未知项目"，是复制式增长的直接结果。跨端方案必须配交付纪律与门禁（本方案 R5 / AC7） |

## 5. 对 Q1 的关键影响

1. zqsystem 的 App 是 **WebView 混合**，即两端本来就都是 HTML/CSS/JS —— 它**本可以**跨端复用 UI 片段，但实际**仍然没有**，而是各端独立。这强化了"跨端复用 UI 收益低、成本高"的判断，**支持 Q1 选 A 而非 B**。
2. 但 zqsystem 从未做到"同时实现"：改一个跨端业务页面必须改两处。因此必须诚实修正预期：
   - Q1-A 给出的不是"写一次"，而是 **"内核一次 + UI 两次"**；
   - 真正的收益在于 UI 两次之间的**差异被压缩到纯呈现层**（契约、权限语义、校验、业务规则已共享），而不是消灭第二次。
3. 因此 A 必须同时包含三件东西，否则会退化成 zqsystem 的 N-c/N-d：
   - 共享契约（`packages/contract`）
   - 共享领域语义（`packages/domain`：权限码、query key、校验、错误分类）
   - 跨端交付纪律与门禁（`.trellis/spec/` 规格 + 可执行校验）
