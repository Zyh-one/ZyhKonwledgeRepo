# OpenSearch 日志检索

OpenSearch 是 34 测试环境 PaaS 平台的日志检索底座。本文聚焦三件事：它内部的数据如何组织、在 34 集群上以什么形式部署运行、以及一次检索请求的 query DSL 如何构造。配套脚本 `~/.claude/skills/pod-log-analyze/pull_logs.py` 即基于此通道。

调查信息：

| 项目            | 34 测试环境                                                                                                               | 黄区（生产，对照）                                                   |
| --------------- | ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| 入口            | `http://logging-dashboards.172-24-32-31.nip.io:30201`（Dashboards，明文 HTTP）                                          | `http://10.8.61.203:9200`（ES 后端直连，明文 HTTP）                |
| Dashboards 版本 | OpenSearch Dashboards 2.18.0                                                                                              | （无 Dashboards，直连 ES）                                           |
| index 模式      | `cambricon-paas*`（按天分片 `cambricon-paas-YYYY.MM.DD`）                                                             | `cambricon-infra*`（infra 日志）/ `cambricon-event*`（k8s 事件） |
| 区分来源字段    | `kubernetes_pod_name`（text，无 `.keyword`）                                                                          | `tag.keyword`（如 `*gateway-plugin*` / `*envoy-svc*`）         |
| 检索正文        | `log`（text）                                                                                                           | `log` / `message`                                                |
| 时间字段        | `@timestamp`（date，UTC）                                                                                               | `@timestamp`（date，UTC）                                          |
| 认证            | 无                                                                                                                        | 无                                                                   |
| 访问通道        | Dashboards console proxy                                                                                                  | 直连 ES`_search` + scroll                                          |
| 后端 pod        | `logging-master-0/1/2`、`logging-hot-data-0`、`logging-cold-data-0`、`logging-dashboards-*`（节点 `machine34`） | （独立集群，另行确认）                                               |
| 采集组件        | `logging-fluentd` DaemonSet（6 副本，`nodeSelector fluentd=true`）+ `cambricon-fd`                                  | 同（fluentd 类采集器 push）                                          |

> 两套是不同的 OpenSearch 实例。本文以 34 为主，黄区作为对照列出；两者 query DSL 语法一致，只是入口通道与区分来源的字段不同。

## 1. 数据如何组织

OpenSearch 是开源分布式搜索与分析引擎（Apache 2.0，Linux Foundation 托管；2021 年由 AWS 从 Elasticsearch 7.10 fork，与 ES 7.10 高度兼容）。底层 Apache Lucene，**文档型**存储，和时序型（VictoriaMetrics/Prometheus）结构不同。层级对照：

| 层级     | OpenSearch（文档型）                                                                                                                                      |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 顶层容器 | **index**（如 `cambricon-paas*`，可拆 **shard** 分片水平分布 + **replica** 副本高可用，按天物理分片为 `cambricon-paas-2026.09.24`） |
| 数据单元 | **document**（一条 JSON）                                                                                                                           |
| 字段     | 任意 JSON 键，每条可不同                                                                                                                                  |
| 查询语言 | query DSL（JSON）                                                                                                                                         |

### 1.1 一条文档长什么样

fluentd 采集 pod stdout 后，每条日志被组装成一个 document 写入 index。典型结构（字段因环境略异）：

```json
{
  "@timestamp": "2026-09-22T00:05:53.408Z",
  "tag": "infra.aibrix.var.log.containers.aibrix-gateway-plugins-6b4c9ffb99-24g57_aibrix-system_gateway-plugin-28c7d1f....log",
  "kubernetes_pod_name": "aibrix-gateway-plugins-6b4c9ffb99-24g57",
  "log": "I0922 00:05:53.408 ... gateway_req_headers.go:146] \"processing request\" ...",
  "namespace": "aibrix-system"
}
```

四个关键字段各司其职：

