Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")
Dim outputFile

outputFile = "D:\JemmaRepo\Jemma\MACHINE_FACTS_VBS.txt"
Set outFile = objFSO.CreateTextFile(outputFile, True)

' CPU Info
outFile.WriteLine("================================================================================")
outFile.WriteLine("(1) CPU INFORMATION")
outFile.WriteLine("================================================================================")
Set objWMI = GetObject("winmgmts:")
Set colItems = objWMI.ExecQuery("Select * from Win32_Processor")
For Each objItem in colItems
    outFile.WriteLine("CPU Name: " & objItem.Name)
    outFile.WriteLine("Manufacturer: " & objItem.Manufacturer)
    outFile.WriteLine("Cores: " & objItem.NumberOfCores)
    outFile.WriteLine("Threads: " & objItem.NumberOfLogicalProcessors)
Next

' Disk Info
outFile.WriteLine("")
outFile.WriteLine("================================================================================")
outFile.WriteLine("(2) DISK INFORMATION")
outFile.WriteLine("================================================================================")
Set colItems = objWMI.ExecQuery("Select * from Win32_LogicalDisk where DriveType=3")
For Each objItem in colItems
    outFile.WriteLine("Drive: " & objItem.Name)
    outFile.WriteLine("Size: " & objItem.Size & " bytes")
    outFile.WriteLine("Free Space: " & objItem.FreeSpace & " bytes")
    outFile.WriteLine("")
Next

' Network Adapters
outFile.WriteLine("")
outFile.WriteLine("================================================================================")
outFile.WriteLine("(3) NETWORK ADAPTERS")
outFile.WriteLine("================================================================================")
Set colItems = objWMI.ExecQuery("Select * from Win32_NetworkAdapter where NetConnectionStatus=2")
For Each objItem in colItems
    outFile.WriteLine("Adapter: " & objItem.Name)
    outFile.WriteLine("Description: " & objItem.Description)
    outFile.WriteLine("MAC Address: " & objItem.MACAddress)
    outFile.WriteLine("Speed: " & objItem.Speed)
    outFile.WriteLine("")
Next

' GPU Info
outFile.WriteLine("")
outFile.WriteLine("================================================================================")
outFile.WriteLine("(4) GPU INFORMATION")
outFile.WriteLine("================================================================================")
Set colItems = objWMI.ExecQuery("Select * from Win32_VideoController")
For Each objItem in colItems
    outFile.WriteLine("GPU: " & objItem.Name)
    outFile.WriteLine("Driver Version: " & objItem.DriverVersion)
    outFile.WriteLine("")
Next

outFile.Close()

' Display file
MsgBox "Facts saved to: " & outputFile, 0, "System Facts Collection Complete"
