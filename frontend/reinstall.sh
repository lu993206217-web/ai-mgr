#!/bin/bash
cd /Users/lu/WorkBuddy/2026-06-13-10-50-39/ai-control-tower/frontend
rm -rf node_modules/.vite node_modules/.cache
npm install --force 2>&1 | tail -15