- **`@timestamp`**（date）—— 采集时间，圈时间窗用。
- **`log`**（text）—— 日志**正文**，即服务 stdout 那一行。全文检索在这里做。
- **`kubernetes_pod_name`**（text，34 上）—— 来源 pod 名，按 pod 定位用。注意无 `.keyword` 子字段（分词，不能聚合/排序）。
- **`tag`**（黄区用）—— 采集器填的**源文件路径**，编码了 pod+namespace+容器名（见 §1.2）。

### 1.2 `tag` 的结构

`tag` 不是服务自己打的，是采集器根据"从哪个文件读到这条日志"自动填的源路径。拆开：

```
infra . aibrix . var.log.containers . <pod名> _ <namespace> _ <容器名>-<容器ID> . log
                                   └────────── k8s 容器日志文件路径 ──────────┘
```

即 k8s 标准容器日志路径 `/var/log/containers/<pod>_<namespace>_<container>-<id>.log`（点代斜杠，前缀 `infra.<系统>`）。因此 `tag.keyword: *gateway-plugin*` 通配命中的是路径中**容器名**那段，`*envoy-svc*` 命中的是 `envoy-svc-exporter`。**选 tag = 选来源容器，不是选正文里的词。**

### 1.3 push 模型（区别于时序库的 pull）

OpenSearch 是**被动收**：它开 :9200 端口等数据，自己不主动拉。是 fluentd DaemonSet 跑在每个节点读 pod stdout 后 **POST 推送**到 OpenSearch 写入 index。对照 VictoriaMetrics 是 **pull**（主动 scrape 各服务 `/metrics`）。方向相反——这是"日志库"与"指标库"的根本差异。

> 已知边界：fluentd 只采 pod **stdout**。容器内写文件路径的日志（如 aibrix gateway-plugins 的 `/tmp/gateway.log`）不进 OpenSearch，读不到。

## 2. 34 上 OpenSearch 是什么形式的服务

它是一组 **StatefulSet pod**（不是单个进程），跑在 `kube-system`、节点 `machine34`：

- `logging-master-0/1/2` —— master 节点（集群状态管理）；
- `logging-hot-data-0` —— 热数据节点（近期索引）；
- `logging-cold-data-0` —— 冷数据节点（历史归档）；
- `logging-dashboards-7fdb6b77bd-*` —— Dashboards UI pod。

对外通过一个 **nip.io HTTP 入口**暴露：`http://logging-dashboards.172-24-32-31.nip.io:30201`（明文、无认证）。nip.io 是把 IP 编进域名的泛解析服务（`172-24-32-31.nip.io` 解析回 `172.24.32.31`），省去配 Ingress/域名。

访问方式两种：

- **浏览器/DevTools**：直接打开 Dashboards UI——Discover 按时间窗查日志、Dev Tools 交互式发 query DSL、Stack Management 看 index pattern 与字段映射（确认某字段是 text 还是 date、有无 `.keyword` 子字段）、Visualize 建图表。
- **脚本**：走 Dashboards 的 **console proxy**，用 `requests` POST 一个 query DSL（见 §3）。不用 `kubectl logs`（只能看节点最近滚动窗口）、不用 `curl`/`WebFetch`（会升 HTTPS 撞坑①）。

## 3. 典型 query DSL 查询请求如何构造

### 3.1 请求形状（34 console proxy 通道）

```http
POST http://logging-dashboards.172-24-32-31.nip.io:30201/api/console/proxy?path=%2Fcambricon-paas*%2F_search&method=GET
Header: Content-Type: application/json; osd-xsrf: true
Body  : { OpenSearch query DSL }
```

- 路径走 query string `path` + `method`，不是 body；`path` 里是 `<index>/<endpoint>`（URL 编码）。
- `<endpoint>` 取 `_count`（计数）或 `_search`（检索/聚合）。

### 3.2 query DSL 解剖

**写法一：`query_string` 串式**（34 脚本常用，简洁）

```json
{
  "size": 1000,
  "_source": ["@timestamp", "log"],
  "sort": [{ "@timestamp": { "order": "asc" } }],
  "query": {
    "query_string": {
      "query": "kubernetes_pod_name:\"pd-300k-0906-201805\" AND @timestamp:[\"2026-09-24T12:30:00.000Z\" TO \"2026-09-24T21:00:00.000Z\"]"
    }
  }
}
```

