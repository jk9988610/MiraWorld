先测试连接服务器admin@iZuf6a27proy7jkii03mbwZ:~$ curl -s ifconfig.me
8.133.252.224

--- 本地 ---
npm install
npm run docs:dev
npm run docs:build

--- 部署（保留 bykc 首页，MiraWorld 在子路径）---
方式 A：阿里云网页终端粘贴
  curl -fsSL https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/bootstrap-on-server.sh | sed 's/\r$//' | bash

若 nginx -t 报 duplicate default server（.bak 留在 sites-enabled）：
  sudo mkdir -p /etc/nginx/backup
  sudo mv /etc/nginx/sites-enabled/*.bak* /etc/nginx/backup/ 2>/dev/null || true
  sudo tee /etc/nginx/snippets/miraworld.conf >/dev/null <<'EOF'
location = /miraworld { return 301 /miraworld/; }
location ^~ /miraworld/ {
    root /var/www/html;
    index index.html;
    try_files $uri $uri.html /miraworld/index.html;
}
EOF
  # 确认 bykc 配置里有: include /etc/nginx/snippets/miraworld.conf;
  sudo nginx -t && sudo systemctl reload nginx

若条目 404/403（无 .html 的 clean URL）：已改为带 .html 链接，服务器更新静态文件：
  curl -fsSL -o /tmp/miraworld-dist.tar.gz https://github.com/jk9988610/MiraWorld/releases/download/miraworld-web/miraworld-dist.tar.gz
  sudo find /var/www/html/miraworld -mindepth 1 -delete
  sudo tar -xzf /tmp/miraworld-dist.tar.gz -C /var/www/html/miraworld
  sudo chown -R www-data:www-data /var/www/html/miraworld
  # 然后打开: http://8.133.252.224/miraworld/world/overview.html
