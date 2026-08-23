**atrust Ubuntu使用方法**

使用docker-atruts镜像，docker  pull hagb/docker-atrust，它可以很好解决atrust对系统DNS的污染

启动docker-atrust容器

```
docker run -d \
  --name atrust \
  --device /dev/net/tun \
  --cap-add NET_ADMIN \
  --restart unless-stopped \
  -e PASSWORD='AtrustVnc123' \
  -e URLWIN=1 \
  -v "$HOME/.atrust-data:/root" \
  -p 127.0.0.1:5901:5901 \
  -p 127.0.0.1:1080:1080 \
  -p 127.0.0.1:8888:8888 \
  -p 127.0.0.1:54631:54631 \
  --sysctl net.ipv4.conf.default.route_localnet=1 \
  hagb/docker-atrust
```

由于atrust是带有可视化界面的，故下载vncveiwer

```
sudo apt install -y tigervnc-viewer
```

大致原理为vncviewer，通过docker挂载的指定端口，访问docker-atrust内部服务，执行登录vpn操作

启动docker-atrust，需要使用 vncviewer 127.0.0.1::5901 命令和aTrsut建立连接



vncviewer默认密码：**AtrustVnc123**


50机器使用说明
网络连接命令：

```
./auth-thu.linux.x86_64 --username tanwenting --password 111111 auth --host gw.ict.ac.cn --ac-id 1
```

50机器访问外网

```
ssh -i ~/.ssh/id_ed25519 -p 2222 -N -L 127.0.0.1:26003:127.0.0.1:26001 fs_zhangyihao@10.10.150.19
```

测试网络连接

```
curl -4 -I -L --connect-timeout 10 --max-time 20 https://openai.com

curl -4 -I -L --connect-timeout 10 --max-time 20 https://www.baidu.com
```
claude-code权限放开

claude --permission-mode bypassPermissions

50机器的vscode网络代理配置位于/home/zhangyuhao/.vscode-server/data/Machine/settings.json:1