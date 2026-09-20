# 大模型推理场景下的 Workload 设计方法（基于 EvalScope）

## 1. 什么是 Workload

在大模型推理场景下，**Workload** 可以理解为：

> 一段时间内，客户端以什么样的请求形态、请求速率、并发规模和持续时间去驱动推理服务。

它不是单指“一个请求”，而是多个维度共同组成的测试负载。

- **Request Shape**：每个请求本身有多重
- **Traffic Pattern**：请求如何进入系统
- **Concurrency**：同时有多少请求处于执行中
- **Duration**：负载持续多长时间

建议将标准 Workload 拆成以下几个维度：

* 请求输入输出长度
  * 包含输入长度，输出长度，PrefixPattern
* 请求发送方式
  * rate，parell
* 请求测试持续时间
  * duration，number

在 EvalScope 中，这些维度都可以映射到具体参数。

---

批注-zyh：输入长度和输出长度可以合为一点描述

## 2. Request Shape：输入与输出长度

LLM 请求最重要的负载参数之一是输入与输出长度：

```text
Input Tokens
Output Tokens
```

输入长度主要决定 Prefill 阶段的计算量，输出长度主要决定 Decode 阶段的工作量。

在 EvalScope 的 random dataset 中，可以通过：

```bash
--min-prompt-length
--max-prompt-length
```

控制输入长度。

EvalScope 可以通过：

```bash
--min-tokens
--max-tokens
```

控制输出长度。

## 3. Prefix Pattern

相同的 Input Length，并不一定代表相同的计算负载。

Prefix构造不匹配，那么两者的 Prefill 工作量完全不同。

因此 Prefix Pattern 也是 Workload 的一部分。

EvalScope random dataset 可以使用：

```bash
--prefix-length
```

控制公共 Prefix 长度。

---

## 4. Traffic Pattern：Request Rate

定义完单请求之后，还需要描述：

> 请求以什么速度进入系统。

EvalScope 对应：

```bash
--rate 5
```

这里需要注意：`5 RPS` 并不一定表示机械地表示每 200ms 一个请求

EvalScope 在 Rate 模式下通常采用 Poisson Arrival。

也就是说：平均 Request Rate = 5 RPS

请求间隔可能类似：

```text
80 ms
410 ms
120 ms
260 ms
...
```

但长期平均值约为：

```text
200 ms / Request
```

这类请求到达方式比固定时间间隔更接近真实线上流量。

---

## 5. Concurrency：Parallel

EvalScope 中：

```bash
--parallel
```

表示同一时刻最多可以有多少个请求处于 in-flight 状态（Max In-Flight Requests）。in-flight表示“已经发送出去但还没有完成响应”的请求

需要特别区分：`--rate` 和`--parallel`

二者含义完全不同。

可以理解为：

```text
--rate
决定请求多快进入系统

--parallel
决定最多允许多少请求同时存在
```

在实际测试中，Rate 和 Parallel 必须联合设计，不能出现相互干扰的情况

---

批注-zyh：“Fixed Rate Workload”和“Concurrency-controlled Workload”应该归纳为“测试场景”一类

## 6. 测试场景

### 6.1 Fixed Rate Workload

对于稳定性测试，一个非常典型的 Workload 是：

```text
Input  = 4K
Output = 512
Rate   = 5 RPS
Mode   = Open-loop
```

其含义为：

> 持续以平均 5 RPS 的外部请求速率向推理服务发送 4K 输入、512 输出的请求。

这种 Workload 主要回答：

> 服务能不能长期稳定承载 5 RPS？

---

### 6.2 Concurrency-controlled Workload

如果目标是测试：

> 固定并发下系统性能如何？

则可以使用：

```bash
--parallel 32
--rate -1
```

例如：

```text
parallel = 32
```

可以理解为：

> 尽可能维持最多 32 个请求同时执行。

这种 Workload 适合测试：

```text
Concurrency Scaling
Latency vs Concurrency
最大稳定并发
Batch 行为
```

例如做并发 Sweep：

```text
parallel = 1
parallel = 4
parallel = 8
parallel = 16
parallel = 32
parallel = 64
```

批注-zyh：Duration和Number可以放在一起，这两个的含义比较简单，介绍的越简单越好

## 7. Duration 与 Number

`--duration` 用于控制压测持续时间。例如：

```bash
--duration 1800
```

表示持续压测 30 分钟。

`--number` 用于限制总请求数；例如 `--number 1000` 表示最多发送 1000 个请求。它适合功能测试、短压测和固定样本数量对比；稳定性测试通常更适合使用 `--duration`，以观察服务在固定负载下持续运行后能否进入稳态。

## 8. Workload Sweep

如果保持 Request Shape 不变，只改变 Request Rate：

```text
Input  = 4K
Output = 512
Prefix = 0
Mode   = Open-loop
Duration = 30min
```

然后依次：

```text
1 RPS
2 RPS
4 RPS
6 RPS
8 RPS
10 RPS
12 RPS
...
```

随着 Rate 增长，系统通常会经历：

```text
低负载区
   ↓
稳定运行区
   ↓
Saturation Point
   ↓
Overload 区
```

目标是找到：

```text
Maximum Sustainable Throughput
```

---

## 9. 推荐 Workload 参数表

| Workload 维度   | 含义                     | EvalScope 参数                                    |
| --------------- | ------------------------ | ------------------------------------------------- |
| Dataset         | Prompt 构造方式          | `--dataset random`                              |
| Input Length    | 单请求 Prefill 工作量    | `--min-prompt-length` / `--max-prompt-length` |
| Output Length   | 单请求 Decode 工作量     | `--min-tokens` / `--max-tokens`               |
| Prefix Length   | 公共 Prefix / Cache 特征 | `--prefix-length`                               |
| Tokenizer       | Token 长度计算依据       | `--tokenizer-path`                              |
| Request Rate    | 请求到达速率             | `--rate`                                        |
| Max Concurrency | 最大在飞请求             | `--parallel`                                    |
| Traffic Mode    | Closed-loop / Open-loop  | `--open-loop`                                   |
| Duration        | 压测持续时间             | `--duration`                                    |
| Request Number  | 最大请求数               | `--number`                                      |
| Streaming       | 流式输出                 | `--stream`                                      |

---
