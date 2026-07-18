# nanoGPT

## 总体介绍

1. 模型推理 = 前向传播 \+ 采样/解码；模型训练 = 前向传播 \+ 计算 loss \+ 反向传播 \+ 梯度累积/同步 \+ 参数更新

    1. 补充：训练模式下的前向传播本身也会和推理有所不同，比如dropout会开启 等等

2. 推理流程：只需要算出下一个 token 概率；

    1. 核心：根据已有 token，预测下一个 token

3. 训练流程

    1. 先做前向传播得到logits，用logits和真实答案和标签labels计算loss

    2. 反向传播（loss\.backward\(\)）

        1. 从训练损失loss开始，沿着计算图反向传播，计算每个参数的梯度

        ```Plain Text
        W_Q.grad
        W_K.grad
        W_V.grad
        W_O.grad
        MLP.weight.grad
        embedding.weight.grad
        lm_head.weight.grad
        ...
        ```

        2. 梯度：当前这个参数对 loss 的影响方向和影响程度。

    3. 梯度累积：训练时会使用梯度累积，gradient\_accumulation\_steps = 4；大致流程如下

        ```Plain Text
        第1个 micro-batch -> forward -> loss -> backward -> 梯度暂存
        第2个 micro-batch -> forward -> loss -> backward -> 梯度继续累加
        第3个 micro-batch -> forward -> loss -> backward -> 梯度继续累加
        第4个 micro-batch -> forward -> loss -> backward -> 梯度继续累加
        ```

        1. 然后执行一次参数更新optimizer\.step\(\)，近似使用使用了一个更大的batch

    4. 参数更新\(optimizer\.step\(\)\)

        1. AdamW 会根据梯度、学习率、动量、weight decay 等因素更新参数；大致流程：

        ```Plain Text
        W_Q_new = W_Q_old + 参数更新量
        W_K_new = W_K_old + 参数更新量
        ...
        ```

        2. 更新完成后，清空梯度optimizer\.zero\_grad\(\)

### 前向传播

1. 模型推理和模型训练所关注的目标不同，故两者在前向传播的过程中存在区别

2. **训练前向需要保存中间激活，推理前向通常不需要**

    1. 在模型训练中，很多中间结果需要保存，比如

        ```Plain Text
        hidden_states
        Q, K, V
        attention scores
        attention probs
        MLP 中间激活
        Norm 中间统计量
        residual 输入输出
        ```

        1. 因为反向传播需要他们计算梯度

    2. 在模型推理中，则不会保存大量中间结果，可能会保存K，V张量（KVCache）

3. **训练时 dropout 开启，推理时 dropout 关闭**

    1. 模型训练，dropout 开启，部分中间激活会被随机置零，目的是避免过拟合，增强泛化能力

4. **训练关注所有 token 的 loss，推理通常只关注最后一个 token**

    1. 模型训练中，batch内的所有有效token位置都会参与loss计算

### loss的计算

5. **logits 和真实标签 y 如何计算出 loss？**

    1. vocab\_size = 5；logits = \[1\.2, 0\.5, 2\.0, 3\.1, 1\.7\]；真实标签 label = 3\(token\_id\)

    2. logits经过softmax变成概率：\[0\.08, 0\.04, 0\.17, 0\.51, 0\.20\]

    3. 取出真实token\_id的概率：p\(苹果\) = 0\.51

    4. **\(核心\)Cross Entropy Loss ：**

        1. 真实答案的预测概率越高，loss 越小；真实答案的预测概率越低，loss 越大。

        2. 公式：loss = \-log\(p\_true\)

    5. 补充：在真实训练过程中，训练数据是以batch（批次）为单位执行训练流程，可能其中的数据logits\.shape = \[batch\_size, seq\_len, vocab\_size\]；

        1. 因此计算流程可能比较复杂，难以梳理清楚

        2. 但是不管计算流程多么复杂，你只需要记住“流程始终是这么个流程”

    6. loss 本质上是在告诉模型：你当前输出和目标之间差多少；在实际模型训练中，loss的设计也是有所不同

        1. Cross Entropy Loss：分类 / token 预测最常用

        2. MSE Loss：回归任务常用

        3. MAE Loss：对异常值更稳健的回归 loss

        4. Binary Cross Entropy：二分类 / 多标签分类

        5. \.\.\.\.

        6. 补充：实际 LLM 训练中，loss 往往不是单一形式，而是组合起来。

