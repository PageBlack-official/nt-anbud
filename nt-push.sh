#!/bin/sh
# Kjøres av launchd (com.pageblack.nt-status) hvert 5. minutt til fre 13.11.2026 kl. 10:00.
# Lager status.json og dytter til GitHub når noe er endret. Logg: /tmp/nt-status.log
PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
cd "$(dirname "$0")" || exit 1
if [ "$(date +%Y%m%d%H%M)" -gt 202611131000 ]; then
  launchctl bootout "gui/$(id -u)/com.pageblack.nt-status" 2>/dev/null
  exit 0
fi
python3 nt-status.py || exit 1
git add -A
if ! git diff --cached --quiet; then
  git commit -qm "status $(date '+%d.%m %H:%M')" && git push -q origin main && echo "$(date '+%d.%m %H:%M') dyttet"
fi
