#!/bin/bash
# Opens the generated Demo if it exists, otherwise the site straight from Source.
cd "$(dirname "$0")" || exit 1
if [ -f "Demo/START-DEMO.command" ]; then
  exec bash "Demo/START-DEMO.command"
else
  exec bash "Source/START-DEMO.command"
fi
