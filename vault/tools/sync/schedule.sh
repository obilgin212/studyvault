#!/bin/zsh
# Run the class sync once a day in the background (macOS launchd).
# launchd starts it at login and then every hour; collect.py --daily exits immediately if today's run already
# succeeded, so the real work happens once, shortly after the Mac is first used each day (retrying hourly on failure).
#   tools/sync/schedule.sh install | uninstall | status | run-now | log
LABEL="com.studyvault.classsync"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$HOME/miniconda3/envs/study/bin/python"
DIR="$HOME/StudyVault/tools/sync"
LOG="$HOME/StudyVault/Inbox/sync/launchd.log"
case "$1" in
  install)
    mkdir -p "$HOME/Library/LaunchAgents" "$(dirname "$LOG")"
    cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$PY</string><string>$DIR/collect.py</string><string>--daily</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>StartInterval</key><integer>3600</integer>
  <key>ProcessType</key><string>Background</string>
  <key>Nice</key><integer>10</integer>
  <key>LowPriorityIO</key><true/>
  <key>EnvironmentVariables</key><dict>
    <key>PATH</key><string>$HOME/.local/bin:$HOME/.ghcup/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
  </dict>
  <key>StandardOutPath</key><string>$LOG</string><key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
    launchctl bootstrap "gui/$(id -u)" "$PLIST" && echo "Scheduled: at login + hourly checks, real run once a day ($PLIST)";;
  uninstall)
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null; rm -f "$PLIST"; echo "Removed schedule";;
  status)
    launchctl print "gui/$(id -u)/$LABEL" 2>/dev/null | grep -E "state =|last exit code|runs =" || echo "Not scheduled"
    grep -E "daily run starting|changes →|no changes|failed|expired|announcements:|materials:|classindex:" "$HOME/StudyVault/Inbox/sync/collector.log" 2>/dev/null | tail -8;;
  run-now)
    launchctl kickstart -k "gui/$(id -u)/$LABEL" && echo "Started (check: $0 status)";;
  log)
    tail -40 "$LOG";;
  *) echo "usage: $0 install | uninstall | status | run-now | log"; exit 1;;
esac
