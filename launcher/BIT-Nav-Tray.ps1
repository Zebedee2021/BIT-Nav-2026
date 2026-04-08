# BIT-Nav Tray Manager v3 - Optimized
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Config
$script:BasePort = 8501
$script:ServicePort = 8501
$script:ServiceUrl = "http://localhost:8501"
$script:ProjectDir = Split-Path -Parent $PSScriptRoot
$script:IsRunning = $false

# ============================================
# Utility Functions
# ============================================

# Find available port
function Find-AvailablePort {
    param([int]$StartPort = 8501)
    for ($port = $StartPort; $port -lt $StartPort + 10; $port++) {
        $portStr = ":" + $port
        $inUse = netstat -ano | findstr $portStr | findstr "LISTENING"
        if (-not $inUse) {
            return $port
        }
    }
    return $null
}

# Find running service port
function Find-RunningPort {
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portCheck = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portCheck) {
            return $p
        }
    }
    return 0
}

# Open URL in browser (reliable method for GUI events)
function Open-UrlInBrowser {
    param([string]$Url)
    
    # Try to find a working browser
    $browserPath = $null
    
    # 1. Try default browser from registry
    try {
        $browserCmd = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\http\shell\open\command" -Name "(Default)" -ErrorAction Stop)."(Default)"
        
        if ($browserCmd -match '"([^"]+)"') {
            $regPath = $matches[1]
        } else {
            $regPath = ($browserCmd -split ' ')[0]
        }
        
        # Verify it exists
        if (Test-Path $regPath) {
            $browserPath = $regPath
        }
    } catch {}
    
    # 2. If default browser not found or is 360 (uninstalled), try common browsers
    if (-not $browserPath -or $browserPath -match "360") {
        $commonBrowsers = @(
            "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
            "${env:LOCALAPPDATA}\Google\Chrome\Application\chrome.exe",
            "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe",
            "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
        )
        
        foreach ($path in $commonBrowsers) {
            if (Test-Path $path) {
                $browserPath = $path
                break
            }
        }
    }
    
    # 3. Launch browser if found
    if ($browserPath) {
        try {
            Start-Process -FilePath $browserPath -ArgumentList $Url
            return $true
        } catch {
            # Fall through to fallback
        }
    }
    
    # 4. Fallback: use cmd /c start
    try {
        Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", "", $Url
        return $true
    } catch {
        [System.Windows.Forms.MessageBox]::Show("Failed to open browser. Please manually navigate to: $Url", "BIT-Nav Error")
        return $false
    }
}

# Create form (hidden)
$form = New-Object System.Windows.Forms.Form
$form.WindowState = "Minimized"
$form.ShowInTaskbar = $false
$form.Size = New-Object System.Drawing.Size(1, 1)

# Create tray icon
$notifyIcon = New-Object System.Windows.Forms.NotifyIcon
$notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
$notifyIcon.Text = "BIT-Nav"
$notifyIcon.Visible = $true

# Create context menu
$contextMenu = New-Object System.Windows.Forms.ContextMenuStrip

# Status item
$statusItem = New-Object System.Windows.Forms.ToolStripMenuItem
$statusItem.Text = "Status: Checking..."
$statusItem.Enabled = $false
[void]$contextMenu.Items.Add($statusItem)
[void]$contextMenu.Items.Add("-")

# Start service
$startItem = New-Object System.Windows.Forms.ToolStripMenuItem
$startItem.Text = "Start Service"
$startItem.Add_Click({
    # Check if default port is occupied
    $basePortStr = ":" + $script:BasePort
    $portInUse = netstat -ano | findstr $basePortStr | findstr "LISTENING"
    if ($portInUse) {
        # Find available port
        $newPort = Find-AvailablePort -StartPort $script:BasePort
        if ($newPort) {
            $script:ServicePort = $newPort
            $script:ServiceUrl = "http://localhost:" + $newPort
        } else {
            [System.Windows.Forms.MessageBox]::Show("No available port found", "Error")
            return
        }
    } else {
        $script:ServicePort = $script:BasePort
        $script:ServiceUrl = "http://localhost:" + $script:BasePort
    }
    
    $scriptPath = Join-Path $PSScriptRoot "start-service.ps1"
    $argList = "-ExecutionPolicy Bypass -File `"" + $scriptPath + "`" -Port " + $script:ServicePort
    Start-Process powershell.exe -ArgumentList $argList -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Check-Status
})
[void]$contextMenu.Items.Add($startItem)

# Stop service
$stopItem = New-Object System.Windows.Forms.ToolStripMenuItem
$stopItem.Text = "Stop Service"
$stopItem.Add_Click({
    # Find and stop any Streamlit service on ports 8501-8510
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portInfo = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portInfo) {
            $parts = $portInfo -split '\s+'
            $procId = $parts[$parts.Count - 1]
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    Start-Sleep -Seconds 2
    Check-Status
})
[void]$contextMenu.Items.Add($stopItem)

# Open browser
$openItem = New-Object System.Windows.Forms.ToolStripMenuItem
$openItem.Text = "Open Page"
$openItem.Add_Click({
    $foundPort = Find-RunningPort
    
    if ($foundPort -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Service is not running. Please start the service first.", "BIT-Nav")
        return
    }
    
    [string]$url = "http://localhost:$foundPort"
    Open-UrlInBrowser -Url $url | Out-Null
})
[void]$contextMenu.Items.Add($openItem)

[void]$contextMenu.Items.Add("-")

# Exit
$exitItem = New-Object System.Windows.Forms.ToolStripMenuItem
$exitItem.Text = "Exit"
$exitItem.Add_Click({
    # Stop all Streamlit services on ports 8501-8510
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portInfo = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portInfo) {
            $parts = $portInfo -split '\s+'
            $procId = $parts[$parts.Count - 1]
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
    $notifyIcon.Visible = $false
    $form.Close()
})
[void]$contextMenu.Items.Add($exitItem)

$notifyIcon.ContextMenuStrip = $contextMenu
$notifyIcon.Add_DoubleClick({
    $foundPort = Find-RunningPort
    
    if ($foundPort -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Service is not running. Please start the service first.", "BIT-Nav")
        return
    }
    
    [string]$url = "http://localhost:$foundPort"
    Open-UrlInBrowser -Url $url | Out-Null
})

# Check status - scan all possible ports
function Check-Status {
    $foundPort = Find-RunningPort
    
    if ($foundPort -ne 0) {
        $script:ServicePort = $foundPort
        $script:IsRunning = $true
        $statusItem.Text = "Running on port " + $foundPort
        $startItem.Enabled = $false
        $stopItem.Enabled = $true
        $notifyIcon.Icon = [System.Drawing.SystemIcons]::Information
    } else {
        $script:IsRunning = $false
        $statusItem.Text = "Stopped"
        $startItem.Enabled = $true
        $stopItem.Enabled = $false
        $notifyIcon.Icon = [System.Drawing.SystemIcons]::Warning
    }
}

# Timer
$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 5000
$timer.Add_Tick({ Check-Status })
$timer.Start()

Check-Status
$notifyIcon.ShowBalloonTip(2000, "BIT-Nav", "Tray started", "Info")

[System.Windows.Forms.Application]::Run($form)
