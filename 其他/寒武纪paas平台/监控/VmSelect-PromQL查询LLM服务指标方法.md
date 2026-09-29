# 向 VmSelect 发起 PromQL 查询获取 LLM Serving 指标的完整方法

> 本文以 `prediction-service-0924-202926`（黄区 `bj-caip` 集群，namespace `ns-e23f5b20fb9b42d3ac674f9691a0b9b1`）为实例，完整记录：如何从代码里找到 PromQL 模板、如何确定 VmSelect 地址、如何填充查询参数、如何构造 HTTP 请求、以及返回结果的格式。
>
> 日期：2026-09-29｜证据来源：devplatform 代码库 + 黄曲生产集群只读查询（`huangqu-cluster-readonly` skill）

---

## 0. 全流程概览

```
① 读 PromQL 模板（带 %(name)s 占位符）
   来源: webapp/caip/projects/shared/src/lib/container-monitor/constant/llm-query.constant.ts

② 查 llmserving CR → 拿到 namespace / label_id / version / 角色 / pod
   来源: kubectl get llmserving <name> -n <ns> -o yaml

③ 确定 VmSelect 地址
   - 代码里写的集群内地址: http://vmselect-vmcluster.monitoring:8481/select/0/prometheus
     (api/common/pkg/conf/conf.go, 仅集群内可解析)
   - 跳板机可达地址: http://172.26.254.216:8481/select/0/prometheus
     (vmselect-node-port 这个 NodePort 服务的 ClusterIP)

④ 填占位符 → 生成完整 PromQL

⑤ 向 VmSelect 发 range 查询: GET /api/v1/query_range?query=...&start=...&end=...&step=...
   返回 JSON matrix 结果

⑥ 解析 JSON → 降采样汇总(min/avg/max + 趋势)
```

---

## 1. PromQL 模板来源与占位符

### 1.1 模板文件

**文件**：`webapp/caip/projects/shared/src/lib/container-monitor/constant/llm-query.constant.ts`

该文件把每条指标定义成一个带 Python 风格 `%(name)s` 占位符的 PromQL 字符串常量。例如「推理请求量」：

```ts
export const vllmRequestPerStep = `
  sum by (namespace%(labelServiceBy)s%(labelVersionBy)s%(groupPod)s) (
    increase(
      http_requests_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id=~"%(labelID)s"%(labelRoleName)s,
        handler=~".*(messages|completions).*"
      }[%(time)s:30s]
    )
  )
`;
```

### 1.2 占位符填充规则

前端在 `llmservice-monitor-graph.component.ts` 里用 `sprintf` 分两阶段填充：

| 占位符             | 取值来源                                                                | 本次实例的值                                           |
| ------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------ |
| `cluster`        | 前端固定填`.*`（后端 VmSelect 只见本集群数据）                        | 我改成精确值`bj-caip`（探测得到）                    |
| `namespace`      | `getK8sNamespace(this.namespace)`                                     | `ns-e23f5b20fb9b42d3ac674f9691a0b9b1`                |
| `labelID`        | `this.applicationID`（服务 UUID，匹配 pod 的 `label_id` 标签）      | `4f0059c1-42d8-4f15-a939-9274b17bfc06`               |
| `pod`            | 下拉选`monitorVariableValues.pod`，默认 `.*`                        | `.*`                                                 |
| `version`        | `monitorVariableValues.version`，默认 `.*`                          | `0.0.1`                                              |
| `time`           | `this.step`（查询步长，同时作为子查询窗口 `[time:30s]` 的窗口长度） | 代码默认`1m`（见 §4.1）；本文实例手动取 `5m`      |
| `groupPod`       | 若选了具体 pod 则`,pod`，否则空串                                     | 空                                                     |
| `labelRoleName`  | 若选了角色则`,label_role_name=~"<role>"`，否则空                      | 空（我在 by 子句里显式加`label_role_name` 来分角色） |
| `labelServiceBy` | 按服务分组时`,label_id`，否则空                                       | 空                                                     |
| `labelVersionBy` | 有版本变量且非`.*` 时 `,label_version`                              | `,label_role_name`（我改为按角色拆）                 |
| `tp`             | 组件构造期烘焙：`0.999`/`0.95`/`0.90`/`0.5`                     | 分位查询时用                                           |
| `status`         | `4xx` / `5xx`                                                       | 错误码查询时用                                         |
| `transferType`   | `CPU_to_MLU` / `MLU_to_CPU`                                         | KV 卸载查询时用                                        |

