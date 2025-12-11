@echo off
set URL=https://www.twitch.tv/konstantinbestgames
set count=1
set browser=firefox
python E:\00_WORK\EnergoChain\multi-window-selenium\main.py -u %URL% -c %count% -b %browser%
pause

