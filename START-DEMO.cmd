@echo off
rem Opens the generated Demo if it exists, otherwise the site straight from Source.
if exist "%~dp0Demo\START-DEMO.cmd" (
  call "%~dp0Demo\START-DEMO.cmd"
) else (
  call "%~dp0Source\START-DEMO.cmd"
)