### 梯度的产生

6. **loss反向传播，如何计算出各个模型参数的梯度？**

    1. 补充：

        1. 反向传播：loss → probs → logits → lm\_head → Transformer blocks → 参数梯度

        2. **说白了，反向传播就是：从loss开始，反过来对模型的每个中间变脸，每个参数求偏导**

        3. logits作为整个模型最终输出结果，那它自然是模型中每个权重参数汇合的结构，那么在求解每个参数的梯度时，自然，loss对logits的梯度dL/dlogits是整个反向传播的起点

        4. **梯度：**实际上就是偏导；首先，在反向传播过程中，模型中的每个参数都应该计算出其对于loss的梯度

            1. 既然loss是由模型中大量权重参数共同参与计算的结果，那么反之，某个参数 w 如果稍微变大一点，loss 会变大还是变小？变化有多明显？

            2. 该问题的数量就是dLoss / dw，这就是loss对参数w的偏导数，即梯度

            3. 反向传播的目的其实就是计算模型中每个参数对于loss的偏导

    2. dL/dlogits：L = CrossEntropy\(probs, target\)，经过求偏导的结果

    $\frac{\partial L}{\partial z_i} = p_i - y_i$

    1. z\_i = 第 i 个 logit；p\_i = softmax 后第 i 个概率；y\_i = 第 i 个 target one\-hot 值

    1. 处理lm\_head

        1. **注意：模型推理和模型训练的lm\_head有所不同**

            1. 模型推理作为自回归生成任务，主要看最后一个 token 的特征向量，比如经过多层transformer block输出张量h\.\[batch\_size, seq\_len, hidden\_size\]，通常只取每个序列的最后一个位置\[batch\_size, \-1, hidden\_size\]，用于下一个token的生成

            2. 模型训练目的是 让模型在每个位置都学习预测下一个 token

                ```Plain Text
                输入位置:    我      喜欢     吃      苹果
                预测目标:    喜欢    吃       苹果    <下一个>
                ```

                1. logits\.shape=\[batch\_size, seq\_len, vocab\_size\]；每个位置都有一个logits向量，故每个位置都可以计算出对应的loss

                2. 模型训练以一个batch数据作为处理单位，故一个batch 经过前向传播得到的总 loss，通常是 batch 内所有有效 token 位置的 token\-level loss 汇合后的结果。

        2. 在lm\_head中，

            ```Plain Text
            logits = h @ W_lm_head
            W_lm_head.shape = [hidden_size, vocab_size]
            h.shape = [batch_size, seq_len, hidden_size]
            ```

            1. 根据反向传播以及一些高等数学方法，可以得到两个梯度 dLoss/dW\_lm\_head 和 dLoss/dh

    2. 后续其实大概就从 dLoss / dh 出发，依次反传到每层Transformer block，其内部依旧是根据各自模块在前向传播中建立的计算图，利用链式法则反向计算 Loss对其内部参数的偏导，并将这些偏导累积到对应参数的 \.grad 中，作为该参数的梯度，最终供 optimizer\.step\(\) 使用。



### 优化器\(optimizer\)

1. 前面的训练流程：forward \-\-\> logits \-\-\> loss \-\-\> backward \-\-\> 参数\.gard

2. optimizer就是根据 参数当前值parameter和参数梯度parameter\.grad，结合一些超参数（比如学习率，weight\_decay等）把参数从旧值更新为新值