> 关键点：`label_id` 是把指标关联到某个在线服务的"主键"——vLLM pod 被 scrape 时带 `label_id=<服务UUID>` 标签，查某个服务的指标就是用 `label_id="..."` 过滤。这个 UUID 来自 llmserving CR 的 `metadata.labels.id`。

---

## 2. 如何获取黄区 VmSelect 地址

### 2.1 代码里的集群内地址

后端 Go 代码 `api/common/pkg/conf/conf.go`（默认值）配置了 VmSelect 上游：

```
query: http://vmselect-vmcluster.monitoring:8481/select/0/prometheus
```

- `/select/0/prometheus` 是 VictoriaMetrics 多租户的 Prometheus 兼容端点。
- 后端 handler `api/monitor/internal/monitoring/monitoring.go` 把前端 `POST /api/monitor/v1/namespace/{ns}/range` 的请求原样转发为 `GET {query}/api/v1/query_range?query=...&start=...&end=...&step=...`。
- 后端到 VmSelect 不加任何鉴权头，纯 GET。

### 2.2 跳板机不能直接解析集群内 DNS

`vmselect-vmcluster.monitoring` 是 ClusterIP 服务名，只在集群 pod 网络内可解析。在跳板机 `remmina-huangqu` 上：

```
$ nslookup vmselect-vmcluster.monitoring
** server can't find vmselect-vmcluster.monitoring: NXDOMAIN
```

### 2.3 找到跳板机可达的 NodePort 服务

通过只读 `kubectl` 发现 `monitoring` 命名空间里有一个 NodePort 服务：

```
$ kubectl get svc -n monitoring | grep -iE "vmselect"
vmselect-node-port     NodePort    172.26.254.216   <none>   8481:30902/TCP   2y19d
vmselect-vmcluster      ClusterIP   None             <none>   8481/TCP          291d
```

- `vmselect-node-port` 的 ClusterIP = `172.26.254.216`，端口 `8481`，NodePort `30902`。
- 跳板机能路由到 `172.26.x.x` 网段，所以直接用 ClusterIP 即可：

```bash
$ curl -s --max-time 5 "http://172.26.254.216:8481/select/0/prometheus/api/v1/query?query=up" | head -c 300
{"status":"success","isPartial":false,"data":{"resultType":"vector","result":[{"metric":{"__name__":"up","cluster":"bj-caip",...},"value":[1790647583,"1"]},...
```

成功。同时从这条返回里发现 `cluster` 标签的真实值 = **`bj-caip`**。

### 2.4 最终采用的可达端点

```
http://172.26.254.216:8481/select/0/prometheus
```

- 即时查询（instant）：`GET .../api/v1/query?query=<PromQL>&time=<unix>`
- 范围查询（range）：`GET .../api/v1/query_range?query=<PromQL>&start=<unix>&end=<unix>&step=<秒>`

---

## 3. 如何获取查询参数（从 llmserving CR）

用只读 `kubectl` 取目标服务的 CR：

```bash
$ kubectl get llmserving prediction-service-0924-202926 \
    -n ns-e23f5b20fb9b42d3ac674f9691a0b9b1 -o yaml
```

关键字段提取：

