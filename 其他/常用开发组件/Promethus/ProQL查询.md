# PromQL 查询

数据进入 TSDB 后，就可以通过 PromQL 查询。

PromQL 的本质可以理解成：

> 对 Time Series 进行选择、过滤、计算和聚合。

整个过程大致是：

```text
选择 Metric
    ↓
根据 Label 过滤
    ↓
选择时间范围
    ↓
数学计算
    ↓
聚合
    ↓
得到最终查询结果
```

---

## 1. 选择 Metric

最简单的查询：

```promql
mlu_utilization
```

表示：

> 查询所有名字叫做 `mlu_utilization` 的时间序列。

如果存在：

```text
mlu=0
mlu=1
mlu=2
mlu=3
```

就会同时得到多条曲线。

---

## 2. 通过 Label 过滤

例如：

```promql
mlu_utilization{pod="prefill-0"}
```

进一步筛选：

```promql
mlu_utilization{
    pod="prefill-0",
    mlu="0"
}
```

Prometheus 实际上是在：

```text
大量 Time Series
        ↓
根据 Label Matcher
        ↓
挑选符合条件的 Time Series
```

---

## 3. 计算 Counter 的速率

例如：

```text
http_requests_total
```

是 Counter。

假设：

```text
10:00:00 → 100
10:00:15 → 130
10:00:30 → 160
```

真正关心的通常不是：

```text
当前累计 160 个请求
```

而是：

> 每秒处理多少请求？

因此可以使用：

```promql
rate(http_requests_total[5m])
```

含义为：

> 根据最近 5 分钟内的 Counter 数据计算平均每秒增长速度。

它可以近似理解成：

```text
Request Counter
      ↓
最近 5 分钟数据
      ↓
计算增长量
      ↓
除以时间
      ↓
Requests / Second
```

也就是 QPS。

---

## 4. 聚合

如果系统里有多个 Pod：

```text
prefill-0
prefill-1
prefill-2
```

可以使用：

```promql
sum(
  rate(http_requests_total[5m])
)
```

得到整个服务的 QPS。

也可以：

```promql
sum by (pod) (
  rate(http_requests_total[5m])
)
```

表示：

> 按 Pod 分组，计算每个 Pod 的 QPS。

这里：

```text
by(pod)
```

实际上就是利用 Label 维度进行聚合。

---

## 5. 计算平均值

例如：

```promql
avg(mlu_utilization)
```

表示计算所有 MLU 的平均利用率。

也可以：

```promql
avg by (pod) (
  mlu_utilization
)
```

表示：

> 分别计算每个 Pod 内所有 MLU 卡的平均利用率。

---

## 6. PromQL 查询的数据流

因此一个典型 PromQL：

```promql
sum by (pod) (
  rate(http_requests_total[5m])
)
```

可以拆成：

```text
http_requests_total
        ↓
找到所有 Request Counter Time Series
        ↓
[5m]
选择每条时间序列最近 5 分钟的数据
        ↓
rate()
计算每条时间序列的每秒速率
        ↓
sum by(pod)
按照 pod Label 分组求和
        ↓
最终得到每个 Pod 的 QPS
```

---

