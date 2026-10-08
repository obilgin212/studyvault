# Run the class sync once a day in the background (Windows Task Scheduler). The Windows twin of schedule.sh.
# The task starts at logon and then every hour; collect.py --daily exits immediately if today's run already
# succeeded, so the real work happens once, shortly after the PC is first used each day (retrying hourly on failure).
#   powershell -ExecutionPolicy Bypass -File tools\sync\schedule_windows.ps1 install | uninstall | status | run-now | log
param([string]$Command = "status")

$Name = "StudyVault Class Sync"
$Vault = Join-Path $env:USERPROFILE "StudyVault"
$Dir = Join-Path $Vault "tools\sync"
$Py = Join-Path $env:USERPROFILE "miniconda3\envs\study\pythonw.exe"      # pythonw: no console window pops up
$Log = Join-Path $Vault "Inbox\sync\collector.log"

switch ($Command) {
  "install" {
    if (-not (Test-Path $Py)) { Write-Error "Python not found at $Py (create the 'study' conda env first)"; exit 1 }
    [Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")      # emoji-safe file I/O for every run
    $action = New-ScheduledTaskAction -Execute $Py -Argument "collect.py --daily" -WorkingDirectory $Dir
    $atLogon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $hourly = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) `
                                       -RepetitionDuration (New-TimeSpan -Days 3650)
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
                                             -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $Name -Action $action -Trigger $atLogon, $hourly -Settings $settings `
                           -Description "Reads Google Classroom once a day for StudyVault (read-only)." -Force | Out-Null
    "Scheduled: at logon + hourly checks, real run once a day ('$Name' in Task Scheduler)"
  }
  "uninstall" {
    Unregister-ScheduledTask -TaskName $Name -Confirm:$false -ErrorAction SilentlyContinue
    "Removed schedule"
  }
  "status" {
    $t = Get-ScheduledTask -TaskName $Name -ErrorAction SilentlyContinue
    if (-not $t) { "Not scheduled"; break }
    $i = Get-ScheduledTaskInfo -TaskName $Name
    "State: $($t.State) | last run: $($i.LastRunTime) | last result: $($i.LastTaskResult) | next: $($i.NextRunTime)"
    if (Test-Path $Log) {
      Get-Content $Log -Tail 200 | Select-String -Pattern "daily run starting|changes|no changes|failed|expired|announcements:|materials:|classindex:" |
        Select-Object -Last 8 | ForEach-Object { $_.Line }
    }
  }
  "run-now" { Start-ScheduledTask -TaskName $Name; "Started (check: schedule_windows.ps1 status)" }
  "log" { if (Test-Path $Log) { Get-Content $Log -Tail 40 } else { "No log yet" } }
  default { "Usage: schedule_windows.ps1 install | uninstall | status | run-now | log" }
}
