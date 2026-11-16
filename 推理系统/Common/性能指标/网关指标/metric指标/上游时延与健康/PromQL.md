# 上游时延与健康 PromQL

本文依据 `gw-query.constant.ts`，收录“上游时延与健康”类别的 4 条当前查询，组成 4 张图：上游时延、上游 QPS、健康实例数和健康比例。原始指标说明紧跟在对应 PromQL 后，便于逐项对照。通用统计规则见 [PromQL 统计范式](../../../PromQL统计范式.md)。

这里的上游由 `envoy_cluster_name` 标识。它是 Envoy 配置中的 upstream cluster 名称，不是 VictoriaMetrics 的 `cluster` 标签，也不能默认等同于模型名。

## 1. PromQL 查询与关联指标

### 1.1 `gwUpstreamLatencyTPPerStep` — 上游时延 P99/P90/P50

对上游时延 Histogram 的累计桶求速率，保留 `le` 合并后计算分位数，最后乘 1000，输出单位为 ms。

```promql
histogram_quantile(
  %(tp)s,
  sum by (cluster, le) (
    rate(
      envoy_cluster_upstream_rq_time_bucket{
        cluster=~"%(cluster)s",
        namespace="envoy-gateway-system"
      }[%(time)s:30s]
    )
  )
)
* 1000
```

#### 关联指标：`envoy_cluster_upstream_rq_time_bucket`

Histogram 的 Bucket Counter，样本值单位为 request，`le` 的单位为 seconds。每个桶记录“上游请求耗时小于等于该 `le` 上界”的累计观测数，`le="+Inf"` 包含全部观测。

| `%(tp)s` | 前端序列 |
| --- | --- |
| `0.99` | P99 |
| `0.9` | P90 |
| `0.5` | P50 |

当前聚合只保留 `(cluster,le)`，所以它是全部上游合并分布的分位数，不是单上游时延。若需按上游拆分，必须改为 `sum by(cluster,envoy_cluster_name,le)`，该改写不属于当前面板。

当前只有 `_bucket`，没有 `_sum`/`_count`，不能使用 `rate(_sum) / rate(_count)` 计算精确平均时延。分位数由桶内插值估算，精度受 bucket 边界影响；不同 Histogram 的 P99 不能相加推导端到端 P99。

**建议定位标签：** `(cluster, namespace, pod, envoy_cluster_name, le)`。

### 1.2 `gwUpstreamRequestPerSecondPerStep` — 上游 QPS

按 `(cluster,envoy_cluster_name)` 对上游请求 Counter 求速率，输出单位为 request/s。

```promql
sum by (cluster, envoy_cluster_name) (
  rate(
    envoy_cluster_upstream_rq_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_cluster_upstream_rq_total`

Counter，单位为 request，表示发往各上游 cluster 的累计请求数。当前按 `(cluster,envoy_cluster_name)` 使用 `rate()`，得到每个上游的窗口平均 QPS。

上游重试会使同一 downstream 请求产生多次 upstream 请求，因此上游总 QPS 不强制等于下游 QPS。`envoy_cluster_name` 不必然等于模型名。

**建议定位标签：** `(cluster, namespace, pod, envoy_cluster_name)`。

### 1.3 `gwUpstreamMembershipHealthyPerStep` — 上游健康实例数

对每个上游的健康成员 Gauge 求窗口平均，再按 `(cluster,envoy_cluster_name)` 求和，输出单位为 member。

```promql
sum by (cluster, envoy_cluster_name) (
  avg_over_time(
    envoy_cluster_membership_healthy{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`envoy_cluster_membership_healthy`

Gauge，单位为 member，表示 Envoy 当前观察到的某上游健康成员数。当前查询先求窗口平均，再按 `(cluster,envoy_cluster_name)` 求和，结果可能为小数。

多 Envoy 副本可能分别报告同一批成员，因此当前求和结果可能需要结合 Envoy 副本数解释，不能直接视为全局去重后的物理实例数。

**建议定位标签：** `(cluster, namespace, pod, envoy_cluster_name)`。

### 1.4 `gwUpstreamHealthyRatePerStep` — 上游健康比例

健康成员窗口平均值之和除以成员总数窗口平均值之和，乘 100，按上游拆分，输出单位为 `%`。

```promql
sum by (cluster, envoy_cluster_name) (
  avg_over_time(
    envoy_cluster_membership_healthy{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
/
sum by (cluster, envoy_cluster_name) (
  avg_over_time(
    envoy_cluster_membership_total{
      cluster=~"%(cluster)s",
      namespace="envoy-gateway-system"
    }[%(time)s:30s]
  )
)
* 100
```

#### 关联指标：`envoy_cluster_membership_healthy`、`envoy_cluster_membership_total`

`envoy_cluster_membership_total` 是 Gauge，单位为 member，表示 Envoy 当前观察到的某上游成员总数，是健康比例的分母。

当前结果是“平均成员数之比”，不是“窗口内所有实例始终健康的时间占比”。分母为 0 时无定义。多 Envoy 副本可能分别报告同一批上游成员；比例在分子、分母视图一致时可抵消副本倍数，但副本视图不一致时仍需按 Pod 排查。

**建议定位标签：** 分子和分母均使用 `(cluster, namespace, pod, envoy_cluster_name)`。

## 2. 查询关系

```text
upstream_rq_total       → rate + 按上游聚合 → 各上游 QPS
upstream_rq_time_bucket → rate + 保留 le     → 全部上游 P99/P90/P50
membership_healthy      → 窗口平均 + 求和    → 健康实例数
membership_healthy
  / membership_total    → 同标签比率 ×100%   → 健康比例
```

当前时延与健康/QPS 的聚合维度不同：时延跨所有上游合并，后三者按 `envoy_cluster_name` 拆分。不能直接把总时延 P99 归到某一个上游，也不能把它与 vLLM TTFT P99 相加推导端到端 P99。

## 3. 可扩展指标（当前未接入面板）

| metric | 类型 | 关键标签 | 含义 |
| --- | --- | --- | --- |
| `envoy_cluster_upstream_rq_xx` | Counter | `envoy_cluster_name`、`envoy_response_code_class` | 上游响应码类别计数 |
| `envoy_cluster_upstream_cx_active` | Gauge | `envoy_cluster_name` | 上游活跃连接数 |
| `envoy_cluster_upstream_cx_total` | Counter | `envoy_cluster_name` | 上游连接累计数 |

当前没有按模型的上游 QPS、时延、错误率或健康度；`envoy_cluster_name` 与模型的映射必须以实际 Envoy 配置为准。
