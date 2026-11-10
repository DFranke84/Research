' Starts Library Manager from wherever this Research folder is (no console window).
' Double-click it, or right-click > Send to > Desktop (create shortcut) to put it on the desktop.
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
pyw = here & "\_scripts\.venv\Scripts\pythonw.exe"
app = here & "\_scripts\library_manager.pyw"
If Not fso.FileExists(pyw) Then
    MsgBox "Library Manager isn't set up on this PC yet (or its Python was moved)." & vbCrLf & vbCrLf & _
           "Double-click Setup.bat in this folder to set it up, then start Library Manager again:" & vbCrLf & here, _
           vbExclamation, "Library Manager"
    WScript.Quit 1
End If
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = here
sh.Run """" & pyw & """ """ & app & """", 1, False