| 字段               | 值                                       | 在 CR 里的位置                                       |
| ------------------ | ---------------------------------------- | ---------------------------------------------------- |
| namespace          | `ns-e23f5b20fb9b42d3ac674f9691a0b9b1`  | metadata.namespace                                   |
| **label_id** | `4f0059c1-42d8-4f15-a939-9274b17bfc06` | metadata.labels.id                                   |
| 模型               | glm5（GLM-5.3-W4A8）                     | labels model.aibrix.ai/name                          |
| version            | `0.0.1`                                | spec.versions[0].name                                |
| 角色               | prefill + decode（PD 分离式）            | spec.versions[0].stormServiceSpec.spec.roles[*].name |
| 创建/过期          | 2026-09-24 12:29:55Z ~ 21:46:44Z         | creationTimestamp / expirationTime                   |
| 状态               | Expired（pod 已回收）                    | 活跃窗口结束后查询属历史指标                         |

pod 名（从 VmSelect 探测得到，pod 已被回收所以只能从指标里看）：

- prefill: `prediction-service-0924-202926-...-prefill-5b7765-0-0`
- decode: `prediction-service-0924-202926-...-decode-59f9c9-0-0`

> 探测 pod 与角色：`count by(pod,label_role_name)(vllm:num_requests_running{namespace="...",label_id="..."})`

---

## 4. 请求是如何构造的（典型示例）

### 4.1 默认时间范围与默认查询间隔（代码默认值，无需手动给定）

代码里写死了默认值，打开在线服务监控页时自动生效，**不需要手动指定时间范围或 step**。来源：`predictor-monitor.component.ts` 的 `getPredictorMonitorDatePicker` + `distributed-platform-antd` 的 `getDateRangeAndStep` / `calculateInterval`。

#### 4.1.1 默认时间范围

宿主页 `PredictorMonitorComponent` 在 `ngOnInit` 用 `getPredictorMonitorDatePicker(predictor)` 构建 DatePicker（`predictor-monitor.component.ts:259-286`，绑定于 `:401`）：

```ts
// predictor-monitor.component.ts:271-279
return predictor.status?.overview === 'Running'
  ? {
      start: null, end: null,
      lastTime: '1h',            // ← 默认时间范围
      minTime: timeRangeMin,
      maxTime: timeRangeMax,
      autoRefreshDuration: '30s',
    }
  : { // Stopped / Expired / Suspended
      start: predictor.status.runningTimestamp ? new Date(predictor.status.runningTimestamp) : timeRangeMin,
      end: end,                  // = suspendedTimestamp + 30s（若无 suspendedTimestamp 则 = now）
      lastTime: null,
      minTime: timeRangeMin,
    };
```

`lastTime: '1h'` 由 `getDateRange`（`date-picker-helper.ts:6-20`）解析为实际 start/end：`end = now`，`start = now - 1h`。`AdvancedDatePickerComponent.writeValue` 空值兜底同样是 `lastTime: '1h'`（`advanced-date-picker.component.ts:162-165`）。

| 服务状态                  | 默认时间范围                                                                                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Running（在线）** | **最近 1 小时**：`end = now`，`start = now - 1h`（`lastTime='1h'`），自动刷新 30s                    |
| Stopped / Expired         | 服务的实际运行窗口：`start = runningTimestamp`（或 `creationTimestamp`），`end = suspendedTimestamp + 30s` |

> 快选菜单 `quickTimeOpts = ['30m','1h','2h','3h','5h','12h','1d','2d','3d','7d']`（`advanced-date-picker.component.ts:63`）；默认选中的是 `'1h'`，不是 6h/24h。
>
> 注：本文实例 `prediction-service-0924-202926` 状态为 Expired，按代码默认其范围应是运行窗口（≈ 09-24 12:29~21:46Z）。下文 §4.2/§4.3 出于"回看整段历史"的目的，把范围手动扩到 9h、step 放到 5m，**那是为了全量回看的覆盖式取值，不是代码默认**；想完全复刻代码默认，对 Running 服务用 `start=now-3600&end=now&step=60`。

#### 4.1.2 默认查询间隔（step）

`ContainerMonitorComponent` 的 step 流（`container-monitor.component.ts:114-122, 429-436`）：

