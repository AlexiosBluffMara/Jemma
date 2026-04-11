[CmdletBinding()]
param(
    [switch]$AsJson
)

$ErrorActionPreference = "SilentlyContinue"

function Convert-BytesToGiB {
    param([Nullable[UInt64]]$Value)
    if ($null -eq $Value) {
        return $null
    }
    return [math]::Round(($Value / 1GB), 2)
}

function Resolve-Tool {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$DisplayName,
        [string[]]$CandidatePaths = @()
    )

    if (-not $DisplayName) {
        $DisplayName = $Name
    }

    $command = Get-Command $Name -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($command) {
        return [ordered]@{
            name = $DisplayName
            installed = $true
            source = $command.Source
            discovery = "path"
        }
    }

    foreach ($candidate in $CandidatePaths) {
        if ($candidate -and (Test-Path $candidate)) {
            return [ordered]@{
                name = $DisplayName
                installed = $true
                source = $candidate
                discovery = "filesystem"
            }
        }
    }

    return [ordered]@{
        name = $DisplayName
        installed = $false
        source = $null
        discovery = $null
    }
}

function Get-ToolVersion {
    param(
        [string]$Executable,
        [string[]]$Arguments
    )

    if (-not $Executable -or -not (Test-Path $Executable)) {
        return $null
    }

    try {
        return (& $Executable @Arguments 2>&1 | Out-String).Trim()
    }
    catch {
        return $null
    }
}

$os = Get-CimInstance Win32_OperatingSystem
$computer = Get-CimInstance Win32_ComputerSystem
$cpuName = (Get-ItemProperty "HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0").ProcessorNameString
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpus = Get-CimInstance Win32_VideoController | ForEach-Object {
    [ordered]@{
        name = $_.Name
        driverVersion = $_.DriverVersion
        adapterRamGiB = Convert-BytesToGiB $_.AdapterRAM
    }
}
$disks = Get-Volume | Where-Object DriveLetter | Sort-Object DriveLetter | ForEach-Object {
    [ordered]@{
        drive = "$($_.DriveLetter):"
        label = $_.FileSystemLabel
        filesystem = $_.FileSystem
        sizeGiB = Convert-BytesToGiB $_.Size
        freeGiB = Convert-BytesToGiB $_.SizeRemaining
    }
}
$adapters = Get-NetAdapter | Where-Object Status -eq "Up" | Sort-Object Name | ForEach-Object {
    [ordered]@{
        name = $_.Name
        description = $_.InterfaceDescription
        linkSpeed = $_.LinkSpeed
        macAddress = $_.MacAddress
    }
}

$java = Resolve-Tool -Name "java" -DisplayName "java" -CandidatePaths @(
    "$env:ProgramFiles\Android\openjdk\jdk-21.0.8\bin\java.exe"
)
$adb = Resolve-Tool -Name "adb" -DisplayName "adb" -CandidatePaths @(
    "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
)
$emulator = Resolve-Tool -Name "emulator" -DisplayName "emulator" -CandidatePaths @(
    "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe"
)
$gradle = Resolve-Tool -Name "gradle" -DisplayName "gradle"
$tailscale = Resolve-Tool -Name "tailscale" -DisplayName "tailscale" -CandidatePaths @(
    "$env:ProgramFiles\Tailscale\tailscale.exe"
)
$speedtest = Resolve-Tool -Name "speedtest" -DisplayName "speedtest"
$androidStudio = Resolve-Tool -Name "studio64" -DisplayName "androidStudio" -CandidatePaths @(
    "$env:ProgramFiles\Android\Android Studio\bin\studio64.exe",
    "$env:LOCALAPPDATA\Programs\Android Studio\bin\studio64.exe"
)

$envEvidence = [ordered]@{
    JAVA_HOME = $env:JAVA_HOME
    ANDROID_HOME = $env:ANDROID_HOME
    ANDROID_SDK_ROOT = $env:ANDROID_SDK_ROOT
    ANDROID_AVD_HOME = $env:ANDROID_AVD_HOME
    GRADLE_HOME = $env:GRADLE_HOME
}

$androidEvidencePaths = @(
    "$env:LOCALAPPDATA\Android\Sdk",
    "$env:APPDATA\Google\AndroidStudio2025.3.3\options\android.sdk.path.xml",
    "$env:USERPROFILE\.android",
    "$env:USERPROFILE\.android\avd",
    "$env:USERPROFILE\.android\adbkey",
    "$env:USERPROFILE\.android\adbkey.pub",
    "$env:USERPROFILE\.gradle",
    "$env:USERPROFILE\.gradle\gradle.properties"
) | ForEach-Object {
    [ordered]@{
        path = $_
        exists = Test-Path $_
    }
}