**写法二：`bool` 结构式**（黄区 `fetch_log.sh` 用，可读性强）

```json
{
  "size": 10000,
  "_source": ["log"],
  "sort": [{ "@timestamp": { "order": "asc" } }],
  "query": {
    "bool": {
      "filter": [{ "range": { "@timestamp": { "gte": "2026-09-29T01:20:00", "lte": "2026-09-29T01:40:00" } } }],
      "must":   [{ "wildcard": { "tag.keyword": "*gateway-plugin*" } }]
    }
  }
}
```

逐键含义：

| 键                           | 作用                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------ |
| `size`                     | 本页返回条数（`_search` 上限 10000，超了用 scroll）                                |
| `_source`                  | 只返回这些字段，省带宽（大日志体只取`log`+`@timestamp`）                         |
| `sort`                     | 按`@timestamp` 升序，保证日志时间顺序                                              |
| `query.query_string.query` | Lucene 串：`pod名:"..."`(text 短语匹配) `AND @timestamp:["..." TO "..."]`(range) |
| `bool.filter`              | 不参与算分的过滤（时间窗 range`gte/lte`）                                          |
| `bool.must`                | 通配匹配（`tag.keyword` 选来源容器；`keyword` 子字段不分词，可通配）             |

时间窗用 **UTC**，北京时间需 +8 转换（如 09-24 20:30 CST → `2026-09-24T12:30:00.000Z`）。

`pull_logs.py` 默认查最近 24h，加 `--start/--end` 指定历史窗口：

```bash
python3 ~/.claude/skills/pod-log-analyze/pull_logs.py \
  --pods "podA,podB" --out <OUT> \
  --start "2026-09-24T12:30:00.000Z" --end "2026-09-24T21:00:00.000Z"
```

### 3.3 scroll 深翻页

结果超万条时用 scroll（黄区 `fetch_log.sh` 即此机制）：

1. 首次 `GET /<index>/_search?scroll=1m` → 返回首批 + `_scroll_id`；
2. 反复 `POST /_search/scroll` body `{"scroll":"1m","scroll_id":"<id>"}` 取下一页；
3. 某次 `hits.hits.length==0` 即取完。

游标上下文维持 1 分钟（每次调用续期），比 `from/size` 翻页稳定，不随页数增大变慢。

### 3.4 四个已知坑

| 坑                               | 现象                                                                                            | 规避                                                                                                                     |
| -------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| ① SSL WRONG_VERSION_NUMBER      | WebFetch/curl 默认升 HTTPS，端口只跑明文 HTTP                                                   | 一律明文 HTTP，用`requests` 直打，不用 WebFetch                                                                        |
| ② console proxy 路径形式        | `/elasticsearch/<path>`、`/api/console/proxy/<path>` 都 404                                 | 必须 query 参数`?path=/cambricon-paas*/_search&method=GET`，缺 `method` 报 `request query.method: expected string` |
| ③ too_many_nested_clauses(1024) | `log:(A OR B OR C)` 多词 OR 在 text 字段炸子句返回 500                                        | 单关键词逐个查（`log:ERROR`、`log:Traceback`…），Python 侧聚合                                                      |
| ④ text 字段不能聚合/排序        | `kubernetes_pod_name` 无 `.keyword`，terms 聚合或 sort 报 `Text fields are not optimised` | 检索用`query_string` 短语匹配，统计 pod 维度在 Python 侧 group by                                                      |

### 3.5 pod 名匹配语义与 63 字符截断

`kubernetes_pod_name:"pd-300k-0906-201805"` 是 text 短语匹配，会命中所有带这些 token 的 role 后缀 pod（`...-decode-...`、`...-prefill-...`）；传完整 pod 名则精确到单 pod。

> 注意 63 字符截断：OpenSearch 中 `kubernetes_pod_name` 存储截断到 63 字符。真实 pod 名 `prediction-service-0924-...-prefill-5b7765-0-0`（64 字符）存为 `pion-service-...-prefill-5b7765-0-0`（前端 `rediction-` 段被截）。用完整真实名做 phrase 查询会 0 命中，应先取截断后的存储名再点查。
