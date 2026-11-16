# 网关流量 PromQL

本文依据 `gw-query.constant.ts`，收录“网关流量”类别的 5 条当前查询：请求总量、QPS、状态码类别数量、成功率和活跃请求。原始指标说明紧跟在对应 PromQL 后，便于逐项对照。通用统计规则见 [PromQL 统计范式](../../../PromQL统计范式.md)。

当前查询以 `namespace="envoy-gateway-system"` 筛选 Envoy Proxy 数据面。这里的下游是“客户端 → Envoy”，与“Envoy → 推理服务”的上游指标应分开解释。

## 1. PromQL 查询与关联指标

### 1.1 `gwRequestTotalPerStep` — 网关请求总量

对 downstream 请求 Counter 使用 `increase()`，得到每个 step 窗口内的请求增量，输出单位为 request。

```promql
sum by (cluster) (
  increase(
    envoy_http_downstream_rq_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_http_downstream_rq_total`

Counter，单位为 request，表示下游 HTTP Connection Manager 的累计请求数。

- `increase()`：得到每个 step 窗口内的请求增量，单位仍为 request；
- `rate()`：得到窗口平均每秒请求数，单位为 request/s；
- 原始 Counter 读数会受进程重启影响，不应直接作为图中的窗口请求量。

当前结果是窗口请求量，不是进程启动以来的累计原始读数。比较不同长度窗口时，应使用下面的 QPS，而不是直接比较窗口总量。

**建议定位标签：** `(cluster, namespace, pod, envoy_http_conn_manager_prefix)`。

### 1.2 `gwRequestPerSecondPerStep` — 网关 QPS

对同一个 Counter 使用 `rate()`，输出窗口平均请求速率，单位为 request/s。

```promql
sum by (cluster) (
  rate(
    envoy_http_downstream_rq_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_http_downstream_rq_total`

指标定义同上。这里对原始 Counter 求窗口平均速率，再跨 Envoy Pod 和其他被聚合标签求和，展示集群级下游 QPS。它没有模型或租户维度。

**建议定位标签：** `(cluster, namespace, pod, envoy_http_conn_manager_prefix)`。

### 1.3 `gwRequestStatusPerStep` — 状态码类别数量

按 `envoy_response_code_class` 统计窗口内 2xx、3xx、4xx、5xx 请求增量，输出单位为 request。

```promql
sum by (cluster, envoy_response_code_class) (
  increase(
    envoy_http_downstream_rq_xx{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_http_downstream_rq_xx`

Counter，单位为 request，按最终响应码类别统计下游请求。`envoy_response_code_class` 使用单字符值：

| 原始标签值 | 前端显示 | 当前成功率是否计入分子 |
| --- | --- | --- |
| `"2"` | 2xx | 是 |
| `"3"` | 3xx | 是 |
| `"4"` | 4xx | 否 |
| `"5"` | 5xx | 否 |

筛选时不能误写为 `envoy_response_code_class="2xx"`。2xx 不保证流式响应完整或模型业务成功，4xx/5xx 也应结合具体路由和上游响应继续定位。

**建议定位标签：** `(cluster, namespace, pod, envoy_http_conn_manager_prefix, envoy_response_code_class)`。

### 1.4 `gwRequestSuccessRatePerStep` — 网关成功率

窗口内 2xx 与 3xx 响应增量之和除以下游请求总增量，乘 100，输出单位为 `%`。

```promql
sum by (cluster) (
  increase(
    envoy_http_downstream_rq_xx{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system",
      envoy_response_code_class=~"2|3"
    }[%(time)s:30s]
  )
)
/
sum by (cluster) (
  increase(
    envoy_http_downstream_rq_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
* 100
```

#### 关联指标：`envoy_http_downstream_rq_xx`、`envoy_http_downstream_rq_total`

当前成功率是 `(2xx + 3xx) / downstream_rq_total × 100%`。这是产品定义的网关 HTTP 成功率：3xx 被视作成功，但不代表模型业务成功率；2xx 也不能单独证明流式响应完整结束或模型结果满足业务要求。

分子、分母来自不同 Counter，窗口边界和在途请求可能造成短期波动，不宜把它当作同一批请求的严格终态对账。分母为 0 时比率无定义。

**建议定位标签：** 分子使用 `(cluster, namespace, pod, envoy_http_conn_manager_prefix, envoy_response_code_class)`，分母使用 `(cluster, namespace, pod, envoy_http_conn_manager_prefix)`。

### 1.5 `gwRequestActivePerStep` — 活跃请求

对正在处理的下游请求 Gauge 求窗口平均，再跨序列求和，输出单位为 request。

```promql
sum by (cluster) (
  avg_over_time(
    envoy_http_downstream_rq_active{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_http_downstream_rq_active`

Gauge，单位为 request，表示 Envoy 正在处理的下游请求数。当前查询先对每个序列求窗口平均，再按 `cluster` 求和，因此展示的是平均活跃请求数，而不是窗口末瞬时值，结果可以是小数。

活跃请求升高需要结合 QPS 和上游时延判断：可能是到达流量增加，也可能是上游处理变慢导致请求滞留。

**建议定位标签：** `(cluster, namespace, pod, envoy_http_conn_manager_prefix)`。

## 2. 查询关系

```text
downstream_rq_total ─┬→ increase → 窗口请求总量
                     └→ rate     → 窗口平均 QPS
downstream_rq_xx    ─┼→ 按 class 拆分 → 状态码类别数量
                     └→ class=2|3 / rq_total → 网关 HTTP 成功率
downstream_rq_active ─→ 窗口平均后求和 → 平均活跃请求数
```

## 3. 可选扩展（当前未接入）

### 3.1 下游 HTTP 连接数

以下查询来自设计草案，**不在当前 `gw-query.constant.ts` 和 12 张面板中**：

```promql
sum by (cluster) (
  increase(
    envoy_http_downstream_cx_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_http_downstream_cx_total`

Counter，单位为 connection，表示下游 HTTP 连接累计数，带 `envoy_http_conn_manager_prefix` 标签。上述查询计算窗口新增连接数。连接数不等于请求数，一个连接可承载多个请求。

### 3.2 监听器下游连接数（仅指标说明，无当前查询）

`envoy_listener_downstream_cx_total` 是 Counter，单位为 connection，按 `envoy_listener_address` 统计监听器收到的下游连接。它与 HTTP Connection Manager 的连接统计层级不同，未核对埋点边界前不应直接相加。

## 4. 当前边界

当前指标没有 model、租户 `label_id` 或 `label_version` 维度，不能按模型或租户拆分网关 QPS、状态码和成功率。若 Envoy 暴露其他路由或监听器标签，可在裸查询中用于进一步定位，但不能据此臆造模型维度。
