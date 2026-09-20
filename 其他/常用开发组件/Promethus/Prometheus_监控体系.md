# Prometheus 监控体系常见附属服务简要总结

## 1. 总体理解

在生产环境中，Prometheus 往往不是单独工作的。

一个比较完整的监控体系通常会围绕 Prometheus，逐步加入：

- 指标采集组件
- Kubernetes 资源发现与管理组件
- 告警组件
- 长期存储组件
- 全局查询组件
- 可视化组件

可以先用下面这张图建立整体认知：

```text
Application / Exporter
        ↓
   Prometheus
        ↓
 ┌──────┼───────────────┐
 ↓      ↓               ↓
Grafana Alertmanager  Remote Storage
                     / Thanos / Mimir
```

如果是在 Kubernetes 环境中，还经常会加入：

```text
Prometheus Operator
ServiceMonitor
PodMonitor
```

---

# 2. Exporter

Exporter 的核心职责是：

> 把某个系统、设备或服务的状态转换成 Prometheus 可以抓取的 Metrics。

很多系统本身并不会直接暴露 Prometheus 格式的 `/metrics`，这时候就需要 Exporter。

常见组件：

- Node Exporter：CPU、内存、磁盘、网络等主机资源
- GPU / MLU Exporter：加速卡利用率、显存、温度、功耗等
- MySQL Exporter、Redis Exporter：数据库或中间件指标
- Blackbox Exporter：HTTP、TCP、DNS、ICMP 等外部探测

可以把 Exporter 理解成：

> Prometheus 与外部系统之间的“指标转换器”。

问题：对于很多本身就会暴露metrics/接口的服务，应该不需要使用Exporter，对吗？

---

批注：感觉k8s中的Promethus体系的服务还是挺多，你可以将创建一个K8s相关的一级标题，将这些内容放入该一级标题中

# 3. Prometheus Operator

Prometheus Operator 主要用于 Kubernetes 环境。

它的作用是：

> 用 Kubernetes CRD 的方式管理 Prometheus 相关资源。

常见管理对象包括：

```text
Prometheus
ServiceMonitor
PodMonitor
PrometheusRule
Alertmanager
```

因此它更像是：

> Prometheus 在 Kubernetes 中的控制器和自动化管理层。

---

# 4. ServiceMonitor

ServiceMonitor 是 Prometheus Operator 提供的一种 CRD。

它主要描述：

> Prometheus 应该抓取哪些 Kubernetes Service。

典型链路：

```text
ServiceMonitor
      ↓
匹配 Service Label
      ↓
找到 Service
      ↓
找到对应 Endpoint
      ↓
Prometheus Scrape
```

它适合 Kubernetes 中 Pod 动态变化的场景。

---

# 5. PodMonitor

PodMonitor 与 ServiceMonitor 类似。

区别主要在于：

```text
ServiceMonitor
→ 通过 Service 找目标

PodMonitor
→ 直接匹配 Pod
```

如果某个应用没有 Service，或者希望直接抓取 Pod，可以使用 PodMonitor。

---

# 6. kube-state-metrics

kube-state-metrics 会把 Kubernetes API 中的对象状态转换为 Metrics。

例如：

```text
Pod 是否 Ready
Deployment 副本数
Pod Phase
Node 状态
PVC 状态
Job 状态
```

它和 Node Exporter 的区别很重要：

```text
Node Exporter
→ CPU / Memory / Disk 等机器资源状态

kube-state-metrics
→ Pod / Deployment / Node 等 Kubernetes 对象状态
```

---

# 7. Alertmanager

Prometheus 可以执行告警规则，但真正负责告警通知管理的通常是 Alertmanager。

完整流程：

```text
Prometheus
    ↓
执行 Alert Rule
    ↓
告警条件成立
    ↓
发送 Alert
    ↓
Alertmanager
    ↓
聚合 / 去重 / 静默 / 路由
    ↓
邮件 / Webhook / IM / Pager
```

可以简单理解为：

> Prometheus 负责判断“是否应该告警”，Alertmanager 负责“如何通知”。

---

# 8. Grafana

Grafana 是监控体系中的可视化层。

典型流程：

```text
Grafana
   ↓
发送 PromQL
   ↓
Prometheus
   ↓
查询 TSDB
   ↓
返回数据
   ↓
Grafana 绘图
```

Grafana 通常不是 Prometheus 原始指标的主要存储位置，它主要负责：

```text
Dashboard
曲线图
表格
变量筛选
告警展示
```

---

批注：以下的几个服务也可以归纳为“Promethus存储”相关，请你也将其归纳为一个统一的一级标题

# 9. Thanos

当 Prometheus 数据量变大后，单个 Prometheus 会逐渐遇到：

