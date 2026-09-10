# Deploy MiraWorld under /miraworld/ (keeps bykc at /)
# Usage: .\deploy\deploy.ps1

$ErrorActionPreference = "Stop"
$HostName = "8.133.252.224"
$User = "admin"
$LocalDist = Join-Path $PSScriptRoot "..\docs\.vitepress\dist"
$RemoteTmp = "/tmp/miraworld-dist"
$RemoteRoot = "/var/www/html/miraworld"

if (-not (Test-Path $LocalDist)) {
    Write-Error "Dist not found. Run: npm run docs:build"
}

Write-Host "Uploading dist to ${User}@${HostName} ..."
ssh "${User}@${HostName}" "rm -rf $RemoteTmp && mkdir -p $RemoteTmp"
scp -r "$LocalDist\*" "${User}@${HostName}:${RemoteTmp}/"
scp (Join-Path $PSScriptRoot "nginx-miraworld.conf") "${User}@${HostName}:/tmp/nginx-miraworld.conf"
scp (Join-Path $PSScriptRoot "setup-nginx.sh") "${User}@${HostName}:/tmp/setup-nginx.sh"

ssh "${User}@${HostName}" @"
set -e
chmod +x /tmp/setup-nginx.sh
sudo bash /tmp/setup-nginx.sh /tmp/nginx-miraworld.conf
sudo mkdir -p $RemoteRoot
sudo find $RemoteRoot -mindepth 1 -delete
sudo cp -a $RemoteTmp/. $RemoteRoot/
sudo chown -R www-data:www-data $RemoteRoot
sudo nginx -t && sudo systemctl reload nginx
echo DEPLOY_OK
curl -sI http://127.0.0.1/miraworld/ | head -n 5
"@

Write-Host "Done. Open http://${HostName}/miraworld/"
