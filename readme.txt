先测试连接服务器admin@iZuf6a27proy7jkii03mbwZ:~$ curl -s ifconfig.me
8.133.252.224

（域名暂缓：未备案公网不稳定，先用 IP）

--- 本地 ---
npm install
npm run docs:dev
npm run docs:build

--- 部署到 IP 子路径 /miraworld/ ---
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