```ts
customStep: string | null = null;
autoStep: string = '1s';           // 占位，首次 calculateAutoStep 后被覆盖
get step(): string { return this.customStep || this.autoStep; }

private calculateAutoStep() {
  const step = getDateRangeAndStep(this.innerDatePicker)[2];   // 秒
  this.autoStep = humanizeSeconds(step || 0.001).replace(/\s/g,'');
}
```

用户不填 `customStep` 时，`step = autoStep`，由 `getDateRangeAndStep` 算出（`date-picker-helper.ts:47-53`）：

```ts
const range = getDateRange(date);               // [startMs, endMs]
const step = getUnixTimestamp(calculateInterval(start, end, 180));
return [getUnixTimestamp(start), getUnixTimestamp(end), step];
```

`calculateInterval`（`interval.ts:94-102`）：目标 180 个采样点，下限 60s：

```ts
function calculateInterval(start, end, resolution=180, lowLimitMs=60000) {
  let intervalMs = roundInterval((end - start) / resolution);
  if (lowLimitMs > intervalMs) intervalMs = lowLimitMs;   // 最低 60s
  return intervalMs;
}
```

**默认 1h 范围下的计算**：

1. `(end - start) = 3,600,000 ms`
2. `/ 180 = 20,000 ms` → `roundInterval(20000)`：`20000 < 25000` → 返回 `20,000 ms`（20s）
3. `lowLimitMs = 60,000 > 20,000` → 钳到 **60,000 ms（60s）**
4. `humanizeSeconds(60) = "1m"` → `autoStep = "1m"`

**所以默认 step = `1m`（60 秒）。**

`roundInterval` 关键分档（`interval.ts:2-91`，单位 ms）：

| 范围跨度 | `(end-start)/180` 落入 | step         |
| -------- | ------------------------ | ------------ |
| ≤ 1h    | 20s → 被下限钳到 60s    | **1m** |
| ~3h      | 60,000 →`<90000`      | 1m           |
| ~6h      | 120,000 →`<210000`    | 2m           |
| ~12h     | 240,000 →`<450000`    | 5m           |
| ~1d      | 480,000 →`<750000`    | 10m          |
| ~2d      | 960,000 →`<1500000`   | 20m          |
| ~7d      | 3,360,000 →`<5400000` | 1h           |

> 子查询窗口 `[%(time)s:30s]`：`%(time)s` 填的就是 `this.step`（默认 `1m`），内层 `:30s` 是**固定字面量**（每条 `llm-query.constant.ts` 常量都写死）。默认渲染为 **`[1m:30s]`**。

#### 4.1.3 小结：代码默认的请求参数

| 参数              | Running 服务默认     | Expired/Stopped 服务默认                     |
| ----------------- | -------------------- | -------------------------------------------- |
| `start`         | `now - 3600`（秒） | runningTimestamp（或 creationTimestamp）     |
| `end`           | `now`（秒）        | suspendedTimestamp + 30s                     |
| `step`          | `60`（1m）         | `roundInterval((end-start)/180)`，下限 60s |
| PromQL 子查询窗口 | `[1m:30s]`         | `[<step>:30s]`                             |

---

### 4.2 填好占位符的 PromQL（以「推理请求量」为例）

模板 `vllmRequestPerStep` 填入实例参数后：

```promql
sum by(namespace,label_role_name)(
  increase(
    http_requests_total{
      cluster="bj-caip",
      namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
      pod=~".*",
      label_version=~"0.0.1",
      label_id="4f0059c1-42d8-4f15-a939-9274b17bfc06",
      handler=~".*(messages|completions).*"
    }[5m:30s]
  )
)
```

说明：

- 我把前端默认的 `cluster=~".*"` 改成精确 `cluster="bj-caip"`（探测得到），更精确。
- 把 `by(...)` 子句里的 `label_version` 换成 `label_role_name`，这样一条查询就能同时返回 prefill 和 decode 两条曲线。
- `[5m:30s]` 是子查询：窗口 5 分钟、子步长 30s；`increase` 计算该窗口内的增量。外层 `step=300s` 控制返回采样点分辨率。
  - ⚠️ 这里 `5m` + `step=300` 是**本文为回看整段 9h 历史而设的手动覆盖值**，不是代码默认。代码默认：Running 服务 `step=60`、子查询窗口 `[1m:30s]`（见 §4.1）。

