@echo off
echo Stopping Telegram bot...
taskkill /F /FI "WINDOWTITLE eq *bot.main*" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo 실행 중인 봇을 찾지 못했습니다.
) else (
    echo 봇이 종료되었습니다.
)
pause
