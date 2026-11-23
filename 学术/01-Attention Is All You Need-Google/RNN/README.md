# RNN 图文学习资料

以 Vanilla RNN 自回归语言模型为主线的入门材料，覆盖序列建模、前向传播、多层结构、推理缓存与 Transformer 对比，作为《Attention Is All You Need》的前置背景阅读。

## 阅读顺序

1. [RNN 核心思想与整体结构](01-RNN核心思想与整体结构.md) — 隐藏状态递推公式、语言模型整体架构、与 Attention 的本质区别
2. [RNN 前向传播与多层堆叠](02-前向传播与多层堆叠.md) — 单步张量维度、权重共享与串行依赖、多层二维结构、PyTorch 示例
3. [RNN 自回归推理与状态缓存](03-自回归推理与状态缓存.md) — 生成流程、Teacher Forcing、隐藏状态缓存的规模特征
4. [RNN 局限性与 Transformer 对比](04-局限性与Transformer对比.md) — 与 Causal Transformer 的逐项对比、三类主要困难、结论速记

## 说明

- 图片统一放在仓库 `source/学术/01-Attention Is All You Need-Google/RNN/<文档名>/` 下，文档内使用相对路径引用（路径含空格，链接中编码为 `%20`）。
- 全部图像为教学用原创简化示意图，参数与 Token IDs 均为示例数据。
