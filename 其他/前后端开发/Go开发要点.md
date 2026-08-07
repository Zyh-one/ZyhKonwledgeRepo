* Go 优雅关闭；信号或通道；
  ```
  操作系统发出 SIGINT/SIGTERM
            ↓
  shutdownSignal.Done() 被关闭
            ↓
  后台 goroutine 被唤醒
            ↓
  给服务最多 5 秒处理已有请求
            ↓
  server.Shutdown(...)
            ↓
  ListenAndServe() 返回 http.ErrServerClosed
            ↓
  main 函数正常退出
  ```
