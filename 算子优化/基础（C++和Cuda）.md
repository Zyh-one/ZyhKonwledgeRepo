**大致思路**：

1. 什么是算子？算子在实际生产场景中是如何发挥作用？算子和核函数的对比；可以适当以pytorch框架举例强调“pytorch实际就是对算子的封装”
2. 为什么需要自定义算子？这一部分可以利用flash-attention，triton等框架，简单强调这些框架大致做了啥？
3. 基础环境配置（C++和Cuda），不用强调python的环境配置；
4. C++的编译流程，Cmake构建流程，kernel launch等cpu端侧逻辑
5. Cuda执行模型
   1. grid，block，thread，wrap，SM等基础概念
   2. sharedMem，cuda stream
6. C++和Cuda的整体执行链路
7. python和 C++(cuda)的配合使用
8. 总结