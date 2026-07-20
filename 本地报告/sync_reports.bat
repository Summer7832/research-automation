@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo =====================================
echo 正在从云端同步最新研报报告...
echo 当前目录: %cd%
echo =====================================

:: 1. 切换到 Git 仓库根目录（A-share-factor-analysis），再拉取最新内容
cd /d "G:\杨紫桐\大学\项目\传GitHub\A-share-factor-analysis"
git fetch origin main
git reset --hard origin/main

:: 2. 获取今天的日期（格式：YYYY-MM-DD）
for /f "tokens=1-3 delims=/-" %%a in ('date /t') do (
    set year=%%a
    set month=%%b
    set day=%%c
)
if "!month!"=="" (
    for /f "tokens=1-3 delims=/- " %%a in ('echo %date%') do (
        set year=%%a
        set month=%%b
        set day=%%c
    )
)
:: 补零处理（如果月份或日期只有1位，前面补0）
if !month! lss 10 set month=0!month!
if !day! lss 10 set day=0!day!
set TODAY=!year!-!month!-!day!

:: 3. 检查今天的报告文件夹是否存在
set SOURCE_DIR=reports\daily\!TODAY!
if not exist "!SOURCE_DIR!" (
    echo ❌ 今天 (!TODAY!) 的报告尚未生成，请稍后再试。
    pause
    exit /b
)

:: 4. 创建“每日汇总”文件夹（存放重命名后的文件）
if not exist "本地报告\每日汇总" mkdir "本地报告\每日汇总"

:: 5. 复制并重命名 PDF 和 MD 文件
set DEST_PDF=本地报告\每日汇总\!TODAY!_研报汇总.pdf
set DEST_MD=本地报告\每日汇总\!TODAY!_研报汇总.md

if exist "!SOURCE_DIR!\daily_report.pdf" (
    copy /Y "!SOURCE_DIR!\daily_report.pdf" "!DEST_PDF!"
    echo ✅ PDF已保存至：!DEST_PDF!
)
if exist "!SOURCE_DIR!\daily_report.md" (
    copy /Y "!SOURCE_DIR!\daily_report.md" "!DEST_MD!"
    echo ✅ MD已保存至：!DEST_MD!
)

echo =====================================
echo ✅ 同步完成！文件已按日期命名归档。
echo 存放位置：本地报告\每日汇总\
pause