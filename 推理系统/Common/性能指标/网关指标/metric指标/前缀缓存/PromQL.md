# 前缀缓存 PromQL

本文依据 `gw-query.constant.ts`，按当前页面顺序收录“前缀缓存”类别的 4 条查询，组成 3 张图：使用率、条目/容量、索引可用性。原始指标说明紧跟在对应 PromQL 后，便于逐项对照。通用统计规则见 [PromQL 统计范式](../../../PromQL统计范式.md)。

这些 metric 来自 AIBrix gateway-plugins，当前通过 `job="aibrix-gateway-plugins"` 筛选。其中 `aibrix_balanced_local_prefix_cache_*` 三项属于内部 balanced 路由实现，只描述路由器为维护前缀感知路由而保存的本地前缀哈希 LRU 元数据，不读取或统计 vLLM 引擎内部的前缀匹配、Prefix Caching 命中和 KV Cache 占用。`aibrix_prefix_cache_indexer_status` 是另一项索引可用性指标，不能与这三项一起归为 balanced 专属。上述指标均没有模型维度。

> **多副本口径：** 每个 gateway-plugins Pod 都维护自己的本地缓存。默认按 `cluster` 聚合适用于总览；排查单副本打满、容量不一致或副本间倾斜时，应改为 `by(cluster,pod)` 展开。

## 1. PromQL 查询与关联指标

### 1.1 `gwPrefixCacheUsagePercPerStep` — 前缀缓存使用率

各 gateway-plugins 副本的使用率先求窗口平均，再按集群等权平均，最后乘 100，输出单位为 `%`。

```promql
avg by (cluster) (
  avg_over_time(
    aibrix_balanced_local_prefix_cache_usage_ratio{
      cluster=~"%(cluster)s",
      job="aibrix-gateway-plugins"
    }[%(time)s:30s]
  )
)
* 100
```

#### 关联指标：`aibrix_balanced_local_prefix_cache_usage_ratio`

Gauge，原始值通常位于 0～1，表示单个 gateway-plugins 副本中 **balanced 路由器本地前缀哈希 LRU 索引的条目容量使用率**，即 `entries / capacity`。其中 entries 是 prefix hash entry 数，capacity 是该 LRU 的条目容量上限；二者都不是 token 数、请求数、vLLM KV block 数或显存字节数。当前查询先求窗口平均，再按 `cluster` 对各副本取平均并乘 100，展示百分比。

**路由适用范围：** 是的，在当前内部实现中，`aibrix_balanced_local_prefix_cache_usage_ratio` 以及对应的 entries、capacity 都是 balanced 路由专属指标。

这是各副本使用率的等权平均，不是 `sum(entries) / sum(capacity)`，也不是缓存命中率。副本容量不同或负载不均时，两种聚合结果可能不同；排查单副本最高水位时可改为 `max by(cluster)` 或 `avg by(cluster,pod)`，但那属于排查改写，不是当前面板口径。按当前源码，`capacity <= 0` 时不会更新 usage_ratio，不能把这种情况自行解释为 0% 或 100%。

**建议定位标签：** `(cluster, namespace, pod)`；完整序列身份以裸样本的全部标签为准。

### 1.2 `gwPrefixCacheEntriesPerStep` — 前缀缓存条目数

对每个副本的 entries 求窗口平均，再按集群求和，输出单位为 entry。

```promql
sum by (cluster) (
  avg_over_time(
    aibrix_balanced_local_prefix_cache_entries{
      cluster=~"%(cluster)s",
      job="aibrix-gateway-plugins"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`aibrix_balanced_local_prefix_cache_entries`

Gauge，单位为 entry，表示单个 gateway-plugins 副本当前保存的本地前缀缓存条目数。多副本的缓存彼此独立，当前面板将各副本窗口平均条目数求和。

结果是“各副本窗口平均条目数之和”，可能为小数，不是窗口末时刻的全局整数快照。

**建议定位标签：** `(cluster, namespace, pod)`。

### 1.3 `gwPrefixCacheCapacityPerStep` — 前缀缓存容量

对每个副本的 capacity 求窗口平均，再按集群求和，与 entries 同图展示，输出单位为 entry。

```promql
sum by (cluster) (
  avg_over_time(
    aibrix_balanced_local_prefix_cache_capacity{
      cluster=~"%(cluster)s",
      job="aibrix-gateway-plugins"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`aibrix_balanced_local_prefix_cache_capacity`

Gauge，单位为 entry，表示单个 gateway-plugins 副本的本地前缀缓存容量上限。当前面板将各副本窗口平均容量求和，与 entries 同图展示。

多副本容量可能不同，当前结果表示各副本窗口平均容量之和。副本扩缩容时，总容量变化应结合 Pod 数变化解释。

**建议定位标签：** `(cluster, namespace, pod)`。

### 1.4 `gwPrefixCacheIndexerStatusPerStep` — 前缀索引可用性

先求每个序列的窗口平均状态，再按 `(cluster,indexer_type)` 取最小值。原始状态为 1=可用、0=不可用，输出按 `local`、`sync` 拆分。

```promql
min by (cluster, indexer_type) (
  avg_over_time(
    aibrix_prefix_cache_indexer_status{
      cluster=~"%(cluster)s",
      job="aibrix-gateway-plugins"
    }[%(time)s:30s]
  )
)
```

#### 关联指标：`aibrix_prefix_cache_indexer_status`

Gauge，原始值 `1` 表示索引可用，`0` 表示不可用。`indexer_type` 的已知取值为：

| 值        | 含义         |
| --------- | ------------ |
| `local` | 本地前缀索引 |
| `sync`  | 同步前缀索引 |

当前查询先对每个序列求窗口平均，再按 `(cluster,indexer_type)` 取最小值，因此：

- 结果为 1：参与聚合的序列在整个窗口内均为可用；
- 结果为 0：至少一个参与聚合的序列在整个窗口内均为不可用；
- 结果位于 0～1：可能存在状态抖动或副本差异，需要按 Pod 展开；
- 无返回序列：只能判读为无数据，不能当作 0。

需要定位具体副本时可改为 `min by(cluster,pod,indexer_type)`，该改写不属于当前面板。

**建议定位标签：** `(cluster, namespace, pod, indexer_type)`。

## 2. 查询关系与边界

```text
单副本 entries / capacity → usage_ratio → 各副本窗口平均 → 集群等权平均 ×100%
各副本 entries、capacity   → 各副本窗口平均 → 集群求和，同图双线
local、sync 索引状态       → 各序列窗口平均 → 按类型取最小值
```

默认聚合隐藏副本差异。出现“平均使用率不高但疑似单副本打满”“索引状态介于 0 和 1”或“容量突然变化”时，应保留 `pod` 标签继续拆解。

当前没有“网关前缀缓存命中次数/查询次数”面板，不能由 entries、capacity 或 usage_ratio 推导命中率。历史记录表明 balanced 缓存指标受路由算法和 `AIBRIX_BALANCED_LOCAL_ROUTER_METRICS_ENABLED` 开关影响；当前页面无数据时，还需区分未启用、未采集、无权限和时间窗无序列。
