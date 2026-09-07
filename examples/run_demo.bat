@echo off
REM Run the agency content pipeline with the sample brief.
REM Make sure .env is configured first: python -m src.config

cd /d "%~dp0.."

REM Load WP_SITE_URL from .env if not set
if "%WP_SITE_URL%"=="" (
    for /f "tokens=1,* delims==" %%a in ('findstr /b "WP_SITE_URL=" .env') do set WP_SITE_URL=%%b
)

if "%WP_SITE_URL%"=="" (
    echo Error: WP_SITE_URL not found in .env or environment.
    echo Run: python -m src.config
    exit /b 1
)

echo === Agency Content Pipeline ===
echo Brief:  examples/sample_brief.md
echo Target: %WP_SITE_URL%
echo.

python -m src.graph --brief examples/sample_brief.md --wp-url "%WP_SITE_URL%"
