# 使用 EvalScope Perf 测试 PD 分离系统：操作流程与实验方法

## 1. 测试目标

在 Prefill/Decode（PD）分离场景下，EvalScope Perf 主要用于从**客户端视角**对整个在线推理系统进行标准化性能压测。

典型链路如下：

```text
EvalScope Perf
      │
      │ OpenAI-compatible API
      ▼
AiBrix / Envoy Gateway
      │
      ├───────────────┐
      ▼               ▼
Prefill Pods       Decode Pods
      │               ▲
      └── KV Transfer ─┘
              │
              ▼
          Response
```

EvalScope 负责回答：

- 整套 PD 系统的最大稳定吞吐是多少？
- 不同并发或请求速率下，TTFT、TPOT 如何变化？
- 不同 Input/Output 长度下，系统更偏 Prefill-bound 还是 Decode-bound？
- 不同 P:D 配比下，哪种资源分配更合理？
- 在满足 SLA 的前提下，系统最多能稳定承载多少流量？

EvalScope 主要负责**外部黑盒性能评测**；真正的瓶颈定位仍需要结合 Prefill/Decode 侧的服务端指标。

---

## 2. 测试原则

### 2.1 EvalScope 请求 Gateway，而不是单独请求 P/D Pod

正式测试 PD 系统时，压测入口应该是系统真正对外暴露的 OpenAI-compatible API，例如：

```text
http://<gateway-address>/v1/chat/completions
```

而不是：

```text
Prefill Pod IP
Decode Pod IP
```

因为我们要评测的是完整链路：

```text
Client
→ Gateway
→ Prefill
→ KV Transfer
→ Decode
→ Gateway
→ Client
```

这才对应真实用户视角下的 PD Serving 性能。

---

### 2.2 一次实验尽量只改变一个变量

固定以下参数：

```text
模型版本
硬件型号
卡数
TP / DP / PP / EP
P:D 配比
KV Transfer 配置
max_model_len
max_num_seqs
max_num_batched_tokens
block size
框架版本
Gateway 配置
```

然后只改变：

```text
parallel
request rate
input length
output length
P:D
```

否则结果很难归因。

---

## 4. 第一阶段：基础可用性与 Baseline

首先不要直接上高并发。

建议固定一个简单 workload，例如：

```text
Input  = 1024 tokens
Output = 128 tokens
parallel = 1
```

目的：

- 确认请求链路正常
- 确认 Streaming 正常
- 确认没有 503 / 504 / timeout
- 获取低负载下的基础 TTFT / TPOT
- 确认 EvalScope 统计口径正常

如果 `parallel=1` 时系统已经出现：

```text
TTFT 极高
大量 503
大量 504
timeout
KV Transfer 异常
```

则暂时不建议继续做吞吐测试，应先解决系统链路问题。

---

## 5. 第二阶段：Concurrency Sweep

这是测量系统整体吞吐上限最重要的一步。

固定：

```text
Input  = 1024 tokens
Output = 128 tokens
P:D    = 当前部署配置
```

依次测试：

```text
parallel = 1
parallel = 2
parallel = 4
parallel = 8
parallel = 16
parallel = 32
parallel = 64
parallel = 128
```

每一档建议运行足够多的请求，例如：

```text
200 ~ 1000 requests
```

避免样本量过少导致数据波动。

### 重点记录

```text
Request Throughput
Input Token Throughput
Output Token Throughput

TTFT Avg
TTFT P50
TTFT P90
TTFT P99

TPOT Avg
TPOT P50
TPOT P90
TPOT P99

ITL

Success Rate
503 Count
504 Count
Timeout Count
```

---

## 6. 如何判断系统吞吐饱和点

理想情况下，随着并发增加：

```text
Concurrency ↑
      │
      ▼
Throughput ↑
      │
      ▼
Throughput 增长逐渐变慢
      │
      ▼
达到平台期
      │
      ▼
TTFT / Queue 快速上升
```

例如：

| Parallel | Req/s | Output tok/s | TTFT P99 | TPOT P99 | Success |
| -------: | ----: | -----------: | -------: | -------: | ------: |
|        1 |   0.8 |          100 |       2s |     50ms |    100% |
|        2 |   1.5 |          190 |     2.5s |     52ms |    100% |
|        4 |   2.8 |          350 |       3s |     55ms |    100% |
|        8 |   5.0 |          620 |       4s |     60ms |    100% |
|       16 |   7.5 |          930 |       8s |     65ms |    100% |
|       32 |   8.2 |         1010 |      25s |     80ms |    100% |
|       64 |   8.3 |         1020 |      80s |    120ms |     95% |

可以观察到：

```text
16 → 32
吞吐仍有增长

32 → 64
吞吐几乎不再增长
但 TTFT 大幅恶化
```

因此当前 workload 下：

```text
系统有效吞吐上限 ≈ 8 req/s
```

这就是当前配置的 saturation point 附近。

---

