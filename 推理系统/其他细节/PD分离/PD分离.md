# PD 分离

大模型推理可以分为两个特征明显不同的阶段：

- **Prefill（P）**：一次处理完整的输入序列，生成首个 token 以及后续解码所需的 KV Cache。矩阵规模较大，通常更偏向计算密集型，直接影响 **TTFT（Time To First Token）**。
- **Decode（D）**：复用 KV Cache，每轮只生成一个 token。单轮计算量较小，但需要反复读取模型权重和 KV Cache，通常更偏向访存密集型，直接影响 **TPOT（Time Per Output Token）**。

## 为什么要进行 PD 分离

传统推理系统将 Prefill 和 Decode 混合部署在同一组 GPU 上，并通过连续批处理提高设备利用率。这种方式简单，但 DistServe 指出了两个关键问题。

第一，两个阶段会相互干扰。长 Prompt 的 Prefill 会占用较长的连续计算时间，使正在进行的 Decode 暂停，造成 TPOT 抖动；反过来，大量 Decode 请求也会挤占调度空间，延长新请求的 TTFT。系统很难同时满足两类延迟 SLO。

第二，两个阶段的最优资源配置并不相同。Prefill 和 Decode 对算力、显存带宽、批大小以及并行策略的偏好不同。混合部署会将它们绑定到同一套扩缩容和并行方案中，往往只能偏向其中一个阶段，或者依靠资源冗余同时满足 TTFT 与 TPOT。

PD 分离将两类计算放到独立的实例（通常是不同 GPU）上：请求先由 Prefill 实例计算并生成 KV Cache，再将 KV Cache 传输给 Decode 实例继续生成。这样可以分别为两个阶段设置批处理、并行策略和副本数，也能隔离长 Prefill 对 Decode 延迟的影响。DistServe 因此将优化目标定义为 **goodput**：在 TTFT、TPOT 及其达标率约束下，系统能够稳定服务的最大请求速率，而不只是脱离延迟约束讨论吞吐量。

## 分离带来的新问题

PD 分离并不是无成本的。模型权重通常需要在两类实例上各自保留；Prefill 结束后还要跨实例传输 KV Cache，长上下文下通信开销尤其明显；此外，请求路由、P/D 实例比例和负载均衡也会直接影响整体性能。因此，PD 分离是否收益，取决于阶段隔离带来的收益能否覆盖 KV Cache 传输与额外资源成本。DistServe 的做法是结合工作负载与 SLO，分别选择 P、D 阶段的并行和资源配置，并依据集群带宽进行放置。

## 参考资料

- [DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model Serving](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin)，OSDI 2024。

补充：

* 在PD分离服务中，TTFT指标的产生和Decode节点没有关系，整个 Prefill计算和产生首token的过程都是在Prefill节点发生的，对吗？

不完全对，在实际P/D分离场景中，“首token”返回有两种路径

**路径一：**Prefill 生成首 token，并直接流式返回

Prefill节点完全prompt prefill计算，采样生成首token，直接返回客户端

此时，KVCache传输对TTFT影响较小

**路径二**：Prefill 只完成前置计算，统一由 Decode 链路返回 token

```
客户端请求
  ↓
Prefill 节点执行 Prefill
  ↓
生成 KV Cache，可能同时算出首 token
  ↓
KV Cache 和相关状态传给 Decode
  ↓
Decode 接管请求
  ↓
通过 Decode 链路向客户端返回首 token
  ↓
继续生成后续 token
```

此时，KVCache传输对TTFT影响较大
