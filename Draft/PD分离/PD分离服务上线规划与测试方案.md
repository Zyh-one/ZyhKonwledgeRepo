# PD 分离服务上线规划与测试方案

## 1. 目标

问题-zyh：PD分离的目标肯定是追求比原来混部更好的性能，对吗？但是现在我不了解混部是一个什么样的运行状态？或者说，一个稳定的推理服务应该是一个什么的运行状况？

推荐整体流程：

```text
现网基线
    ↓
离线功能验证
    ↓
Prefill / Decode 单组件能力测试
    ↓
KV Transfer 验证
    ↓
PD 系统容量测试
    ↓
稳定性测试
    ↓
故障注入
    ↓
Shadow Traffic
    ↓
小流量 Canary
    ↓
逐级放量
    ↓
全量上线
```

---

## 2. 建立现网 Baseline

在测试 PD 服务之前，首先需要明确当前线上混部服务的性能基线。

建议采集以下指标：

| 类型     | 指标                        |
| -------- | --------------------------- |
| 请求规模 | QPS / RPM                   |
| 请求特征 | Input Tokens P50/P90/P99    |
| 请求特征 | Output Tokens P50/P90/P99   |
| 并发     | Concurrent Requests         |
| 延迟     | TTFT P50/P90/P99            |
| 延迟     | TPOT P50/P90/P99            |
| 延迟     | E2E Latency                 |
| 吞吐     | Input / Output Tokens/s     |
| 稳定性   | 请求成功率                  |
| 错误     | 4xx / 5xx / 499 / 503 / 504 |
| 设备     | GPU/MLU 利用率              |
| 显存     | Memory Usage                |
| KV       | KV Cache Usage              |
| Cache    | Prefix Cache Hit Rate       |

其中最重要的是获取真实线上请求长度分布，例如：

```text
Input Tokens:
P50 = 2K
P90 = 8K
P99 = 32K

Output Tokens:
P50 = 500
P90 = 2K
P99 = 8K
```

后续 EvalScope 压测应尽量模拟该分布，而不是只使用固定的 Input / Output 长度。

---

## 3. Prefill 单组件能力测试

在进行完整 PD 压测之前，先测试单个 Prefill 实例的能力。

重点指标：

- Prefill Throughput
- Input Tokens/s
- TTFT
- Waiting Requests
- Active Requests
- 不同 Input Length 下的吞吐变化

测试矩阵示例：

| Input Length | 并发 | TTFT | Prefill Throughput |
| -----------: | ---: | ---: | -----------------: |
|           1K |    1 |    - |                  - |
|           4K |    1 |    - |                  - |
|           8K |    4 |    - |                  - |
|          32K |    4 |    - |                  - |
|          64K |    8 |    - |                  - |

最终应得到：

> 单个 Prefill 实例在不同输入长度和并发下的稳定 Input Tokens/s 上限。

不要只用 QPS 判断 Prefill 能力，因为 Prefill 的计算负载和 Input Tokens 高度相关。

---

## 4. Decode 单组件能力测试

Decode 重点关注生成阶段。

主要指标：

- Output Tokens/s
- TPOT
- ITL
- Active Sequences
- Waiting Sequences
- 最大稳定并发

测试矩阵示例：

| Concurrent Sequences | Output TPS | TPOT P50 | TPOT P99 |
| -------------------: | ---------: | -------: | -------: |
|                    1 |          - |        - |        - |
|                    8 |          - |        - |        - |
|                   32 |          - |        - |        - |
|                   64 |          - |        - |        - |

最终需要明确：

> 单个 Decode 实例能够稳定承载多少活跃 Sequence，以及对应的生成吞吐。

Prefill 和 Decode 的单组件能力明确以后，才能合理规划 P:D 配比。

---

## 5. KV Transfer 链路验证

PD 服务核心链路：

```text
Client
  ↓
Gateway
  ↓
Prefill
  ↓
生成 KV Cache
  ↓
KV Transfer
  ↓
Decode
  ↓
Token Generation
```

