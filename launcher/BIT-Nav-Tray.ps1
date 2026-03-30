# BIT-Nav Tray Manager v2
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# Config
$script:BasePort = 8501
$script:ServicePort = 8501
$script:ServiceUrl = "http://localhost:8501"
$script:ProjectDir = Split-Path -Parent $PSScriptRoot
$script:IsRunning = $false

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
    # Find which port the service is running on
    $foundPort = 0
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portCheck = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portCheck) {
            $foundPort = $p
            break
        }
    }
    
    if ($foundPort -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Service is not running. Please start the service first.", "BIT-Nav")
        return
    }
    
    # Build URL and open browser
    [string]$url = "http://localhost:$foundPort"
    
    # Check if default browser is valid
    try {
        $browserCmd = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\http\shell\open\command" -Name "(Default)" -ErrorAction Stop)."(Default)"
        if ($browserCmd -match '"([^"]+)"') {
            $browserPath = $matches[1]
        } else {
            $browserPath = ($browserCmd -split ' ')[0]
        }
        # Verify browser executable exists
        if (-not (Test-Path $browserPath)) {
            [System.Windows.Forms.MessageBox]::Show("Default browser not found at: $browserPath`n`nPlease check your default browser settings or manually navigate to: $url", "BIT-Nav Warning")
            return
        }
        # Open URL with verified browser
        Start-Process -FilePath $browserPath -ArgumentList $url
    } catch {
        # Fallback to simple start command
        try {
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", $url
        } catch {
            [System.Windows.Forms.MessageBox]::Show("Failed to open browser. Please manually navigate to: $url", "BIT-Nav Error")
        }
    }
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
    # Find which port the service is running on
    $foundPort = 0
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portCheck = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portCheck) {
            $foundPort = $p
            break
        }
    }
    
    if ($foundPort -eq 0) {
        [System.Windows.Forms.MessageBox]::Show("Service is not running. Please start the service first.", "BIT-Nav")
        return
    }
    
    [string]$url = "http://localhost:$foundPort"
    try {
        $browserCmd = (Get-ItemProperty -Path "Registry::HKEY_CLASSES_ROOT\http\shell\open\command" -Name "(Default)" -ErrorAction Stop)."(Default)"
        if ($browserCmd -match '"([^"]+)"') {
            $browserPath = $matches[1]
        } else {
            $browserPath = ($browserCmd -split ' ')[0]
        }
        if (-not (Test-Path $browserPath)) {
            [System.Windows.Forms.MessageBox]::Show("Default browser not found: $browserPath`n`nPlease check your default browser settings.", "BIT-Nav Warning")
            return
        }
        Start-Process -FilePath $browserPath -ArgumentList $url
    } catch {
        try {
            Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "start", $url
        } catch {
            [System.Windows.Forms.MessageBox]::Show("Failed to open browser. Please manually navigate to: $url", "BIT-Nav Error")
        }
    }
})

# Check status - scan all possible ports
function Check-Status {
    $foundPort = $null
    # Scan ports 8501-8510 to find running service
    for ($p = 8501; $p -le 8510; $p++) {
        $portStr = ":" + $p
        $portCheck = netstat -ano | findstr $portStr | findstr "LISTENING"
        if ($portCheck) {
            $foundPort = $p
            break
        }
    }
    
    if ($foundPort) {
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
