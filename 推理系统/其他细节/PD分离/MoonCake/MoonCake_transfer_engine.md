**MoonCake Transfer Engine**

对应“KVCache传输”的P2P

vLLM实例在使用transfer engine时，需要以下启动参数来指定：

```
--kv-transfer-config {"kv_connector":"MooncakeConnector","kv_role":"kv_producer","kv_connector_extra_config":{"num_workers":64}}"
```

vLLM会通过pip install的方式安装transfer engine，故在使用transfer engine过程中，不需要额外部署中间层服务

但是MoonCake transfer engine的二进制程序是相对独立，故可以对其进行单独测试



MoonCake Transfer Engine官方公开数据：

* 传输数据量：40 GB
* 并发度：64
* 最小传输粒度：128 KB
* `4 × 200 Gbps RoCE`：约 **87 GB/s**
* `8 × 400 Gbps RoCE`：约 **190 GB/s**

公开测试数据高度依赖环境，故需要在实际环境中实测


MoonCake Transfer Engine的源码位于开源项目[github.com/kvcache-ai/Mooncake/tree/main/mooncake-transfer-engine](https://github.com/kvcache-ai/Mooncake/tree/main/mooncake-transfer-engine)

部署MoonCake Transfer Engine的方式：拉取开源项目MoonCake，C++源码编译，但是针对MLU好像有些许区别
