@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo   YTFB Studio - Windows build
echo ============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [X] Python পাওয়া যায়নি। python PATH-এ আছে কিনা দেখুন।
  pause
  exit /b 1
)

echo [1/3] প্রয়োজনীয় প্যাকেজ আছে কিনা দেখা হচ্ছে...
python -c "import PyInstaller, PySide6, moviepy, edge_tts, playwright" 2>nul
if errorlevel 1 (
  echo     কিছু প্যাকেজ নেই - ইনস্টল করা হচ্ছে...
  python -m pip install -r requirements.txt || goto :failed
)

if /i "%1"=="--with-browser" (
  echo [2/3] ব্রাউজার বান্ডল করা হবে ^(exe বড় হবে^)...
  set YTFB_BUNDLE_BROWSERS=1
) else (
  echo [2/3] ছোট বিল্ড ^(ব্রাউজার প্রথমবার অ্যাপ থেকেই ইনস্টল করা যাবে^)...
  set YTFB_BUNDLE_BROWSERS=0
)

echo [3/3] বিল্ড চলছে... ^(একটু সময় লাগবে^)
python -m PyInstaller --noconfirm --clean YTFBAutomation.spec || goto :failed

echo.
echo ============================================
echo   সফল!  ফোল্ডার:  dist\YTFBStudio\
echo   চালান:         dist\YTFBStudio\YTFBStudio.exe
echo ============================================
echo.
echo প্রথমবার চালু হয়ে Tools পেজ থেকে "ব্রাউজার ইনস্টল" ও "বাংলা ফন্ট নামান" চাপুন।
echo.
pause
exit /b 0

:failed
echo.
echo [X] বিল্ড ব্যর্থ হয়েছে। উপরের এরর দেখুন।
pause
exit /b 1