### 4.3 HTTP 请求（range 查询）

VmSelect 的 range 查询是 HTTP GET，参数走 query string：

```
GET http://172.26.254.216:8481/select/0/prometheus/api/v1/query_range
    ?query=<URL编码后的PromQL>
    &start=1790572200      # 2026-09-24 12:30:00Z 的 unix 秒
    &end=1790605500        # 2026-09-24 21:45:00Z 的 unix 秒
    &step=300              # 5 分钟一个采样点
```

用 curl + `--data-urlencode` 自动编码最省事（避免手写 URL 编码）：

```bash
curl -sG "http://172.26.254.216:8481/select/0/prometheus/api/v1/query_range" \
  --data-urlencode 'query=sum by(namespace,label_role_name)(increase(http_requests_total{cluster="bj-caip",namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",pod=~".*",label_version=~"0.0.1",label_id="4f0059c1-42d8-4f15-a939-9274b17bfc06",handler=~".*(messages|completions).*"}[5m:30s]))' \
  --data-urlencode 'start=1790572200' \
  --data-urlencode 'end=1790605500' \
  --data-urlencode 'step=300'
```

`-G` 表示把 `--data-urlencode` 的内容拼到 URL query string 上（GET），而不是放进 body。

> 上例 `start/end/step` 是覆盖式手动取值（回看 9h 全程）。若要完全复刻代码默认，对 Running 服务：`start=$(date -d '1 hour ago' +%s)`、`end=$(date +%s)`、`step=60`，子查询窗口随之 `[1m:30s]`。

### 4.4 批量查询（Python 脚本）

实际排查时一次会拉十几条指标，用 Python `urllib` 循环更高效。核心片段：

```python
import urllib.request, urllib.parse, json, datetime

VM="http://172.26.254.216:8481/select/0/prometheus"
NS="ns-e23f5b20fb9b42d3ac674f9691a0b9b1"
LID="4f0059c1-42d8-4f15-a939-9274b17bfc06"

def unix(dt):
    return int(datetime.datetime.fromisoformat(dt.replace("Z","+00:00")).timestamp())

START=unix("2026-09-24T12:30:00Z")   # 1790572200
END  =unix("2026-09-24T21:45:00Z")   # 1790605500
STEP=300

L=f'cluster="bj-caip",namespace="{NS}",pod=~".*",label_version=~"0.0.1",label_id="{LID}"'

def rng(q):
    p=urllib.parse.urlencode({"query":q,"start":START,"end":END,"step":STEP})
    url=f"{VM}/api/v1/query_range?{p}"
    with urllib.request.urlopen(url,timeout=60) as r:
        d=json.load(r)
    return d["data"]["result"] if d.get("status")=="success" else []

q=f'sum by(namespace,label_role_name)(increase(http_requests_total{{{L},handler=~".*(messages|completions).*"}}[5m:30s]))'
series=rng(q)
# series: [{"metric":{"label_role_name":"decode",...},"values":[[ts,"v"],...]}, ...]
```

> 通过 SSH 在跳板机上跑：`ssh -F ~/ssh-connections/ssh-config remmina-huangqu "python3 -s -" < script.py`

---

## 5. 请求结果的格式

### 5.1 range 查询返回结构（`resultType: "matrix"`）

```json
{
  "status": "success",
  "isPartial": false,
  "data": {
    "resultType": "matrix",
    "result": [
      {
        "metric": {
          "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
          "label_role_name": "decode"
        },
        "values": [
          [1790572200, "44.2"],
          [1790572500, "40"],
          [1790572800, "56"],
          "...": "...",
          [1790605500, "0"]
        ]
      },
      {
        "metric": {
          "namespace": "ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
          "label_role_name": "prefill"
        },
        "values": [
          [1790572200, "44.8"],
          [1790572500, "50.17"],
          "...": "..."
        ]
      }
    ]
  }
}
```