3. **SGD\(最简单，最基础\)**

    1. 参数新值 = 参数旧值 \- 学习率 × 梯度

    2. 逻辑：沿着让 loss 下降的方向调整参数；loss\>0，参数增大；loss\<0，参数变小

    3. 超参：learning rate

4. **Momentum**

    1. 引入“历史梯度趋势”，参考过去几步梯度的大致方向

    2. 逻辑：

        1. 如果最近几步梯度方向差不多，说明方向稳定，可加速前进

        2. 如何梯度方向来回震荡，说明方向不稳定，需抵消一部分震荡

5. **Adam**

    1. 在Momentum 基础上增加一层：不同参数使用不同的自适应更新幅度。

    2. 两个状态:

        ```Plain Text
        m：一阶动量，类似梯度的滑动平均
        v：二阶动量，类似梯度平方的滑动平均
        ```

        1. m记录：这个参数最近梯度方向如何

        2. v 记录：这个参数最近梯度幅度有多大

        3. 更新量 ≈ learning\_rate × m / sqrt\(v\)

    3. 逻辑：

        1. 梯度长期很大的参数 \-\-\-\> 更新步幅调小

            1. 梯度长期很大，通常说明这个参数所在方向的 loss 曲面比较陡、变化剧烈，所以需要谨慎更新；

        2. 梯度长期很小的参数 \-\-\-\> 更新步幅调大

            1. 梯度长期很小，说明这个方向变化较平缓或信号较弱，所以可以适当放大更新。

    4. 解决“不同参数梯度尺度不同”

6. **AdamW（最常见的）**

    1. 它和Adam的核心区别在于“新增weight\_decay”

    2. 先用 Adam 的 m / v 动量机制处理 loss 梯度，再额外用 weight\_decay 对参数本身做衰减。

        1. 参数更新 = Adam 梯度更新 \+ decoupled weight decay 衰减

        2. W = W \- lr × AdamUpdate\(W\.grad\) \-\-\-\- \[先\]

        3. W = W × \(1 \- lr × weight\_decay\)  \-\-\-\- \[后\]

    3. 观察以上公式，你会发现 weight decay 不主要看当前梯度，而是直接作用在参数值上

    4. 作用：提升泛化能力，避免过拟合

7. **补充：**通常在模型训练中，还会有“参数分组”的行为（param\_groups）

    1. `param_groups`作为传给 optimizer 的配置，告诉优化器：

        1. 这批参数：用 weight\_decay = 0\.01

        2. 那批参数：用 weight\_decay = 0\.0

    2. optimizer只是作为接受param\_groups配置的模块，“参数分组”动机主要来自模型训练经验，它和optimizer所采取的优化算法\(AdamW等\)没有关系

    3. 比如，在transformer中通常这样分

    ```Plain Text
    需要 weight decay：
        Linear 层的 weight
        Attention 里的 W_Q、W_K、W_V、W_O
        MLP 里的 W_up、W_gate、W_down
    
    不需要 weight decay：
        bias
        LayerNorm / RMSNorm 的 weight
        有时 embedding 也单独处理
    ```

    4. 参数分组就是：针对模型中不同类型、不同作用、不同训练需求的参数，配置不同的训练策略和优化超参数，本质上属于工程训练配置概念，主要动机来自模型训练经验和训练策略

8. optimizer\.zero\_grad\(\)：清空每个参数此前累积的梯度





## nanoGPT

9. 在nanoGPT项目中，主体的训练逻辑主要在train\.py和model\.py中，下面简单介绍模型训练的大致流程

```Plain Text
读取配置参数
   ↓
判断是否使用 DDP 分布式训练
   ↓
设置随机种子、device、dtype、混合精度上下文
   ↓
构造 get_batch() 数据读取函数
   ↓
读取 meta.pkl 获取 vocab_size
   ↓
初始化模型 GPT
   ↓
初始化优化器 AdamW
   ↓
可选 torch.compile()
   ↓
可选 DDP 包装
   ↓
进入训练循环
   ↓
定期评估 train/val loss
   ↓
前向传播 → 计算 loss
   ↓
反向传播 → 梯度累积 → 梯度裁剪
   ↓
optimizer.step() 更新参数
   ↓
定期保存 checkpoint
```

