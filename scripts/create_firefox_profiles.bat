@echo off
setlocal enabledelayedexpansion

REM === Set Firefox path ===
set "FIREFOX_EXE=C:\Program Files\Mozilla Firefox\firefox.exe"

REM === Set base profile directory ===
set "BASE_DIR=%USERPROFILE%\FirefoxProfiles"

REM === Desktop User Agent ===
set "UA_DESKTOP=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Gecko/20100101 Firefox/118.0"

REM === Mobile User Agent ===
set "UA_MOBILE=Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/118.0 Mobile/15E148 Safari/605.1.15"

REM === Create Desktop Profiles ===
for /L %%i in (1,1,6) do (
    set "PROFILE_NAME=Profile%%i"
    set "PROFILE_PATH=%BASE_DIR%\!PROFILE_NAME!"
    "%FIREFOX_EXE%" -CreateProfile "!PROFILE_NAME! !PROFILE_PATH!"
    echo user_pref("general.useragent.override", "!UA_DESKTOP!") >> "!PROFILE_PATH!\prefs.js"
)

REM === Create Mobile Profiles ===
for /L %%i in (1,1,6) do (
    set "PROFILE_NAME=Profile%%i_mobile"
    set "PROFILE_PATH=%BASE_DIR%\!PROFILE_NAME!"
    "%FIREFOX_EXE%" -CreateProfile "!PROFILE_NAME! !PROFILE_PATH!"
    echo user_pref("general.useragent.override", "!UA_MOBILE!") >> "!PROFILE_PATH!\prefs.js"
)

echo All profiles created with custom user agents.
pause