要点：

- `result` 是数组，每个元素一条时间序列（由 `by(...)` 子句的标签组合决定有几条）。
- `metric` 是该序列的标签集（不含 `__name__`，因为聚合后没有单一指标名）。
- `values` 是 `[unix_timestamp, "数值字符串"]` 二元组列表，时间戳是**秒级 unix 时间**，值是字符串（需要 `float()` 转换）。
- 一个 `step` 一个点，共 `(end-start)/step + 1` 个点（本例 ~108 个）。
- 无数据的点 VictoriaMetrics 不返回该点（不是返回 0），所以要做空值过滤。

### 5.2 instant 查询返回结构（`resultType: "vector"`）

即时查询（`/api/v1/query?query=...&time=...`）返回 `vector`：

```json
{
  "status": "success",
  "data": {
    "resultType": "vector",
    "result": [
      {
        "metric": {"pod": "...", "label_role_name": "prefill"},
        "value": [1790647583, "1"]
      }
    ]
  }
}
```

- `value` 是单个 `[timestamp, "value"]` 而非 `values` 数组。
- 适合"探测"用途（确认数据存在、发现标签值），不适合看趋势。

### 5.3 错误情况

- `status: "error"` + `errorType` + `error` 字段：PromQL 语法或执行错误。
- `status: "success"` 但 `result: []`：查询语法对但该时间无匹配序列（标签拼错、时间窗口无数据）。
- HTTP 5xx / 连接失败：端点不可达或 DNS 解析失败（如用 `vmselect-vmcluster.monitoring` 从跳板机查就会 NXDOMAIN）。

---

## 6. 从原始结果到可读汇总

108 个原始点直接看没意义，我做了两层降采样：

1. **min / avg / max**：对每条序列所有非空点求最小/均值/最大，给出该指标在该时段的整体范围。
2. **18 桶趋势**：把序列按时间均分成 18 段（9.25h ÷ 18 ≈ 31min/段），每段取均值，输出一行 18 个数字，肉眼即可看趋势与拐点。

示例输出（请求量）：

```
### 请求量(每5m)
  [ decode] min=  0.0 avg=14.78 max=88.0  trend: 44.2 48.17 62.0 49.5 27.5 30.17 9.33 0 0 0 0 0 0 0 0 0 0 0
  [prefill] min=  0.0 avg=14.78 max=86.0  trend: 44.8 50.17 64.5 45.83 27.67 30.67 7.33 0 0 0 0 0 0 0 0 0 0 0
```

一眼看出：前 7 段有流量、之后归零；两角色请求量几乎一致（PD 每请求都过 prefill+decode）。

---

## 7. 常用指标 PromQL 速查（按本次实例参数填好）

公共标签串：

```
L = cluster="bj-caip",
    namespace="ns-e23f5b20fb9b42d3ac674f9691a0b9b1",
    pod=~".*",
    label_version=~"0.0.1",
    label_id="4f0059c1-42d8-4f15-a939-9274b17bfc06"
```

下述查询都按 `label_role_name` 分角色，窗口 `[5m:30s]`，外层 `step=300s`。

