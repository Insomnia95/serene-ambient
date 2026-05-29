#!/bin/bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/shims:$PYENV_ROOT/bin:/usr/local/bin:/usr/bin:/bin"
eval "$(pyenv init -)" 2>/dev/null || true
cd /Users/annashvets/Calm-veritas
exec python3 admin.py
