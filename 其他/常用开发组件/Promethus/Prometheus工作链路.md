# 单个 Prometheus 服务的完整工作链路

## 1. Prometheus 在整套监控体系中的角色

如果只关注一个独立的 Prometheus 服务，可以把它理解成一个围绕“时序指标数据”工作的系统。

它的核心职责主要有四部分：

1. **发现监控目标**
2. **抓取 Metrics**
3. **存储时间序列数据**
4. **通过 PromQL 查询和计算数据**

整体链路可以概括为：

```text
业务服务 / Exporter
        ↓
暴露 /metrics
        ↓
Prometheus 发现 Target
        ↓
定时 Scrape
        ↓
解析 Metric + Labels + Value
        ↓
形成 Time Series
        ↓
写入本地 TSDB
        ↓
PromQL 查询 / 聚合 / 计算
        ↓
Prometheus API 返回结果
        ↓
Grafana / Alertmanager / 其他调用方
```

这里重点讨论的是 **Prometheus 服务本身内部的工作链路**。

---

# 2. 第一阶段：Prometheus 获取监控目标

Prometheus 首先需要知道：我要去哪里抓取 `/metrics`？（target地址）

## 2.1 静态配置

例如：

```yaml
scrape_configs:
  - job_name: "vllm"
    static_configs:
      - targets:
          - "10.0.0.10:8000"
          - "10.0.0.11:8000"
```

Prometheus 会直接按照配置中的地址进行抓取。

---

## 2.2 服务发现

在 Kubernetes 环境中，更常见的是 Service Discovery。

例如：

```text
Prometheus
    ↓
查询 Kubernetes API Server
    ↓
发现 Pod / Service / Endpoint
    ↓
根据 Label / Annotation 过滤
    ↓
生成真正的 Scrape Target
```

问：通过服务发现的方式，需要在Promethus中添加什么配置吗？会有标注API Server地址的环境变量吗？这种方式，中间肯定有相关格式协调配置，对吗？

---

# 3. 第二阶段：目标服务暴露 `/metrics`

Prometheus 本身通常并不主动理解业务内部状态。

它依赖被监控程序主动暴露指标。

例如：

```text
GET /metrics
```

返回：

```text
http_requests_total{method="POST",status="200"} 1024

process_resident_memory_bytes 524288000

mlu_utilization{mlu="0",pod="prefill-0"} 76
```

每一条数据最重要的组成部分是：

```text
Metric Name + Labels + Value
```

例如：

```text
mlu_utilization{mlu="0",pod="prefill-0"} 76
```

---

# 4. 第三阶段：Prometheus 执行 Scrape

Prometheus 会按照一定时间间隔主动访问 Target。

例如：

```yaml
scrape_interval: 15s
```

意味着：

```text
10:00:00 scrape
10:00:15 scrape
10:00:30 scrape
10:00:45 scrape
...
```

因此 Prometheus 的数据采集模式本质上是：Pull 模式

问：这部分配置是promethus的启动yaml中存在的吗？

---

# 5. 第四阶段：Prometheus 解析 Metrics

抓取 `/metrics` 后，Prometheus 会解析其中的数据。

例如：

```text
http_requests_total{
    pod="prefill-0",
    status="200"
} 100
```

Prometheus 会把它理解成一条**时间序列**。

其身份由：

```text
Metric Name + Labels
```

共同决定。

# 8. 第六阶段：写入 Prometheus TSDB

Prometheus 内部包含自己的时间序列数据库：

```text
TSDB
Time Series Database
```

抓取完成后的 Sample 会被持续写入 TSDB。

逻辑上可以理解为：

```text
Metric
+
Labels
        ↓
定位 Time Series
        ↓
Timestamp + Value
        ↓
写入 TSDB
```

例如：

```text
mlu_utilization{pod="prefill-0",mlu="0"}

10:00:00  70
10:00:15  73
10:00:30  81
10:00:45  77
```

Prometheus 存储的核心对象并不是传统关系型数据库中的：

```text
一行记录
```

而是：

> 一条条随时间不断产生 Sample 的 Time Series。

---

# 9. Prometheus 的指标类型

业务程序暴露指标时，通常会使用以下几类指标。

## 9.1 Gauge

Gauge 表示：

> 当前值。

例如：

```text
CPU 利用率
内存使用量
GPU / MLU 利用率
当前请求数
队列长度
温度
```

例如：

```text
mlu_utilization 75
```

它可以：

```text
增加
减少
保持不变
```

---

## 9.2 Counter

Counter 表示：

> 从服务启动以来累计发生了多少次。

例如：

```text
请求总数
错误总数
Token 总数
Cache Hit 总数
```

例如：

```text
http_requests_total 1000
```

下一次可能变成：

```text
http_requests_total 1020
```

一般不会下降，只有进程重启等情况会归零。

因此 Counter 通常不会直接查看原始值，而是通过：

