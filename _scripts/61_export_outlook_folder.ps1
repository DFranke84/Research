# Export (read-only) every email in an Outlook folder - across all open stores/PST files - to a staging folder:
#   <out>\<n>\meta.json, body.txt, body.html, attachments\...
# Usage:  powershell -File 61_export_outlook_folder.ps1 -Path "Email\Recipes" -Out "E:\Research\_work\email_export"
param([string]$Path = "Email\Recipes", [string]$Out = (Join-Path (Split-Path $PSScriptRoot -Parent) "_work\email_export"))
$ErrorActionPreference = "Stop"
$ol = New-Object -ComObject Outlook.Application
$ns = $ol.GetNamespace("MAPI")
New-Item -ItemType Directory -Force $Out | Out-Null
$n = 0
foreach ($s in $ns.Stores) {
    $f = $s.GetRootFolder()
    try { foreach ($part in $Path.Split('\')) { $f = $f.Folders.Item($part) } } catch { continue }
    foreach ($m in $f.Items) {
        if ($m.Class -ne 43) { continue }      # mail items only
        $n++
        $d = Join-Path $Out ("{0:D4}" -f $n)
        New-Item -ItemType Directory -Force (Join-Path $d "attachments") | Out-Null
        [IO.File]::WriteAllText((Join-Path $d "body.txt"), [string]$m.Body, [Text.Encoding]::UTF8)
        [IO.File]::WriteAllText((Join-Path $d "body.html"), [string]$m.HTMLBody, [Text.Encoding]::UTF8)
        $atts = @()
        $i = 0
        foreach ($a in $m.Attachments) {
            $i++
            $name = ($a.FileName -replace '[\\/:*?"<>|]', '_')
            if (-not $name) { $name = "attachment$i" }
            $p = Join-Path (Join-Path $d "attachments") ("{0:D2}_{1}" -f $i, $name)
            try {
                $a.SaveAsFile($p)
                $cid = ""
                try { $cid = $a.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x3712001F") } catch {}
                $atts += @{ file = (Split-Path $p -Leaf); name = $a.FileName; size = (Get-Item $p).Length; cid = $cid }
            } catch { $atts += @{ file = ""; name = $a.FileName; error = $_.Exception.Message } }
        }
        $meta = [ordered]@{
            store = $s.FilePath; folder = $f.FolderPath; subject = [string]$m.Subject
            sender = [string]$m.SenderName; received = $m.ReceivedTime.ToString("yyyy-MM-dd HH:mm")
            attachments = $atts
        }
        [IO.File]::WriteAllText((Join-Path $d "meta.json"), ($meta | ConvertTo-Json -Depth 5), [Text.Encoding]::UTF8)
    }
}
"exported $n emails to $Out"