可将其转换更直观的数据流程图

```Plain Text
train.bin / val.bin
        ↓
   get_batch()
        ↓
 x: [batch_size, block_size]
 y: [batch_size, block_size]
        ↓
      GPT(x, y)
        ↓
 logits: [batch_size, block_size, vocab_size]
 loss: next-token prediction loss
        ↓
 backward()
        ↓
 optimizer.step()
        ↓
 模型参数更新
```

1. x: \[batch\_size, block\_size\]是需要经过模型前向传播的训练数据，y: \[batch\_size, block\_size\]则是训练数据x的标签，用于后续计算loss

2. 训练数据x经过模型前向传播会得到logits: \[batch\_size, block\_size, vocab\_size\]

    1. batch\_size：一次喂给模型多少段文本样本；block\_size：每段文本样本有多少个 token；vocab\_size：词表中一共有多少种可能 token

    2. logits\[b, t, :\]表示 第 b 条样本中，第 t 个位置经过 GPT 前向传播后，对“下一个 token 是词表中每一个 token”的打分。

10. 模型初始化分别有3种方式：

    1. scratch：

    2. resume：

    3. gpt2/gpt2\-medium：

11. 在模型训练中，存在两个参数gradient\_accumulation\_steps和batch\_size

    1. gradient\_accumulation\_steps = 40 表示梯度累积40个iteration进行更新参数

    2. batch\_size = 12 表示每批训练的样本数为12，当gradient\_accumulation\_steps \> 1时，这个参数通常又被称为micro\_batch\_size

12. dropout：随机丢弃一些中间激活值，目的让模型不要过度依赖某些特征，从而缓解过拟合

    1. “中间激活值”主要指前向传播过程中的中间张量，重点围绕在\[n,hidden\_size\]中的hidden\_size上

        ```Plain Text
        原始 hidden state:
        [0.8, 1.2, -0.5, 0.3, 2.1]
        
        dropout = 0.2 后，可能变成:
        [0.8, 0.0, -0.5, 0.3, 0.0]
        ```

        1. 被置0的位置，本轮训练不参与后续计算

    2. dropout理论上可以放在前向传播中的很多位置，可以是自注意力模块的输出，可以是MLP模块的输出，主要还是作用张量的hidden\_size维度

    3. 当dropout = 0\.1时，训练时，每个元素有 10% 概率被置为 0；剩下 90% 的元素会被保留并按比例放大。

    4. 具体执行方法：

        1. 系统按照hidden\_size随机生成一个mask，比如当hidden\_size=4，x=\[1\.0, 2\.0, 3\.0, 4\.0\]时，mask=\[1, 0, 1, 0\]

        2. 执行x \* mask，得到dropout后的结果\[1\.0, 0\.0, 3\.0, 0\.0\]

        3. 在某些场景下，可能还会有inverted dropout，将保留下来的值除以1\-p，最终输出\[2\.0, 0\.0, 6\.0, 0\.0\]

            1. 其实就是将保留的元素按比例放大

13. learing\_rate：学习率，控制参数更新的基础步长，属于AdamW optimizer优化器参数

    1. 在训练循环中，主要作用于optimizer\.step\(\)

14. 在模型训练中，一次iteration对应一次参数更新，而非一个batch数据的训练流程执行

    1. 当gradient\_accumulation\_steps=48，batch\_size = 12时，此时一个iteration可能包含多个mcrao\-batch数据，一个iteration对应一次 optimizer\.step\(\)

15. weight\_decay： AdamW 的权重衰减系数

    1. 作用：让参数不要无限变大，是一种正则化手段；

    2. 和 dropout 一样，都是缓解过拟合/提升泛化的手段，但方式不同

        1. dropout：作用在前向传播的中间激活值上，主要作用在张量数据的hidden\_size维度

        2. weight\_decay：作用在模型参数更新上