```promql
rate()
```

或：

```promql
increase()
```

分析变化速度。

---

## 9.3 Histogram

Histogram 用于统计：

> 某个数值的分布情况。

例如：

```text
请求延迟
TTFT
TPOT
请求大小
响应大小
```

它通常会产生：

```text
_bucket
_sum
_count
```

例如：

```text
request_duration_seconds_bucket
request_duration_seconds_sum
request_duration_seconds_count
```

然后通过：

```promql
histogram_quantile()
```

计算：

```text
P50
P90
P95
P99
```

---

## 9.4 Summary

Summary 也可以描述数据分布。

不过在大规模 Prometheus 系统中，Histogram 往往更方便进行跨实例聚合。

---

批注：这部分对PromQL的介绍直接转移到“其他/常用开发组件/Promethus/ProQL查询.md”中，在当前文档中，简单批注即可

# 10. 第七阶段：PromQL 查询

PromQL 用于对 TSDB 中的时间序列进行选择、过滤、计算和聚合，详细语法与示例见 [PromQL 查询](./ProQL查询.md)。

---

# 11. 第八阶段：Prometheus 返回查询结果

PromQL 查询结束后，Prometheus 会把结果通过 HTTP API 返回。

例如：

```text
Grafana
    ↓
向 Prometheus 发送 PromQL
    ↓
Prometheus Query Engine
    ↓
读取 TSDB
    ↓
执行 PromQL
    ↓
返回 Query Result
    ↓
Grafana 绘图
```

这里需要注意：

> Grafana 通常并不保存 Prometheus 的原始监控数据。

Grafana 更像：

```text
Visualization Layer
```

真正的数据通常仍然存储在 Prometheus 中。

---

# 12. 一个完整例子：MLU 利用率

假设业务暴露：

```text
mlu_utilization{
    pod="prefill-0",
    mlu="0",
    model="glm"
} 78
```

完整链路为：

```text
MLU Runtime / Driver
        ↓
Exporter 获取 MLU 利用率
        ↓
Exporter 暴露 /metrics
        ↓
mlu_utilization{...} 78
        ↓
Prometheus 每 15 秒 Scrape
        ↓
解析 Metric + Labels + Value
        ↓
确定 Time Series
        ↓
mlu_utilization{
    pod="prefill-0",
    mlu="0",
    model="glm"
}
        ↓
写入 Sample
        ↓
Timestamp + 78
        ↓
写入 TSDB
        ↓
PromQL 查询
        ↓
mlu_utilization{pod="prefill-0"}
        ↓
Prometheus 返回结果
        ↓
Grafana
        ↓
绘制 MLU 利用率曲线
```

---

# 13. 一个完整例子：请求 QPS

业务程序内部：

```text
收到请求
    ↓
http_requests_total++
```

暴露：

```text
http_requests_total{
    pod="prefill-0",
    status="200"
} 1000
```

Prometheus：

```text
Scrape
    ↓
1000
    ↓
15 秒后
    ↓
1030
    ↓
15 秒后
    ↓
1060
```

TSDB 中形成：

```text
10:00:00 → 1000
10:00:15 → 1030
10:00:30 → 1060
```

PromQL：

```promql
rate(http_requests_total[5m])
```

得到：

```text
requests / second
```

然后 Grafana 将其显示为：

```text
QPS 曲线
```

---

# 14. 单个 Prometheus 服务内部完整工作链路

可以最终浓缩为下面这张逻辑图：

```text
                   ┌────────────────────┐
                   │ Application        │
                   │ Exporter           │
                   └─────────┬──────────┘
                             │
                             │ /metrics
                             │
                             ▼
                   ┌────────────────────┐
                   │ Target Discovery   │
                   │ 目标发现            │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ Scrape Manager     │
                   │ 定时抓取 Metrics    │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ Metrics Parser     │
                   │                    │
                   │ Metric Name        │
                   │ Labels             │
                   │ Value              │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ Time Series        │
                   │                    │
                   │ Metric + Labels    │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ Sample             │
                   │                    │
                   │ Timestamp + Value  │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ Prometheus TSDB    │
                   │ 时序数据库          │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ PromQL Engine      │
                   │                    │
                   │ Filter             │
                   │ Rate               │
                   │ Aggregate          │
                   │ Quantile           │
                   └─────────┬──────────┘
                             │
                             ▼
                   ┌────────────────────┐
                   │ HTTP API           │
                   └─────────┬──────────┘
                             │
              ┌──────────────┼───────────────┐
              ▼              ▼               ▼
          Grafana       Alert Rules       API Client
```

可以把一个独立 Prometheus 服务理解成：

> **一个主动从监控目标抓取 Metrics，将 Metric + Labels 转化为时间序列并存入 TSDB，然后通过 PromQL 对这些时间序列进行查询、过滤、计算和聚合的时序监控数据库系统。**

---
