@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   资质代办全网推广助手 - 打包构建脚本
echo ============================================
echo.

:: 检查是否安装了 NSIS (用于生成安装程序)
where makensis >nul 2>&1
if %errorlevel% equ 0 (
    set HAS_NSIS=1
    echo [检测] NSIS 已安装，将生成 .exe 安装程序
) else (
    set HAS_NSIS=0
    echo [提示] NSIS 未安装，仅生成免安装绿色版
    echo        下载地址: https://nsis.sourceforge.io/Download
)
echo.

:: 步骤1: 清理旧文件
echo [1/4] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 步骤2: PyInstaller 打包
echo [2/4] PyInstaller 打包中 (可能需要几分钟)...
pyinstaller --clean build.spec

if not exist dist\QualificationPromoteBot\QualificationPromoteBot.exe (
    echo [失败] PyInstaller 打包出错，请检查上方错误信息
    pause
    exit /b 1
)
echo [2/4] PyInstaller 打包完成

:: 步骤3: 复制必要文件到打包目录
echo [3/4] 复制配置文件和数据目录...
if exist .env.example copy /Y .env.example dist\QualificationPromoteBot\ >nul
if exist assets copy /Y assets\*.* dist\QualificationPromoteBot\assets\ >nul 2>&1

:: 复制Playwright Chromium浏览器 (如果系统已安装)
if not exist dist\QualificationPromoteBot\browsers mkdir dist\QualificationPromoteBot\browsers
set BROWSERS_SRC=%LOCALAPPDATA%\ms-playwright
if exist "%BROWSERS_SRC%\chromium-1217" (
    echo [3/4] 复制Chromium浏览器 (约400MB，需要几分钟)...
    xcopy /E /I /Q "%BROWSERS_SRC%\chromium-1217" "dist\QualificationPromoteBot\browsers\chromium-1217" >nul
    xcopy /E /I /Q "%BROWSERS_SRC%\ffmpeg-1011" "dist\QualificationPromoteBot\browsers\ffmpeg-1011" >nul
    xcopy /E /I /Q "%BROWSERS_SRC%\winldd-1007" "dist\QualificationPromoteBot\browsers\winldd-1007" >nul
    echo [3/4] 浏览器文件复制完成
) else (
    echo [3/4] 警告: 未找到系统Chromium浏览器，需在目标机器上运行 playwright install chromium
)
echo [3/4] 文件复制完成

:: 步骤4: NSIS 生成安装程序 (可选)
if %HAS_NSIS% equ 1 (
    echo [4/4] 生成 NSIS 安装程序...
    makensis installer.nsi >nul 2>&1
    if %errorlevel% equ 0 (
        echo [4/4] 安装程序生成成功!
        echo.
        echo ============================================
        echo   构建完成! 输出文件:
        echo.
        echo   免安装绿色版: dist\QualificationPromoteBot\
        echo   安装程序:     dist\资质代办推广助手_Setup.exe
        echo ============================================
    ) else (
        echo [警告] NSIS 构建失败，仅免安装绿色版可用
    )
) else (
    echo [4/4] 跳过安装程序生成 (NSIS 未安装)
    echo.
    echo ============================================
    echo   构建完成! 输出文件:
    echo.
    echo   免安装绿色版: dist\QualificationPromoteBot\
    echo ============================================
    echo.
    echo   提示: 安装 NSIS 后可生成 .exe 安装包
)

echo.
echo 按任意键退出...
pause >nul
