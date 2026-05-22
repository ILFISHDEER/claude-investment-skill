@echo off
chcp 65001 >nul
cd /d "C:\Users\OpenClawUser\Projects\investment-skill"

echo === 投资框架全自动更新 ===

echo [1/3] 检查数据新鲜度...
python check_freshness.py > check_result.txt 2>&1
findstr "🚨" check_result.txt >nul
if %errorlevel% == 0 (
    echo ⚠️  发现过期数据，开始更新...
    python update_data.py
    echo ✅ 数据更新完成
) else (
    echo ✅ 数据新鲜，跳过更新
)

echo.
echo [2/3] 生成最新报告...
python -c "
import subprocess
import sys

# 调用Claude Code生成报告（如果配置了claude CLI）
print('报告生成指令已准备')
print('请对AI说：按当前配置生成最新的L2简报')
" 2>nul

echo.
echo [3/3] 完成！
echo ================================
echo 下一步：在Claude窗口输入：
echo    生成报告
echo ================================
del check_result.txt 2>nul
pause