```text
本地存储容量有限
长期保存困难
多个 Prometheus 无法统一查询
高可用问题
```

Thanos 常用于增强 Prometheus：

```text
长期存储
全局查询
高可用
跨 Prometheus 查询
```

典型结构：

```text
Prometheus
    ↓
Thanos Sidecar
    ↓
Object Storage

Grafana
    ↓
Thanos Query
    ↓
多个 Prometheus + 历史数据
```

---

# 10. Mimir / Cortex

Mimir 和 Cortex 更偏向大规模分布式 Prometheus Metrics 后端。

它们主要解决：

```text
横向扩展
长期存储
多租户
高可用
大规模查询
```

相比：

```text
Prometheus
→ 本地 TSDB
```

它们更像：

```text
Distributed Metrics Backend
```

---

# 11. VictoriaMetrics

VictoriaMetrics 是常见的高性能时序存储系统，并兼容 Prometheus 生态。

常见能力：

```text
高压缩率
长期存储
Prometheus Remote Write
PromQL / MetricsQL 查询
较低资源消耗
```

常见链路：

```text
Prometheus
    ↓
Remote Write
    ↓
VictoriaMetrics
```

---

# 12. Remote Write

Remote Write 不是独立服务，而是 Prometheus 的一种重要能力。

它允许 Prometheus：

> 把采集到的 Metrics 持续发送到远程时序数据库。

例如：

```text
Prometheus
    ↓
Remote Write
    ↓
Mimir / VictoriaMetrics / 其他远程存储
```

这样可以形成：

```text
Prometheus
负责采集和短期本地处理

远程系统
负责长期存储和大规模查询
```

---


# 15. 生产环境中的整体关系

一个典型 Kubernetes Prometheus 体系可以抽象为：

```text
                    Kubernetes
                        │
        ┌───────────────┼────────────────┐
        ↓               ↓                ↓
 Application       Node Exporter    kube-state-metrics
 /metrics          /metrics          /metrics
        │               │                │
        └───────────────┼────────────────┘
                        ↓
              ServiceMonitor
              PodMonitor
                        ↓
              Prometheus Operator
                        ↓
                  Prometheus
                        │
          ┌─────────────┼─────────────┐
          ↓             ↓             ↓
       Grafana      Alertmanager   Remote Write
                                      ↓
                           Thanos / Mimir /
                           VictoriaMetrics
```

---

# 16. 各组件职责速记

| 组件                | 核心作用                                   |
| ------------------- | ------------------------------------------ |
| Prometheus          | 指标抓取、TSDB 存储、PromQL 查询、规则计算 |
| Exporter            | 将外部系统状态转换为 Metrics               |
| Node Exporter       | 主机 CPU、内存、磁盘、网络等               |
| GPU / MLU Exporter  | 加速卡利用率、显存、温度、功耗等           |
| kube-state-metrics  | Kubernetes 对象状态                        |
| Prometheus Operator | 在 Kubernetes 中管理 Prometheus 体系       |
| ServiceMonitor      | 描述通过 Service 抓取的目标                |
| PodMonitor          | 描述直接抓取的 Pod                         |
| Grafana             | 指标可视化                                 |
| Alertmanager        | 告警聚合、去重、路由和通知                 |
| Pushgateway         | 暂存短生命周期任务主动 Push 的指标         |
| Blackbox Exporter   | 外部探测 HTTP/TCP/DNS/ICMP 等服务          |
| Thanos              | 多 Prometheus 全局查询、长期存储、高可用   |
| Mimir / Cortex      | 大规模分布式 Metrics 后端                  |
| VictoriaMetrics     | 高性能时序存储和 Prometheus 兼容后端       |
| Remote Write        | 将 Prometheus 数据发送到远程存储           |

---

# 17. 建议的学习顺序

如果当前主要是在 Kubernetes + AI Infra 场景下使用 Prometheus，可以按三层理解：

```text
第一层：

Exporter
    ↓
Prometheus
    ↓
Grafana
```

然后补：

```text
第二层：

Prometheus Operator
ServiceMonitor
PodMonitor
kube-state-metrics
Alertmanager
```

最后遇到大规模生产问题时再学习：

```text
第三层：

Remote Write
Thanos
Mimir
VictoriaMetrics
```

---

# 18. 一句话总结

生产环境中的 Prometheus 监控体系，本质上是在 Prometheus 的：

```text
采集
+
存储
+
查询
```

能力周围，逐渐增加：

```text
Exporter       → 指标来源
Operator       → Kubernetes 管理
ServiceMonitor → Target 管理
Alertmanager   → 告警
Grafana        → 展示
Thanos/Mimir   → 大规模存储与查询
```

最终形成一整套 Metrics 可观测性系统。
