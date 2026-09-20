# 外部缓存 PromQL

本文依据 `llm-query.constant.ts` 中的业务注释，收录“外部缓存”类别的前端 PromQL。

**方向标签**：KV 卸载系列 6 张图按 `transfer_type` 区分方向，两张方向图共用同一 PromQL 模板，仅 `transfer_type` 取值不同：

- `CPU_to_MLU`（i18n `kvOffloadCPG` = “CPU → AI 卡”）：从 CPU 内存 promote 回 AI 卡（命中回填方向）；
- `MLU_to_CPU`（i18n `kvOffloadGPC` = “AI 卡 → CPU”）：从 AI 卡 offload 到 CPU 内存（卸载写出方向）。

**口径提醒（重要）**：`vllm:external_prefix_cache_hits_total` / `vllm:external_prefix_cache_queries_total` 单位为 **token**（非命中/查询事件次数），与 `缓存/metric指标.md` 的本地 prefix cache 指标同口径。命中率 = 命中 token 数 / 查询 token 数，是 token 级比例。

## 1. PromQL 查询

### 1.1 `vllmExternalPrefixCacheHitsPerStep` — External Prefix 缓存命中次数

External Prefix 缓存命中次数（窗口内命中的 token 增量）。

```promql
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
      label_id="%(labelID)s"%(labelRoleName)s
    }[%(time)s:30s]
  )
)
```

### 1.2 `vllmExternalPrefixCacheHitsRatePerStep` — External Prefix 缓存命中率

External Prefix 缓存命中率（命中 token / 查询 token ×100）。**一条图聚合 2 个 metric**：分子 `external_prefix_cache_hits_total`、分母 `external_prefix_cache_queries_total`。

```promql
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
    vllm:external_prefix_cache_queries_total{
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

### 1.3 `vllmKVOffloadTotalBytesPerStep`（CPU→AI 卡）— KV 卸载传输字节数

KV 卸载传输字节数（`transfer_type="CPU_to_MLU"`，CPU → AI 卡方向）。

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  increase(
    vllm:kv_offload_total_bytes_total{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="CPU_to_MLU"
    }[%(time)s:30s]
  )
)
```

### 1.4 `vllmKVOffloadTotalBytesPerStep`（AI 卡→CPU）— KV 卸载传输字节数

PromQL 与 §1.3 完全一致，仅将 `transfer_type="CPU_to_MLU"` 改为 `transfer_type="MLU_to_CPU"`（AI 卡 → CPU 方向）。

### 1.5 `vllmKVOffloadSizeTPCPGPerStepConfig`（CPU→AI 卡）— KV 卸载传输大小分位

每次 KV 卸载传输的数据大小分布（`transfer_type="CPU_to_MLU"`）。**一条图聚合 5 条 query**：4 条分位（P99.9 / P95 / P90 / P50，均由 `kv_offload_size_bucket` 经 `histogram_quantile` 计算）+ 1 条均值（由 `kv_offload_size_sum` / `kv_offload_size_count` 计算）。两张方向图（本节 CPU→AI 卡、§1.6 AI 卡→CPU）共用这组模板，仅 `transfer_type` 取值不同。

> **大传输场景失真警告**：`kv_offload_size` Histogram 的有限桶边界由 vLLM 源码 `TRANSFER_SIZE_BUCKETS` 硬编码，最大有限桶仅 200MB（详见 [metric指标.md §4](./metric指标.md) 的桶边界口径）。GLM-5 等大模型单次 KV offload 传输为 GB 量级，全部塌进 `+Inf` 桶，导致 `histogram_quantile` 退回返回 200MB 作为 cap 伪值——**4 条分位（P99.9/P95/P90/P50）在此场景全部失真**，典型现象是 P99.9 ≪ avg。**均值 query（`rate(_sum)/rate(_count)`）与 §1.3/1.4 传输字节总量不受桶影响，可信。** 分位图在大传输场景仅供参考，不作为结论依据。

分位模板（实例化为 `%(tp)s` = 0.999 / 0.95 / 0.90 / 0.5 共 4 条）：

```promql
histogram_quantile(
  %(tp)s,
  sum by (
    namespace,
    label_version,
    le%(groupPod)s
  ) (
    rate(
      vllm:kv_offload_size_bucket{
        cluster=~"%(cluster)s",
        namespace="%(namespace)s",
        pod=~"%(pod)s",
        label_version=~"%(version)s",
        label_id="%(labelID)s"%(labelRoleName)s,
        transfer_type="CPU_to_MLU"
      }[%(time)s:30s]
    )
  )
)
```

均值模板（`rate(_sum) / rate(_count)`）：

```promql
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:kv_offload_size_sum{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="CPU_to_MLU"
    }[%(time)s:30s]
  )
)
/
sum by (
  namespace,
  label_version%(groupPod)s
) (
  rate(
    vllm:kv_offload_size_count{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="CPU_to_MLU"
    }[%(time)s:30s]
  )
)
```

### 1.6 KV 卸载传输大小分位（AI 卡→CPU）

PromQL 组与 §1.5 完全一致，仅将所有 `transfer_type="CPU_to_MLU"` 改为 `transfer_type="MLU_to_CPU"`。

### 1.7 `vllmKVOffloadSizeBucketPerStep`（CPU→AI 卡）— KV 卸载传输大小热力图

KV 卸载每次传输大小的原始分布热力图（`transfer_type="CPU_to_MLU"`），基于 `kv_offload_size_bucket` 的 `increase()`。

> **热力图失真警告**：与 §1.5 分位图同源，均受 `TRANSFER_SIZE_BUCKETS` 桶边界限制（最大有限桶 200MB）。GB 级传输塌进 `+Inf` 桶后，200MB 以上区间无法再细分密度，热力图在大传输场景只能看到 `le=+Inf` 一格堆积、其余有限桶几乎为 0，**分布参考价值有限**。详见 [metric指标.md §4](./metric指标.md) 的桶边界口径。

```promql
sum by (
  namespace,
  label_version,
  le%(groupPod)s
) (
  increase(
    vllm:kv_offload_size_bucket{
      cluster=~"%(cluster)s",
      namespace="%(namespace)s",
      pod=~"%(pod)s",
      label_version=~"%(version)s",
      label_id="%(labelID)s"%(labelRoleName)s,
      transfer_type="CPU_to_MLU"
    }[%(time)s:30s]
  )
)
```

### 1.8 KV 卸载传输大小热力图（AI 卡→CPU）

PromQL 与 §1.7 完全一致，仅将 `transfer_type="CPU_to_MLU"` 改为 `transfer_type="MLU_to_CPU"`。

## 2. 查询关系

```text
External Prefix 查询 token → External 命中 token → External 命中率
KV Offload 传输字节总量（按 transfer_type 分向） → CPU/AI 卡间数据搬运量
KV Offload 单次传输大小 → 分位（P99.9/P95/P90/P50 + 均值）/ 热力图（bucket 原始分布）
```

External 命中 token 与 KV Offload 字节不是同一量纲（token vs byte），不可直接相加/比较。KV 卸载传输字节数（`increase`）是窗口总量、不是带宽；要算带宽用 `rate()`。单次传输大小分位/热力图描述“每次传输的粒度”，与传输总量是不同维度。
