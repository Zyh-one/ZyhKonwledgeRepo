# KV 传输流程（NIXL / PD 分离）

> 本文是对同目录 `PD_NIXL_对话整理/` 归档材料中**流程部分**的总结（原 README 第二~五章），配图直接引用归档目录。
> 指标的源码核实口径与 PromQL 细节见同目录《KV传输（NIXL）》；归档材料按通用上游口径整理，与本部署分支源码核实结论有出入时以《KV传输（NIXL）》为准（主要差异在各节脚注）。

## 1. 交接全流程

![PD 分离整体示意](PD_NIXL_对话整理/images/pd_flow.svg)

以 **Decode Pull / RDMA READ** 模式为例，一次请求的 KV 交接：

1. **Prefill 计算**：生成各 Transformer 层 KV Cache，持有供 Decode 读取的 KV 数据。
2. **协调与准备**：传递请求元数据/远端内存信息；Decode 分配或匹配目标 KV Block，建立或复用连接与内存注册。Handshake 不一定对每次请求完整重做。
3. **Post**：Decode 组织源/目标内存描述符，向 NIXL 后端发起异步 READ 任务。提交成功 ≠ KV 已传完。
4. **Transfer / Completion**：底层通信后台推进搬运，并报告任务完成。
5. **请求级就绪**：vLLM 确认该请求所需 KV（含必要 Rank）均已准备好，Decode 可以继续生成。
6. **通知/资源生命周期**：Pull 模式中 Decode 向 Prefill 发送读取完成通知，帮助 Prefill 安全释放或复用原 KV；与第 5 步时序可能交叠。

**关键区别**：*"一次 NIXL 传输完成"* 不等于 *"整次请求在 vLLM 中完成交接"*；准备、就绪协调、通知与生命周期管理并不全部计入 NIXL 数据传输时间。

## 2. Post、Transfer、Xfer Time 的计时边界

![Post 与 Xfer Time 计时边界](PD_NIXL_对话整理/images/nixl_timeline.svg)

**Post（提交）**：把"源内存段、目标内存段、大小、访问元数据"组成传输任务提交给通信后端；CPU 不逐字节搬运，由 RDMA/通信后端异步执行。

**计时分层**：

```text
T_xfer    ≈ T_post + T_post_return_to_completion
T_handoff ≈ T_prepare/wait + T_xfer + T_ready/sync
```

- 第一式第二项含后端排队、真实数据搬运、进度推进与完成检测，**不能视作纯网络时间**。
- 第二式是**解释性分层**而非可用 Histogram 直接相加的严格公式——多 Rank、多次 Transfer 可相互重叠。

| 流程 | 是否通常算入 Xfer Time | 备注 |
|---|---|---|
| Prefill 完成模型计算 | 否 | 计算阶段 |
| Decode 等待调度、KV 元数据与内存准备 | 否 | 传输前阶段 |
| Post 提交 READ/WRITE | 是 | 同步提交开销 |
| 后端异步搬运与完成检测 | 是 | 数据传输操作阶段 |
| 全部 Rank 的 KV 就绪、vLLM 状态推进 | 不保证 | 请求级状态可能滞后于单次 Transfer |
| 完成通知和 Prefill 资源释放 | 通常不在该 Transfer 计时范围 | 需看具体实现 |

## 3. KV Block 与 NIXL Descriptor 映射

![KV Block 与 Descriptor](PD_NIXL_对话整理/images/descriptor_mapping.svg)

- **KV Block**：vLLM 管理缓存的单位，通常包含若干 Token 对应的 KV 数据。
- **Memory Descriptor**：NIXL 描述一个参与传输的内存段的地址、长度及访问元数据；不是"网络包"，也不是"请求"。
- 实际 KV 物理布局可能按 Layer、K/V、Rank、连续内存块组织；一个逻辑 Token Block 在不同层的存储位置可能分散，某些连续区域又可合并为更少 Descriptor。
- 监控对应：`vllm:nixl_num_descriptors`（每次 Transfer 的描述符数分布）与 `vllm:nixl_post_time_seconds` 联合观察，判断离散内存段增多是否推高提交开销。

> 本分支实测参考：描述符 ≈ （层， 块） 段一一对应，均值约 44503 个/次传输、6.8 GiB/次；详见《KV传输（NIXL）》§2.3/§2.4。

## 4. 三类失败与 KV 过期的位置

![NIXL 失败事件的位置](PD_NIXL_对话整理/images/failure_layers.svg)

| Counter | 直观含义 | 特别注意 |
|---|---|---|
| `vllm:nixl_num_failed_transfers_total` | NIXL 相关失败事件 | 某些上游实现是*综合*计数（含握手/通知失败）；**本部署分支已核实与通知失败分开计数**（见《KV传输（NIXL）》§3.2） |
| `vllm:nixl_num_failed_notifications_total` | 通知发送失败 | 数据可能已成功搬运，但 Prefill 尚不知读取完成 |
| `vllm:nixl_num_kv_expired_reqs_total` | KV 请求级租约过期 | 只在 Prefill 侧记录；不代表传输操作一定失败 |

**三个请求示例**：

- 请求 A：RDMA READ 失败 → data transfer failure。
- 请求 B：KV 已传完、完成通知发送失败 → notification failure。
- 请求 C：P 侧 KV 一直等不到读取/确认，租约超时 → KV expired request（不能仅凭它判定 RDMA 故障）。

**判断方法**：失败总体增加 → 查 NIXL 错误日志、通信状态、P/D Pod 资源；通知失败增多 → 查通知链路与 P 侧资源保持/回收；KV Expired 增多 → 查 Decode 队列、调度等待、P 侧租约与读取完成时间。**不要**用失败 Counter 直接推算用户请求失败率——单请求可能涉及多 Transfer、多 Rank 或重试。
