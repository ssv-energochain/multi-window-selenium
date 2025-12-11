@echo off
set URL=https://www.google.com
set count=1
set browser=yandex
python E:\00_WORK\EnergoChain\multi-window-selenium\main.py -u %URL% -c %count% -b %browser%
pause

