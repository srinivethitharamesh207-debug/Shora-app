@echo off
REM Build Shora Backend with Maven
echo Building Shora Backend...
cd /d "%~dp0"

REM Try using Maven if installed
if exist C:\maven\apache-maven-3.9.6\bin\mvn.cmd (
    echo Using Maven from C:\maven
    C:\maven\apache-maven-3.9.6\bin\mvn.cmd clean install
) else (
    REM Try system Maven
    echo Looking for Maven in PATH...
    where mvn >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        mvn clean install
    ) else (
        echo Maven not found. Please install Maven from https://maven.apache.org/download.cgi
        echo After installation, add maven\bin to your PATH
        pause
    )
)
pause
