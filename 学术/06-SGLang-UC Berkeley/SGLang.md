# 1.初识：

RadixAttention；KV 前缀复用；压缩有限状态机；约束解码（JSON）；前端 DSL；API speculative execution

核心：LM 程序是多轮、共享前缀、结构化输出的多调用负载，而通用推理引擎每个请求结束就把 KV cache 丢掉——能不能把「多调用结构」本身当作优化对象？

## 1.1Abstract

LLM 越来越多地用于需要多次生成调用、控制流、结构化输入输出的复杂任务。SGLang = 前端语言 + 运行时后端。

- 前端：Python 内嵌 DSL，提供 `gen / select / extend / fork / join / image / video` 等原语，用原生 Python 控制流表达复杂 prompting 流程；
- 运行时三项优化：
  1. **RadixAttention**：用 radix tree 维护所有请求的 KV cache（LRU 淘汰），跨多次调用自动复用公共前缀；
  2. **压缩有限状态机（compressed FSM）**：把正则约束编译成 FSM，能压缩的多 token 路径一次解出多个 token，而非逐 token mask；
  3. **API speculative execution**：针对只能走 API 的模型（如 GPT-4）优化多调用程序。

在 agent 控制、逻辑推理、few-shot、JSON 解码、RAG、多轮对话等负载上，相对 Guidance / vLLM / LMQL 最高 **6.4× 吞吐**。

```
        "系统提示 + few-shot 示例"（共享前缀）
          ├── 分支 A  ──▶ 复用前缀 KV，只算新增部分
          ├── 分支 B  ──▶ 同上
          └── 分支 C  ──▶ 同上
radix tree 节点 = 一段 token 序列；命中即跳过对应 prefill
LRU 淘汰长时间不用的子树，显存与性能兼得
```

对比：vLLM 的 PagedAttention 解决「一个请求内如何省显存」，SGLang 解决「多个请求/多次调用之间如何复用 KV」。两者不冲突，后来的引擎常一起用。

我的关注点：RadixAttention 的「缓存命中」直接改变 prefill 的工作量，所以它天然和 PD 分离、前缀缓存亲和调度耦合；读的时候留意 cache-aware scheduling 那部分。

## 1.2Introduction

- 趋势：从「聊天」转向「程序化使用 LLM」——agent、tool use、few-shot、self-consistency、tree-of-thought，本质都是「多次、有依赖的生成调用」。
- LM 程序的两个共性：(1) 多个 LLM 调用 + 控制流；(2) 结构化输入/输出（便于组合、嵌入已有系统）。
- 两个痛点：
  - **编程难**：字符串拼接、prompt 调参、脆弱的输出解析、多模态处理、并行控制，代码可读性差（文中示例：等价 OpenAI-API 风格代码要多 2.1× 行数）；
  - **执行慢**：通用引擎不知道负载结构，KV cache 请求结束即丢弃，共享前缀被反复 prefill；约束解码只逐 token mask，浪费可并行解码的机会。
- 方法论：系统性利用 LM 程序的「multi-call structure」做优化；前端与后端可独立使用。
- 待读：3 节 radix tree 的匹配/插入/淘汰与调度策略、4 节 FSM 压缩的正确性条件、5 节 API speculative execution 的投机与校验。
