# 缓存 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录“缓存”类别的前端 PromQL。

> **组织说明**：前端“缓存”区块共 4 张图，按从左到右的显示顺序排列（对应 `llmservice-monitor-graph.component.html` 的 `monitor.cache` 区块）：**综合 Prefix 缓存命中率 → Prefix 缓存命中次数 → Prefix 缓存命中率 → KV 缓存利用率**。另有配置探针 `vllmConfigInfo`（非图表，用于判定 Pod 是否为 vLLM 并读取 KV Cache 配置标签）。每张图各对应一条 PromQL，故按图顺序逐节给出。本类别 metric 见 [metric指标.md](./metric指标.md)。

## 1. PromQL 查询

### 1.1 配置探针 `vllmConfigInfo`（非图表）

缓存配置信息。不是展示图，而是探测 Pod 是否暴露 vLLM 指标并读取 KV Cache / 引擎配置标签，价值在标签而不在数值。

```promql
vllm:cache_config_info{
  cluster=~"%(cluster)s",
  namespace="%(namespace)s",
  label_id="%(labelID)s"%(labelRoleName)s
}
```

### 1.2 `vllmPrefixCacheOverallHitsRatePerStep` — 综合 Prefix 缓存命中率

外部 KV 复用命中与本地 Prefix 缓存命中之和占本地查询总数的比例（×100）。一条 PromQL 集成了 3 个 metric（external_prefix_cache_hits_total + prefix_cache_hits_total / prefix_cache_queries_total）。

```promql
(
  sum by (
    namespace,
    label_version%(groupPod)s
  ) (
    increase(
      vllm:external_prefix_cache_hits_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"
      }[%(time)s:30s]
    )
  )
  +
  sum by (
    namespace,
    label_version%(groupPod)s
  ) (
    increase(
      vllm:prefix_cache_hits_total{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"
      }[%(time)s:30s]
    )
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"
    }[%(time)s:30s]
  )
)
*
100
```

### 1.3 `vllmPrefixCacheHitsPerStep` — Prefix 缓存命中次数

KV 复用命中次数（本地 Prefix Cache 命中事件的窗口增量）。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_hits_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.4 `vllmPrefixCacheHitsRatePerStep` — Prefix 缓存命中率

KV 复用命中率（本地命中 / 本地查询 ×100）。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_hits_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:prefix_cache_queries_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
*
100
```

### 1.5 `vllmKVUsagePercPerStep` — KV 缓存利用率

KV Cache 已用容量比例（avg_over_time 后 ×100 展示百分比）。它是容量利用率，不是命中率。

```promql
avg by (
  namespace,
  label_version,
  engine%(groupPod)s
) (
  avg_over_time(
    vllm:kv_cache_usage_perc{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
*
100
```

## 2. 查询关系

```text
Cache 配置探针 → 判定 vLLM + 读取 KV Cache 配置
本地命中/查询 → 综合 Prefix 缓存命中率（含外部命中）/ 命中次数 / 命中率
KV Cache 水位 → 容量压力（利用率，非命中率）
```

本地命中次数不等于节省的 Token 数，KV Cache 利用率也不是命中率。综合命中率把外部 KV 复用命中也算入分子，但分母仍是本地查询数，口径与本地命中率不同。
