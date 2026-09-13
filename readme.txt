先测试连接服务器admin@iZuf6a27proy7jkii03mbwZ:~$ curl -s ifconfig.me
8.133.252.224

（域名暂缓：未备案公网不稳定，先用 IP）

--- 本地 ---
npm install
npm run docs:dev
npm run docs:build

--- Cloud Agent SSH（jk9988610.pem）---
Cursor → Cloud Agents → Environment → Secrets:
  MIRAWORLD_SSH_PRIVATE_KEY = jk9988610.pem 完整内容
新开的 Agent 会话才会注入；deploy.py 只使用该密钥。

--- 部署到 IP 子路径 /miraworld/（两步，不要合并）---
npm run docs:build
npm run deploy

deploy 只在 Cloud Agent VM 里用 Python 上传 dist；不会在云服务器上跑 apt/python 安装。
首次 nginx 引导见 bootstrap-on-server.sh（服务器上执行一次即可）。

--- 旧：服务器端 tar 更新（可选）---
阿里云网页终端:
  curl -fsSL https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/bootstrap-on-server.sh | sed 's/\r$//' | bash

仅更新静态文件:
  curl -fsSL -o /tmp/miraworld-dist.tar.gz https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/miraworld-dist.tar.gz
  sudo mkdir -p /var/www/html/miraworld
  sudo find /var/www/html/miraworld -mindepth 1 -delete
  sudo tar -xzf /tmp/miraworld-dist.tar.gz -C /var/www/html/miraworld
  sudo chown -R www-data:www-data /var/www/html/miraworld

访问:
  bykc:      http://8.133.252.224/
  MiraWorld: http://8.133.252.224/miraworld/

--- 运维文档（仓库内）---
  docs/ops/server-capacity-and-orders.md  压测、内存、缓存、下单容量估算
  站点侧栏「运维」栏目（部署后: /miraworld/ops/）