| 指标                 | PromQL                                                                                                                                                                                                                         |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 请求量               | `sum by(namespace,label_role_name)(increase(http_requests_total{<L>,handler=~".*(messages\|completions).*"}[5m:30s]))`                                                                                                        |
| 成功推理量           | `sum by(namespace,label_role_name)(increase(vllm:request_success_total{<L>}[5m:30s]))`                                                                                                                                       |
| 并发 running         | `sum by(namespace,label_role_name)(avg_over_time(vllm:num_requests_running{<L>}[5m:30s]))`                                                                                                                                   |
| 并发 waiting         | `sum by(namespace,label_role_name)(avg_over_time(vllm:num_requests_waiting{<L>}[5m:30s]))`                                                                                                                                   |
| TTFT avg             | `sum by(...)(rate(vllm:time_to_first_token_seconds_sum{<L>}[5m:30s])) / sum by(...)(rate(vllm:time_to_first_token_seconds_count{<L>}[5m:30s]))`                                                                              |
| TPOT avg(ms)         | 同上，指标名`vllm:request_time_per_output_token_seconds_*`，整体 `*1000`                                                                                                                                                   |
| E2E avg              | 同上，指标名`vllm:e2e_request_latency_seconds_*`                                                                                                                                                                             |
| ITL avg(ms)          | 同上，指标名`vllm:inter_token_latency_seconds_*`，整体 `*1000`                                                                                                                                                             |
| KV 使用率%           | `avg by(namespace,label_role_name,engine)(avg_over_time(vllm:kv_cache_usage_perc{<L>}[5m:30s]))*100`                                                                                                                         |
| prefix cache 命中率% | `(sum by(...)(increase(vllm:prefix_cache_hits_total{<L>}[5m:30s])) + sum by(...)(increase(vllm:external_prefix_cache_hits_total{<L>}[5m:30s]))) / sum by(...)(increase(vllm:prefix_cache_queries_total{<L>}[5m:30s])) * 100` |
| 成功率%              | `sum by(...)(increase(http_requests_total{<L>,handler=~".*(messages\|completions).*",status=~"2.."}[5m:30s])) / sum by(...)(increase(http_requests_total{<L>,handler=~".*(messages\|completions).*"}[5m:30s])) * 100`          |
| 输出 token           | `sum by(...)(increase(vllm:generation_tokens_total{<L>}[5m:30s]))`                                                                                                                                                           |
| 输入 token           | `sum by(...)(increase(vllm:prompt_tokens_total{<L>}[5m:30s]))`                                                                                                                                                               |

> 分位数（P99/P95/P90/P50）版本：把 `avg` 类指标换成 `histogram_quantile(0.999, sum by(namespace,label_role_name,le)(rate(vllm:<xxx>_bucket{<L>}[5m:30s])))`，`tp` 取 `0.999`/`0.95`/`0.9`/`0.5`。完整模板见 `llm-query.constant.ts`。

---

## 8. 只读边界与合规说明

- 所有 `kubectl` 操作均为 `get` / `describe` 只读，未执行任何变更命令。
- 对 VmSelect 的请求为 HTTP GET（`query` / `query_range`），属只读查询，无写入副作用。
- 经由 `huangqu-cluster-readonly` skill 的固定 SSH 连接（`ssh -F ~/ssh-connections/ssh-config remmina-huangqu`）执行。
- 未读取 Secret 的 `data`/`stringData`；未 exec/port-forward/proxy 进入 pod。
- `vmselect-node-port` 的 NodePort/ClusterIP 是从 `kubectl get svc` 公开状态读出的，非敏感信息。

---

## 9. 复用 Checklist（下次查别的服务）

1. `kubectl get llmserving <服务名> -n <ns> -o yaml` → 取 `metadata.labels.id`（=label_id）、`spec.versions[0].name`（=version）、`metadata.namespace`、`creationTimestamp`/`expirationTime`（=活跃窗口）。
2. 确定 VmSelect 端点：跳板机上 `curl http://172.26.254.216:8481/select/0/prometheus/api/v1/query?query=up`；若该 NodePort 变了，用 `kubectl get svc -n monitoring | grep vmselect` 重新找。
3. 探测 cluster 标签值：`query=count by(cluster)(vllm:cache_config_info{namespace="<ns>",label_id="<id>"})&time=<窗口中间时刻>`。
4. 探测角色/pod：`query=count by(pod,label_role_name)(vllm:num_requests_running{namespace="<ns>",label_id="<id>"})&time=...`。
5. 填模板 → range 查询 `query_range?query=...&start=...&end=...&step=300`。
6. 解析 JSON `data.result[].values`，降采样汇总。