建议将 TTFT 拆解为：

```text
TTFT
≈ Gateway Latency
+ Prefill Queue
+ Prefill Compute
+ KV Transfer
+ Decode Queue
+ Decode First Token
```

重点监控：

- KV Transfer Requests
- KV Transfer Success / Failure
- KV Transfer Bytes
- KV Transfer Latency
- KV Transfer Queue Length
- Decode KV Wait Time

否则，即使观察到 TTFT 很高，也无法判断究竟是 Prefill、KV Transfer 还是 Decode 引起。

---

## 6. PD 服务监控体系

### 6.1 Gateway

建议监控：

```text
request_total
request_success_total
request_error_total
request_duration
prefill_route_count
decode_route_count
```

最好能够通过 Request ID 追踪：

```text
Request
  ↓
Prefill Pod A
  ↓
Decode Pod B
```

---

### 6.2 Prefill

建议监控：

```text
active_requests
waiting_requests
prefill_tokens_total
prefill_tokens_per_second
prefill_latency
kv_blocks_generated
```

---

### 6.3 KV Transfer

建议重点监控：

```text
kv_transfer_requests
kv_transfer_success
kv_transfer_failure
kv_transfer_bytes
kv_transfer_latency
kv_transfer_queue_length
decode_wait_kv_latency
```

---

### 6.4 Decode

建议监控：

```text
active_sequences
waiting_sequences
generation_tokens_per_second
TPOT
ITL
kv_receive_latency
```

Grafana / VictoriaMetrics 最好形成如下链路视图：

```text
Gateway
   ↓
Prefill
   ↓
KV Transfer
   ↓
Decode
```

这样发生 TTFT 或 503/504 异常时，可以快速判断瓶颈位置。

---

## 7. PD 系统 Workload 设计

完整 PD 压测至少包含以下场景：

| 场景        | Input | Output | 主要压力       |
| ----------- | ----- | ------ | -------------- |
| Short-Short | 短    | 短     | 基础性能       |
| Long-Short  | 长    | 短     | Prefill        |
| Short-Long  | 短    | 长     | Decode         |
| Long-Long   | 长    | 长     | P + D 综合极限 |
| Mixed       | 随机  | 随机   | 模拟生产       |

分析原则：

### Long Input + Short Output 性能下降

优先检查：

```text
Prefill Capacity
Prefill Queue
KV Transfer
```

### Short Input + Long Output 性能下降

优先检查：

```text
Decode Capacity
Active Sequences
Decode Queue
Output Tokens/s
```

---

## 8. 阶梯式容量测试

不要只进行单点高并发测试，例如直接使用 `parallel=100`。

推荐逐级提高负载：

```text
QPS:
1
2
4
8
12
16
20
30
40
```

每个档位持续固定时间，并记录：

- TTFT P50/P90/P99
- TPOT P50/P90/P99
- Success Rate
- 503 / 504
- Prefill Queue
- Decode Queue
- KV Transfer Latency
- Input / Output Throughput

需要重点寻找系统的：

> Saturation Point（饱和点）

例如：

```text
QPS 8
TTFT P99 = 3s

QPS 10
TTFT P99 = 5s

QPS 12
TTFT P99 = 18s

QPS 14
开始出现 503
```

这种情况下，QPS 12 已经进入明显排队阶段，生产安全容量可能只能设置为 QPS 8~9。

---

## 9. P/D 配比测试

P:D Ratio 是 PD 上线中最重要的实验之一。

不要只测试一个固定配置。

建议测试：

```text
1P : 1D
2P : 1D
4P : 1D
6P : 1D

4P : 2D
6P : 2D
```

观察：

- Prefill Queue
- Decode Queue
- Prefill Tokens/s
- Decode Tokens/s
- TTFT
- TPOT
- KV Transfer

判断方法：

### Prefill Queue 持续增加

```text
Prefill Capacity 不足
```

需要增加 Prefill 资源或者减少 Prefill 压力。