$profile = [ordered]@{
    capturedAt = (Get-Date).ToString("s")
    machineFacts = [ordered]@{
        hostName = $env:COMPUTERNAME
        osCaption = $os.Caption
        osVersion = $os.Version
        buildNumber = $os.BuildNumber
        osArchitecture = $os.OSArchitecture
        manufacturer = $computer.Manufacturer
        model = $computer.Model
        cpuName = $cpuName
        cpuCores = $cpu.NumberOfCores
        cpuLogicalProcessors = $cpu.NumberOfLogicalProcessors
        ramGiB = Convert-BytesToGiB $computer.TotalPhysicalMemory
        gpus = $gpus
        disks = $disks
        activeNetworkAdapters = $adapters
    }
    toolingAvailability = [ordered]@{
        java = $java
        javaVersion = Get-ToolVersion -Executable $java.source -Arguments @("-version")
        androidStudio = $androidStudio
        adb = $adb
        adbVersion = Get-ToolVersion -Executable $adb.source -Arguments @("version")
        emulator = $emulator
        emulatorVersion = Get-ToolVersion -Executable $emulator.source -Arguments @("-version")
        gradle = $gradle
        gradleVersion = Get-ToolVersion -Executable $gradle.source -Arguments @("-v")
        tailscale = $tailscale
        tailscaleVersion = Get-ToolVersion -Executable $tailscale.source -Arguments @("version")
        tailscaleIp = Get-ToolVersion -Executable $tailscale.source -Arguments @("ip")
        tailscaleStatus = Get-ToolVersion -Executable $tailscale.source -Arguments @("status")
        speedtest = $speedtest
    }
    androidToolingEvidence = [ordered]@{
        environmentVariables = $envEvidence
        paths = $androidEvidencePaths
    }
    measurementAssessment = [ordered]@{
        canMeasureNow = @(
            "Local OS, CPU, RAM, GPU, disks, and active adapter link speeds",
            "Installed tooling and Android SDK or Studio evidence",
            "Tailscale client presence, IPs, and peer status"
        )
        cannotMeasureNow = @(
            "Phone-to-desktop Tailscale throughput from this machine alone"
        )
        notes = @(
            "End-to-end throughput requires a second endpoint that can send or receive traffic over the tailnet.",
            "Use a paired phone or another tailnet node with a traffic generator such as iperf3 to measure realistic throughput."
        )
    }
}

if ($AsJson) {
    $profile | ConvertTo-Json -Depth 6
    exit 0
}

Write-Host "== Machine facts =="
Write-Host ("Host: {0}" -f $profile.machineFacts.hostName)
Write-Host ("OS:   {0} {1} (build {2}, {3})" -f $profile.machineFacts.osCaption, $profile.machineFacts.osVersion, $profile.machineFacts.buildNumber, $profile.machineFacts.osArchitecture)
Write-Host ("CPU:  {0}" -f $profile.machineFacts.cpuName)
Write-Host ("RAM:  {0} GiB" -f $profile.machineFacts.ramGiB)
Write-Host "GPUs:"
$profile.machineFacts.gpus | ForEach-Object { Write-Host ("  - {0} (driver {1})" -f $_.name, $_.driverVersion) }
Write-Host "Disks:"
$profile.machineFacts.disks | ForEach-Object { Write-Host ("  - {0} {1} total, {2} free" -f $_.drive, $_.sizeGiB, $_.freeGiB) }
Write-Host "Active network adapters:"
$profile.machineFacts.activeNetworkAdapters | ForEach-Object { Write-Host ("  - {0}: {1} ({2})" -f $_.name, $_.description, $_.linkSpeed) }

Write-Host "`n== Tooling availability =="
foreach ($toolName in "java", "androidStudio", "adb", "emulator", "gradle", "tailscale", "speedtest") {
    $tool = $profile.toolingAvailability[$toolName]
    $status = if ($tool.installed) { "installed" } else { "missing" }
    Write-Host ("- {0}: {1}{2}" -f $tool.name, $status, $(if ($tool.source) { " [$($tool.source)]" } else { "" }))
}

Write-Host "`n== Android tooling evidence =="
$profile.androidToolingEvidence.environmentVariables.GetEnumerator() | ForEach-Object {
    Write-Host ("- {0}: {1}" -f $_.Key, $(if ($_.Value) { $_.Value } else { "<unset>" }))
}
$profile.androidToolingEvidence.paths | Where-Object exists | ForEach-Object {
    Write-Host ("- found: {0}" -f $_.path)
}

Write-Host "`n== Measurement assessment =="
$profile.measurementAssessment.canMeasureNow | ForEach-Object { Write-Host ("- can measure: {0}" -f $_) }
$profile.measurementAssessment.cannotMeasureNow | ForEach-Object { Write-Host ("- cannot measure: {0}" -f $_) }
$profile.measurementAssessment.notes | ForEach-Object { Write-Host ("- note: {0}" -f $_) }