## 7. 第三阶段：Workload Sweep

PD 分离系统对 Input / Output 长度非常敏感。

建议至少设计四类标准 workload：

| Workload    | Input Tokens | Output Tokens | 主要目的      |
| ----------- | -----------: | ------------: | ------------- |
| Short-Short |          256 |           128 | 基础轻负载    |
| Long-Short  |         4096 |           128 | Prefill-heavy |
| Short-Long  |          256 |          1024 | Decode-heavy  |
| Long-Long   |         4096 |          1024 | P+D 重负载    |

### 7.1 Prefill-heavy

```text
Input = 4096 / 8192 / 16384
Output = 16 / 32 / 128
```

主要观察：

```text
Input tokens/s
TTFT
Prefill utilization
Prefill waiting queue
Prefill running requests
KV generation / transfer
```

如果出现：

```text
Prefill utilization ≈ 95%+
Prefill queue 持续增长
Decode utilization 很低
```

则系统偏：

```text
Prefill-bound
```

---

### 7.2 Decode-heavy

```text
Input = 128 / 256
Output = 512 / 1024 / 2048
```

主要观察：

```text
Output tokens/s
TPOT
ITL
Decode utilization
Decode running requests
Decode waiting queue
```

如果出现：

```text
Decode utilization ≈ 95%+
TPOT 快速恶化
Decode queue 持续增长
Prefill utilization 较低
```

则系统偏：

```text
Decode-bound
```

---

## 8. 第四阶段：Rate Sweep

Concurrency Sweep 更适合找容量边界，而 Rate Sweep 更接近真实生产流量。

例如：

```text
request rate:
1 req/s
2 req/s
4 req/s
6 req/s
8 req/s
10 req/s
12 req/s
16 req/s
```

观察：

```text
输入 Request Rate
实际完成 Request Throughput
TTFT
TPOT
Success Rate
Queue
```

理想状态：

```text
输入 1 req/s
实际完成 ≈ 1 req/s

输入 2 req/s
实际完成 ≈ 2 req/s

输入 4 req/s
实际完成 ≈ 4 req/s
```

直到：

```text
输入 12 req/s
实际完成 ≈ 8 req/s
TTFT 开始快速增加
```

则说明系统吞吐已经饱和。

---

## 9. 第五阶段：结合服务端指标定位瓶颈

EvalScope 只能告诉你：

```text
“系统表现怎么样”
```

服务端 Metrics 才能告诉你：

```text
“为什么会这样”
```

建议同时采集：

### Prefill

```text
MLU/GPU utilization
running requests
waiting requests
input tokens/s
KV generation rate
KV transfer latency
```

### Decode

```text
MLU/GPU utilization
running requests
waiting requests
output tokens/s
TPOT / ITL
```

### Gateway / System

```text
503
504
timeout
routing latency
request queue
KV transfer error
network latency
```

例如：

```text
EvalScope:
TTFT P99 = 80s
Throughput = 8 req/s

Prefill:
utilization = 98%
queue = 很高

Decode:
utilization = 35%
queue ≈ 0
```

则可以判断：

```text
Prefill 是主要瓶颈
```

如果：

```text
Prefill utilization = 40%
Decode utilization = 98%
TPOT 大幅恶化
```

则：

```text
Decode 是主要瓶颈
```

如果：

```text
Prefill 不忙
Decode 不忙

但 TTFT 极高
503 / 504 大量出现
```

则需要重点检查：

```text
AiBrix routing
Gateway
KV Transfer
网络
Timeout
Request lifecycle
```

---

## 10. 第六阶段：调整 P:D 配比

只有完成前面的瓶颈分析之后，再调整 P:D。

例如总资源固定为 4 个实例：

```text
1P : 3D
2P : 2D
3P : 1D
```

对于完全相同的 workload：

```text
Input = 4096
Output = 256
```

重新执行 Concurrency Sweep。

结果记录：

| P:D | Max Req/s | Input tok/s | Output tok/s | TTFT P99 | TPOT P99 |
| --- | --------: | ----------: | -----------: | -------: | -------: |
| 1:3 |       ... |         ... |          ... |      ... |      ... |
| 2:2 |       ... |         ... |          ... |      ... |      ... |
| 3:1 |       ... |         ... |          ... |      ... |      ... |

需要注意：

```text
最大吞吐最高
≠
最佳生产配置
```

例如：

```text
3P:1D
Req/s 最大
但 TPOT P99 很差
```

则 Decode 资源不足。

因此更合理的目标是：

```text
在 SLA 约束下寻找最大稳定吞吐
```

---

## 11. SLA Capacity

可以定义生产 SLA，例如：

```text
Success Rate >= 99%

TTFT P99 <= 10s

TPOT P99 <= 100ms
```

那么系统 Capacity 应定义为：

```text
满足以上 SLA 条件时
能够承载的最大 Request Rate
```

而不是简单地：

```text
压到系统完全跑不动之前的最大 QPS
```

