# PromQL 基础与监控指标计算

## 1. PromQL 是什么

PromQL 是 Prometheus Query Language 的缩写，是用于查询和计算 Prometheus 时序数据的查询语言。

PromQL 与 SQL 的作用有一定类似性，但查询对象不同：

```text
SQL     -> 查询表、记录和字段
PromQL  -> 查询指标、标签和时间序列
```

PromQL 不仅用于取出某个原始指标，还可以对指标进行筛选、分组、聚合、速率计算、算术运算和时间序列关联。

## 2. PromQL 在监控页面中的作用

在 Predictor 监控页面中，PromQL 承担“数据选择与计算规则”的角色。

它决定：

- 查询哪些基础指标；
- 查询哪个 namespace、Pod、Container 或设备；
- 选择多长的时间窗口；
- 是否对数据求平均、总和或变化速率；
- 是否将多个指标关联起来；
- 最终产生哪些时间序列和图表曲线。

因此，页面标题只是人类可读的简称，PromQL 才是指标真实计算口径的主要依据。

## 3. 指标和标签

一条 Prometheus 指标可以表示为：

```text
mlu_utilization{
  cluster="cluster-a",
  node="machine-01",
  uuid="device-uuid",
  mlu="0",
  type="mlu590"
} 15.8
```

其中：

- `mlu_utilization` 是指标名；
- `{...}` 中是用于区分时间序列的标签；
- `15.8` 是某个采集时刻的指标值。

相同指标名加上不同的标签组合，会形成不同的时间序列。

## 4. 标签筛选

### 4.1 精确匹配

```promql
container_memory_working_set_bytes{namespace="ns-xxx"}
```

只选择 `namespace` 完全等于 `ns-xxx` 的时间序列。

### 4.2 正则匹配

```promql
container_memory_working_set_bytes{pod=~"pod-a|pod-b"}
```

选择 `pod-a` 或 `pod-b`。

常见匹配操作符：

| 操作符 | 含义 |
| --- | --- |
| `=` | 精确相等 |
| `!=` | 不相等 |
| `=~` | 正则匹配 |
| `!~` | 正则不匹配 |

页面中的多选结果通常会被组合为 `pod-a|pod-b` 这样的正则条件。

## 5. 指标类型与 rate

### 5.1 Gauge

Gauge 表示可以上升也可以下降的当前状态，例如：

```text
container_memory_working_set_bytes
mlu_utilization
mlu_memory_utilization
```

这类指标可以直接查询，或使用 `avg_over_time` 计算一段时间的平均值。

### 5.2 Counter

Counter 表示持续累加的计数器，例如：

```text
container_cpu_usage_seconds_total
container_network_receive_bytes_total
container_fs_reads_bytes_total
```

用户通常不关心 Counter 累计到多少，而关心它在单位时间内增长多少，因此需要使用：

```promql
rate(container_network_receive_bytes_total[5m])
```

它表示该 Counter 在最近五分钟内的每秒平均增长速度。

## 6. 常用时间函数

### 6.1 avg_over_time

```promql
avg_over_time(metric[5m])
```

计算某条时间序列在指定时间窗口内的平均值，常用于平滑瞬时波动。

### 6.2 子查询步长

项目中常见：

```promql
avg_over_time(metric[%(time)s:30s])
```

其中：

- `%(time)s` 会被前端替换为当前查询步长或时间窗口；
- `30s` 是子查询的分辨率。

## 7. 分组与聚合

```promql
sum by(cluster, pod, container)(metric)
```

它将具有相同 `cluster + pod + container` 标签的数据求和，并保留这三个标签。

分组标签也影响图表曲线的粒度。例如：

```text
sum by(pod)             -> 每个 Pod 一条曲线
sum by(pod, container)  -> 每个容器一条曲线
```

## 8. 算术运算与派生指标

PromQL 可以用基础指标计算页面所需的派生指标。

例如 CPU 利用率：

```promql
容器 CPU 使用速率
/
容器 CPU Limit
* 100
```

如果某容器实际使用 `0.64 Core`，CPU Limit 为 `4 Core`，则：

```text
0.64 / 4 * 100% = 16%
```

因此，PromQL 不仅能找到数据，还能明确定义页面指标的计算口径。

## 9. 时间序列关联

不同指标可以通过共同标签进行关联。

MLU 利用率查询的结构是：

```promql
mlu_utilization
* on(uuid, type, vf)
group_right
mlu_container
```

两个指标的作用分别是：

```text
mlu_utilization  -> 提供设备利用率
mlu_container    -> 提供设备与 namespace、Pod、Container 的关系
```

`on(uuid, type, vf)` 表示按设备 UUID、类型和虚拟功能进行匹配。`group_right` 用来处理两侧时间序列数量不同的情况，并保留右侧的容器归属信息。

这里的乘法不只是业务数学运算，还承担了按标签匹配和合并时间序列的作用。

## 10. 项目中的 PromQL 模板

前端保存的不总是最终 PromQL，而是带占位符的模板：

```promql
container_memory_working_set_bytes{
  namespace="%(namespace)s",
  pod=~"%(pod)s",
  container=~"%(container)s"
}
```

常见占位符包括：

```text
%(cluster)s
%(namespace)s
%(version)s
%(pod)s
%(container)s
%(path)s
%(time)s
```

用户完成筛选后，前端将当前值填入模板，生成最终查询再发送给 `monitor-server`。

## 11. 从 PromQL 可以确定的内容

通过 PromQL 可以确定：

- 使用了哪些基础指标；
- 查询了哪些资源和标签；
- 使用了多长的时间窗口；
- 是否计算了变化速率；
- 是否进行了平均、求和或其他聚合；
- 利用率的分子和分母分别是什么；
- 不同指标是否通过标签进行了关联；
- 最终按哪些标签拆分图表曲线。

## 12. 仅凭 PromQL 无法确定的内容

PromQL 不能完整说明：

- Exporter 如何从操作系统、驱动或硬件获取原始数据；
- MLU/GPU 利用率在驱动内部的精确统计方法；
- 指标生产者的暴露周期；
- Prometheus 对该目标的实际抓取周期；
- 当前集群中是否有指标缺失、重启或异常样本；
- 某个指标在不同 Exporter 版本中是否存在口径差异。

如果需要继续追溯原始指标的实现，还需要查看 Exporter 文档、Exporter 源码、实际指标端点和 Prometheus 抓取配置。

## 13. 阅读项目 PromQL 的建议顺序

面对一条较长的 PromQL，可以按以下顺序分析：

1. 找出所有基础指标名；
2. 查看标签筛选条件；
3. 判断指标是 Gauge 还是 Counter；
4. 从内向外阅读 `rate`、`avg_over_time` 等函数；
5. 查看 `sum by` 等聚合后保留了哪些标签；
6. 查看指标之间的除法、乘法或其他运算；
7. 查看 `on`、`group_left`、`group_right` 等关联规则；
8. 最后用一句自然语言总结该表达式的计算口径。

## 14. 总结

PromQL 是监控数据链路中的“选择与计算规则”。

```text
Exporter 负责测量并暴露原始指标
Prometheus 采集体系负责采集和保存时间序列
PromQL 负责筛选、聚合、关联和计算
monitor-server 负责平台权限和查询转发
前端负责组织条件和展示查询结果
```

> 想要准确理解一张监控图的含义，不能只看图表标题，还需要查看它使用的 PromQL 和基础指标定义。

