@echo off
echo Windows 시작 프로그램에 봇을 등록합니다...
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SCRIPT=%~dp0start_bot.bat"
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%STARTUP%\AMIC_TelegramBot.lnk'); $s.TargetPath = '%SCRIPT%'; $s.WorkingDirectory = '%~dp0'; $s.Save()"
echo.
echo 바로가기가 생성되었습니다: %STARTUP%\AMIC_TelegramBot.lnk
echo PC 재시작 시 봇이 자동 실행됩니다.
pause