这两者意义完全不同。

生产性能评测更关注：

```text
Sustainable Throughput
```

即：

```text
可持续稳定吞吐
```

---

## 12. 第七阶段：真实业务 Workload

固定长度 workload 适合做性能分析，但最终仍需要真实业务数据验证。

建议采集：

```text
真实 Input Length Distribution
真实 Output Length Distribution
真实 Prompt 内容
多轮对话比例
Request Rate 分布
Burst Traffic
```

然后使用 EvalScope 对真实 workload 做最终容量验证。

测试流程因此应包含：

```text
Synthetic Benchmark
        ↓
找系统瓶颈
        ↓
调整 P:D
        ↓
得到合理配置
        ↓
Real Workload Benchmark
        ↓
最终生产容量
```

---

## 13. 推荐的完整实验流程

```text
                PD Benchmark Protocol
                         │
                         ▼
                 ① 环境参数记录
                         │
                         ▼
                      Warm-up
                         │
                         ▼
              ② parallel=1 Baseline
                         │
                         ▼
              ③ Concurrency Sweep
             1 / 2 / 4 / 8 / 16 / ...
                         │
                         ▼
              找到 Saturation Point
                         │
                         ▼
                ④ Workload Sweep
              Short-Short
              Long-Short
              Short-Long
              Long-Long
                         │
                         ▼
             P-bound / D-bound 判断
                         │
                         ▼
                   ⑤ Rate Sweep
                         │
                         ▼
                 模拟生产流量
                         │
                         ▼
                    ⑥ P:D Sweep
              1:3 / 2:2 / 3:1 ...
                         │
                         ▼
                  ⑦ SLA Capacity
                         │
                         ▼
                 ⑧ Real Workload
                         │
                         ▼
             得到最终生产性能结论
```

---

## 14. 推荐实验结果模板

每一轮测试建议至少记录：

```text
[Test Environment]

Model:
Model Version:
Serving Framework:
Framework Version:

Hardware:
Card Number:

TP:
DP:
PP:
EP:

P:D:
KV Transfer Backend:

max_model_len:
max_num_seqs:
max_num_batched_tokens:

--------------------------------------------------

[Workload]

Dataset:
Input Length:
Output Length:

Parallel:
Request Rate:
Request Number:
Stream:

--------------------------------------------------

[Client Metrics]

Request Throughput:
Input Token Throughput:
Output Token Throughput:

TTFT Avg:
TTFT P50:
TTFT P90:
TTFT P99:

TPOT Avg:
TPOT P50:
TPOT P90:
TPOT P99:

ITL:

Success Rate:
503:
504:
Timeout:

--------------------------------------------------

[Server Metrics]

Prefill Utilization:
Prefill Running:
Prefill Waiting:
Prefill Input tok/s:

Decode Utilization:
Decode Running:
Decode Waiting:
Decode Output tok/s:

KV Transfer Latency:
KV Transfer Error:

--------------------------------------------------

[Conclusion]

Saturation Point:

Primary Bottleneck:
Prefill / Decode / KV Transfer / Gateway / Network

SLA Capacity:

Recommended P:D:
```

---

## 15. 最推荐的第一轮实验

为了避免一开始变量太多，可以先固定当前 PD 配置：

```text
Input  = 1024
Output = 128
```

依次执行：

```text
parallel:
1
2
4
8
16
32
64
```

每档：

```text
200 ~ 500 requests
```

记录：

```text
Success Rate

Req/s
Input tok/s
Output tok/s

TTFT P50/P90/P99
TPOT P50/P90/P99

Prefill Utilization
Prefill Queue

Decode Utilization
Decode Queue
```

这一轮的目标只有两个：

```text
1. 找出当前 PD 系统的吞吐饱和点

2. 初步判断瓶颈位于 Prefill 还是 Decode
```

第一轮跑通之后，再继续：

```text
改变 Input / Output
        ↓
确定 P-bound / D-bound
        ↓
改变 P:D
        ↓
重新 Benchmark
```

---

# 总结

EvalScope Perf 在 PD 分离场景下最适合承担：

```text
标准化客户端 Benchmark / Load Generator
```

完整测试方法可以概括为：

```text
固定环境
   ↓
Baseline
   ↓
Concurrency Sweep
   ↓
找到系统饱和点
   ↓
Workload Sweep
   ↓
识别 P/D 瓶颈
   ↓
Rate Sweep
   ↓
模拟真实生产流量
   ↓
P:D Sweep
   ↓
SLA Capacity
   ↓
真实业务验证
```

最终目标不是简单回答：

```text
“这套系统最快是多少 QPS？”
```

而是回答：

```text
在特定 Input/Output workload、
特定 P:D 配比、
特定 SLA 约束下，

这套 PD 分离系统能够稳定承载多少流量，
瓶颈在哪里，
以及应该如何调整 Prefill/Decode 资源配比。
```

这才是一套完整的 PD 分离 Serving 性能评测方法。
