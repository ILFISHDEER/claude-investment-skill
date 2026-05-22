@echo off
chcp 65001 >nul
cd /d "C:\Users\OpenClawUser\Projects\investment-skill"

echo === Investment Skill 一键更新 ===
echo.

echo [1/4] 检查数据新鲜度...
python check_freshness.py
if %errorlevel% neq 0 (
    echo ⚠️  发现过期数据，开始更新...
    python update_data.py
) else (
    echo ✅ 数据新鲜
)

echo.
echo [2/4] 检查链接完整性...
python check_links.py
if %errorlevel% neq 0 (
    echo ⚠️  发现链接问题，尝试修复...
    python check_links.py --fix
)

echo.
echo [3/4] 修复报告返回链接...
python generate_report.py --fix-all

echo.
echo [4/4] 生成健康检查报告...
python integrity_check.py

echo.
echo ================================
echo ✅ 一键更新完成！
echo ================================
echo.
echo 下一步：对AI说"生成报告"
pause
