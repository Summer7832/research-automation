@echo off
set TOKEN=你的token（替换成实际值）
curl -X POST -H "Authorization: token %TOKEN%" -H "Accept: application/vnd.github.v3+json" https://api.github.com/repos/Summer7832/A-share-factor-analysis/actions/workflows/daily_report.yml/dispatches -d "{\"ref\":\"main\"}"
echo 触发成功！请前往 Actions 页面查看进度。
pause