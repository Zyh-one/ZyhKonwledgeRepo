# aTrust → 19 堡垒机 → 50 机器

该工具使用 OpenSSH 和用户级 systemd 维护独立隧道，不依赖 WindTerm。

链路：

```text
localhost:6009
  → OpenSSH
  → 127.0.0.1:1080 SOCKS5
  → 10.10.150.19:2222
  → 10.10.150.50:2023
```

## 首次安装并启动

```bash
/home/cambricon/sshTool/install-service.sh
```

## 登录 50 机器

```bash
/home/cambricon/sshTool/connect-50.sh
```

## 运行或恢复 Claude tmux 会话

```bash
/home/cambricon/sshTool/claude-50.sh
```

`claude-50.sh` 会连接或创建名为 `claude` 的 tmux 会话。SSH/VPN
短暂中断不会终止该会话中的任务。

## 管理隧道

```bash
/home/cambricon/sshTool/start-tunnel.sh
/home/cambricon/sshTool/stop-tunnel.sh
/home/cambricon/sshTool/status.sh
/home/cambricon/sshTool/logs.sh
```

systemd 会在隧道异常退出后等待 5 秒自动重建。SSH 每 10 秒发送保活，
连续 3 次无响应即触发重连。

本地端口使用 `6009`，因为生成工具时 WindTerm 正占用 `6008`。