### Decode Queue / Active Sequence 持续增加

```text
Decode Capacity 不足
```

需要增加 Decode 资源。

### Prefill / Decode 都不忙，但 TTFT 很高

重点检查：

```text
KV Transfer
网络
Gateway
路由逻辑
跨节点同步
KV 接收等待
```

---

## 10. Prefix Cache 场景测试

Prefix Cache 会直接改变 Prefill 工作量，因此也会影响最优 P:D Ratio。

建议分别测试：

```text
Prefix Cache Hit Rate:
0%
30%
50%
80%
```

逻辑关系：

```text
Prefix Cache Hit ↑
        ↓
Prefill Compute ↓
        ↓
Prefill Resource Requirement ↓
        ↓
最优 P:D Ratio 改变
```

因此线上 Prefix Cache 命中率较高时，不能简单沿用无 Cache 场景下的 P:D 配比。

---

## 11. 稳定性测试

100 个请求只能用于基础功能测试，不能证明生产稳定性。

建议至少进行：

```text
1h
6h
24h
```

条件允许时进行：

```text
48h / 72h
```

重点检查：

- Memory Leak
- KV Cache 泄漏
- CPU 内存持续增长
- GPU/MLU Memory 异常增长
- FD 数量增长
- 网络连接泄漏
- Waiting Queue 是否长期积压
- Prefix Cache 是否异常
- 503 / 504 是否随运行时间增加
- P/D 负载是否逐渐失衡

尤其需要警惕：

```text
运行 10 分钟正常
运行 12 小时后开始出现 503 / 504
```

---

## 12. 故障注入测试

PD 系统正常运行不代表具备生产可用性，还需要主动制造故障。

建议测试：

- Kill Prefill Pod
- Kill Decode Pod
- Kill Gateway Pod
- KV Transfer 中断
- 节点网络抖动
- Prefill Timeout
- Decode Timeout
- 节点重启
- Pod 重建

例如：

```bash
kubectl delete pod <prefill-pod>
```

观察：

- 已经进入 Prefill 的请求如何处理
- 已生成 KV 的请求是否异常
- 新请求是否能够重新路由
- Gateway 多久感知 Pod 不可用
- 请求是否出现大量 503 / 504
- 是否存在 KV Cache 泄漏
- Pod 恢复后是否自动重新加入服务
- 是否会发生级联故障

---

## 13. Shadow Traffic

如果基础设施允许，正式灰度前建议先使用真实流量进行 Shadow 测试。

```text
                   ┌── 当前生产服务 → 返回用户
线上请求 → Gateway ┤
                   └── PD Shadow → 结果丢弃
```

PD Shadow 可以获得真实的：

- Input Length 分布
- Output Length 分布
- Prefix 分布
- 请求间隔
- Burst 特征
- 并发变化
- 真实业务 Prompt

同时不会影响用户请求。

---

## 14. Canary 灰度上线

Shadow 验证通过后，再进入正式流量。

推荐比例：

```text
1%
 ↓
5%
 ↓
10%
 ↓
20%
 ↓
50%
 ↓
100%
```

每一阶段都设置上线 Gate，例如：

```text
Success Rate >= 99.9%

TTFT P99 <= Baseline × 1.1

TPOT P99 <= Baseline × 1.1

503 Rate < 0.1%

504 Rate < 0.05%
```

任意核心指标明显异常，则停止放量。

---

## 15. Rollback 设计

上线前必须设计快速回滚能力。

推荐 Gateway 同时保留：

```text
                ┌── Mixed Pool
Client → Gateway
                └── PD Pool
```

灰度期间：

```text
Mixed = 90%
PD    = 10%
```

出现异常时：

```text
Mixed = 100%
PD    = 0%
```

回滚最好通过路由权重完成，而不是重新部署模型服务。

目标是做到：

> PD 服务出现异常后，可以快速停止新请求进入 PD Pool。

---

## 16. 上线验收表

建议最终形成统一验收标准：

| 测试项 | 指标                  | 示例目标           |
| ------ | --------------------- | ------------------ |
| 功能   | Success Rate          | > 99.9%            |
| TTFT   | P50/P90/P99           | 不劣于上线阈值     |
| Decode | TPOT P99              | 不劣于上线阈值     |
| 系统   | 503 Rate              | < 0.1%             |
| 系统   | 504 Rate              | < 0.05%            |
| KV     | Transfer Success Rate | > 99.99%           |
| 稳定性 | 24h Soak Test         | 无持续异常         |
| 故障   | Prefill Pod Down      | 自动恢复           |
| 故障   | Decode Pod Down       | 自动恢复           |
| 容量   | Stable Peak QPS       | ≥ 线上峰值 × 1.3 |

生产系统不要按照最大压测极限运行。

推荐：

```text
System Capacity >= Production Peak Traffic × 1.3
```

如果业务流量存在明显突发：

```text
System Capacity >= Production Peak Traffic × 1.5 ~ 2.0
```

---

## 17. 推荐实际执行流程

结合 EvalScope、AiBrix Gateway、Prefill/Decode、KV Transfer、VictoriaMetrics / Grafana，可以采用以下完整流程：

```text
阶段 0
线上混部 Baseline
        ↓
阶段 1
单 Prefill Benchmark
        ↓
阶段 2
单 Decode Benchmark
        ↓
阶段 3
KV Transfer Benchmark
        ↓
阶段 4
1P1D 功能验证
        ↓
阶段 5
多 P / 多 D 功能验证
        ↓
阶段 6
P:D Ratio 实验
        ↓
阶段 7
Short/Long/Mixed Workload
        ↓
阶段 8
QPS 阶梯容量压测
        ↓
阶段 9
Burst Traffic 压测
        ↓
阶段 10
Prefix Cache 场景测试
        ↓
阶段 11
24h+ Soak Test
        ↓
阶段 12
Fault Injection
        ↓
阶段 13
Shadow Traffic
        ↓
阶段 14
1% Canary
        ↓
5%
        ↓
10%
        ↓
20%
        ↓
50%
        ↓
100%
```

---

## 18. 测试分析核心原则

PD 测试不能只回答：

> “这个服务能不能跑？”

而应该回答以下问题：

### 容量

```text
一个 Prefill 实例能处理多少 Input Tokens/s？

一个 Decode 实例能处理多少 Output Tokens/s？

当前 P:D Ratio 是否合理？

整套系统最大稳定 QPS 是多少？
```

### 延迟

```text
TTFT 时间消耗在哪一层？

Prefill Queue 是否堆积？

KV Transfer 是否成为瓶颈？

Decode Queue 是否堆积？
```

### 稳定性

```text
长时间运行是否出现资源泄漏？

单个 P/D Pod 故障是否影响整个系统？

故障是否可以自动恢复？
```

### 生产上线

```text
PD 是否优于当前 Baseline？

是否至少拥有 30% 容量冗余？

是否支持 Canary？

是否支持分钟级甚至更快的路由回滚？
```

---

## 19. 总结

PD 分离上线建议建立统一的五阶段验收体系：

```text
Baseline
    ↓
Capacity
    ↓
Stability
    ↓
Failure Recovery
    ↓
Canary
```

不要仅通过少量请求成功就认为 PD 服务具备上线条件。

真正适合生产的 PD 服务必须同时满足：

- 功能正确
- 性能可控
- P/D 配比合理
- KV Transfer 稳定
- 高负载下不会快速雪崩
- 长时间运行稳定
- 单组件故障能够恢复
- 支持真实流量灰度
- 支持快速回滚

这套测试体系后续可以复用于不同模型、不同并行配置以及不同 KV 传输方案，例如：

- GLM
- DeepSeek
- Qwen
- 不同 TP / DP 配置
- 不同 P:D Ratio
- Mooncake / NIXL
- Prefix Cache
- KV Offload

从而形成一套标准化的 **PD 分离服务生产上线验收流程**。
