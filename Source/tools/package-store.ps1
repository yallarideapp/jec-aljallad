#Requires -Version 7.0
<#
.SYNOPSIS
  Builds everything that is generated from Source/ for JEC | AlJallad Contracting.
.DESCRIPTION
  Demo/                                        portable preview: runtime files, Open-demo.html, launchers, README-AR.md
  JEC-AlJallad-complete-with-demo/JEC-AlJallad/
      JEC-AlJallad-website-source.zip          Source + launchers + guides + client documents (entries under JEC-AlJallad/)
      Demo/  Documents/  README-AR.md  Cloudflare-guide.md
  The live site is not built here: Cloudflare builds Source/ from GitHub on every push (see Cloudflare-guide.md).
  JEC-AlJallad-complete-with-demo.zip          the delivery folder, zipped
  Then hides the internal items (Windows: Hidden attribute, macOS: chflags hidden) and prints a JSON summary.
  Run it through UPDATE-PACKAGE.cmd (Windows) or UPDATE-PACKAGE.command (macOS). Never edit the outputs by hand.
#>
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$SiteName = 'JEC-AlJallad'
$Sep      = [IO.Path]::DirectorySeparatorChar
$Root     = [IO.Path]::GetFullPath([IO.Path]::Combine($PSScriptRoot, '..', '..')).TrimEnd($Sep)

# ---------------------------------------------------------------- explicit lists
$RuntimeFiles   = @('index.html')                                         # relative to Source/
$RuntimeDirs    = @('v', 'vi', 'tiles', 'media', 'renders', 'real')       # relative to Source/
$DemoExtras     = @('server.cjs', 'START-DEMO.cmd', 'START-DEMO.command') # relative to Source/
$RootFiles      = @('README-AR.md', 'Cloudflare-guide.md', 'START-DEMO.cmd', 'START-DEMO.command',
                    'UPDATE-PACKAGE.cmd', 'UPDATE-PACKAGE.command', 'server.cjs', '.gitignore')
$ClientDocs     = @('Documents/README-AR.md', 'Documents/SOURCES.md', 'Documents/IMAGE-ASSETS.md')
$MediaOriginals = 'Documents/Media-originals'
$Internal       = @('Source', 'Demo', 'Documents', 'Production', 'AGENTS.md', 'JEC-ALJALLAD-CONTEXT.md', 'README-AR.md',
                    'Cloudflare-guide.md', 'UPDATE-PACKAGE.cmd', 'UPDATE-PACKAGE.command', 'START-DEMO.cmd',
                    'START-DEMO.command', 'server.cjs', '.gitignore')
$Stored         = @('.mp4', '.webm', '.webp', '.jpg', '.jpeg', '.png', '.zip', '.gz', '.woff2')   # already compressed
$Forbidden      = '(^|/)(AGENTS\.md|[^/]*-CONTEXT\.md|Evidence|Archives|Production|public-preview|node_modules|dist|\.wrangler|\.dev\.vars|\.env[^/]*)(/|$)'

# ---------------------------------------------------------------- helpers
function Resolve-Inside([string]$Relative) {
    $full = [IO.Path]::GetFullPath([IO.Path]::Combine($Root, $Relative)).TrimEnd($Sep)
    if ($full -ne $Root -and -not $full.StartsWith($Root + $Sep, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing a path outside the project: $full"
    }
    return $full
}

function Test-Skip([string]$Rel) {
    foreach ($seg in $Rel.Split('/')) {
        if ($seg -in @('.DS_Store', 'Thumbs.db', 'desktop.ini', 'node_modules', '__pycache__', 'dist', '.wrangler', '.dev.vars')) { return $true }
        if ($seg -like '.env*' -or $seg -like '*.log' -or $seg -like '*.tmp') { return $true }
    }
    return $false
}

function Get-Files([string]$BaseFull, [string]$Rel) {
    # every file of $Rel (a file or a folder under $BaseFull) as { Full, Rel, Length }; Rel uses '/'
    $p = [IO.Path]::GetFullPath([IO.Path]::Combine($BaseFull, $Rel))
    if (Test-Path -LiteralPath $p -PathType Leaf) { $items = @(Get-Item -LiteralPath $p -Force) }
    elseif (Test-Path -LiteralPath $p -PathType Container) { $items = @(Get-ChildItem -LiteralPath $p -Recurse -File -Force) }
    else { throw "Missing: $p" }
    foreach ($it in $items) {
        $r = [IO.Path]::GetRelativePath($BaseFull, $it.FullName).Replace('\', '/')
        if (-not (Test-Skip $r)) { [pscustomobject]@{ Full = $it.FullName; Rel = $r; Length = $it.Length } }
    }
}

function Reset-Folder([string]$Relative) {
    $full = Resolve-Inside $Relative
    if (Test-Path -LiteralPath $full) { Remove-Item -LiteralPath $full -Recurse -Force }
    [void][IO.Directory]::CreateDirectory($full)
    return $full
}

function Copy-Files($Files, [string]$DestFull) {
    foreach ($f in $Files) {
        $d = [IO.Path]::Combine($DestFull, $f.Rel)
        [void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($d))
        [IO.File]::Copy($f.Full, $d, $true)
    }
}

function Write-Text([string]$Full, [string]$Text) {
    [IO.File]::WriteAllText($Full, $Text.Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
}

function New-Zip([string]$ZipFull, $Entries) {
    # Entries: { Full, Name } where Name is the path inside the ZIP ('/' separated)
    $tmp = "$ZipFull.tmp"
    if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
    $expected = [ordered]@{}
    foreach ($e in $Entries) {
        if ($expected.Contains($e.Name)) { throw "Duplicate ZIP entry: $($e.Name)" }
        if ($e.Name -match $Forbidden) { throw "Internal file would go into a ZIP: $($e.Name)" }
        $expected[$e.Name] = (Get-Item -LiteralPath $e.Full -Force).Length
    }
    $fs = [IO.File]::Open($tmp, [IO.FileMode]::CreateNew)
    try {
        $zip = [IO.Compression.ZipArchive]::new($fs, [IO.Compression.ZipArchiveMode]::Create)
        try {
            foreach ($e in $Entries) {
                $ext = [IO.Path]::GetExtension($e.Full).ToLowerInvariant()
                $level = if ($Stored -contains $ext) { [IO.Compression.CompressionLevel]::NoCompression } else { [IO.Compression.CompressionLevel]::Optimal }
                $entry = [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $e.Full, $e.Name, $level)
                if ($ext -in @('.command', '.sh')) { $entry.ExternalAttributes = 0x81ED0000 }   # rwxr-xr-x when unzipped on macOS
            }
        } finally { $zip.Dispose() }
    } finally { $fs.Dispose() }
    # reopen and compare entry list and sizes before the archive replaces the old one
    $check = [IO.Compression.ZipFile]::OpenRead($tmp)
    try {
        if ($check.Entries.Count -ne $expected.Count) { throw "ZIP check failed: $ZipFull has $($check.Entries.Count) entries, expected $($expected.Count)" }
        foreach ($ce in $check.Entries) {
            if (-not $expected.Contains($ce.FullName) -or $expected[$ce.FullName] -ne $ce.Length) { throw "ZIP check failed: $ZipFull at $($ce.FullName)" }
        }
    } finally { $check.Dispose() }
    if (Test-Path -LiteralPath $ZipFull) { Remove-Item -LiteralPath $ZipFull -Force }
    Move-Item -LiteralPath $tmp -Destination $ZipFull
    return [pscustomobject]@{
        archive = [IO.Path]::GetRelativePath($Root, $ZipFull).Replace('\', '/')
        entries = $expected.Count
        mb      = [math]::Round((Get-Item -LiteralPath $ZipFull -Force).Length / 1MB, 1)
    }
}

function Set-Hidden([string]$Relative) {
    $full = Resolve-Inside $Relative
    if (-not (Test-Path -LiteralPath $full)) { return }
    if ($IsWindows) {
        $i = Get-Item -LiteralPath $full -Force
        $i.Attributes = $i.Attributes -bor [IO.FileAttributes]::Hidden
    } elseif ($IsMacOS) {
        & chflags hidden $full
    }
}

# ---------------------------------------------------------------- 1. runtime files
$SourceFull = Resolve-Inside 'Source'
$runtime = @()
foreach ($f in $RuntimeFiles) { $runtime += @(Get-Files $SourceFull $f) }
foreach ($d in $RuntimeDirs)  { $runtime += @(Get-Files $SourceFull $d) }
if (-not ($runtime | Where-Object Rel -eq 'index.html')) { throw 'Source/index.html is missing' }
foreach ($big in ($runtime | Where-Object Length -gt 20MB)) { Write-Warning "Over 20 MB (some hosts refuse it): Source/$($big.Rel)" }

# ---------------------------------------------------------------- 2. Demo/
$DemoFull = Reset-Folder 'Demo'
Copy-Files $runtime $DemoFull
foreach ($f in $DemoExtras) { Copy-Files @(Get-Files $SourceFull $f) $DemoFull }
Write-Text ([IO.Path]::Combine($DemoFull, 'Open-demo.html')) @'
<!doctype html>
<html lang="ar" dir="rtl"><head><meta charset="utf-8"><title>JEC | AlJallad — Demo</title>
<script>location.replace('index.html' + location.hash);</script></head>
<body><a href="index.html">فتح الموقع</a></body></html>
'@
Write-Text ([IO.Path]::Combine($DemoFull, 'README-AR.md')) @'
# نسخة العرض (Demo) — JEC | AlJallad Contracting

- أسهل طريقة: شغّل `START-DEMO.command` على الماك أو `START-DEMO.cmd` على ويندوز. يفتح الموقع على http://localhost:8080 ويحتاج Node.js مثبّتاً.
- بدون Node: افتح `Open-demo.html`. الموقع يعمل، لكن التنقّل داخل الفيلم أثناء السكرول يكون أقل دقة.
- على الماك، إذا ظهرت رسالة صلاحيات عند الضغط المزدوج: افتح Terminal داخل هذا المجلد واكتب `bash START-DEMO.command`.
- يحتاج اتصالاً بالإنترنت لتحميل الخطوط ومكتبة GSAP.
- المبنى المعروض تصوّر معماري بالذكاء الاصطناعي وليس مشروعاً منفّذاً. قسم المشاريع الحقيقية مأخوذ من حساب @jallad.contracting.
'@
if ($IsMacOS -or $IsLinux) { & chmod 755 ([IO.Path]::Combine($DemoFull, 'START-DEMO.command')) }

# ---------------------------------------------------------------- 3. delivery folder and the source ZIP
$OuterRel = "$SiteName-complete-with-demo"
$OuterFull = Reset-Folder $OuterRel
$DelFull = [IO.Path]::Combine($OuterFull, $SiteName)
[void][IO.Directory]::CreateDirectory($DelFull)

$srcEntries = @()
foreach ($f in @(Get-Files $Root 'Source'))      { $srcEntries += [pscustomobject]@{ Full = $f.Full; Name = "$SiteName/$($f.Rel)" } }
foreach ($r in $RootFiles)                       { foreach ($f in @(Get-Files $Root $r)) { $srcEntries += [pscustomobject]@{ Full = $f.Full; Name = "$SiteName/$($f.Rel)" } } }
foreach ($r in $ClientDocs)                      { foreach ($f in @(Get-Files $Root $r)) { $srcEntries += [pscustomobject]@{ Full = $f.Full; Name = "$SiteName/$($f.Rel)" } } }
foreach ($f in @(Get-Files $Root $MediaOriginals)) { $srcEntries += [pscustomobject]@{ Full = $f.Full; Name = "$SiteName/$($f.Rel)" } }

$results = @()
$results += New-Zip ([IO.Path]::Combine($DelFull, "$SiteName-website-source.zip")) $srcEntries

Copy-Files @(Get-Files $Root 'Demo') $DelFull
Copy-Files @($ClientDocs | ForEach-Object { Get-Files $Root $_ }) $DelFull
Copy-Files @(Get-Files $SourceFull 'tools/delivery-README-AR.md' | ForEach-Object { [pscustomobject]@{ Full = $_.Full; Rel = 'README-AR.md' } }) $DelFull
Copy-Files @(Get-Files $Root 'Cloudflare-guide.md') $DelFull
if ($IsMacOS -or $IsLinux) { & chmod 755 ([IO.Path]::Combine($DelFull, 'Demo', 'START-DEMO.command')) }

# ---------------------------------------------------------------- 4. the complete ZIP
$results += New-Zip (Resolve-Inside "$SiteName-complete-with-demo.zip") @(Get-Files $OuterFull $SiteName | ForEach-Object { [pscustomobject]@{ Full = $_.Full; Name = $_.Rel } })

# ---------------------------------------------------------------- 5. clean folder view
foreach ($i in $Internal) { Set-Hidden $i }

[pscustomobject]@{
    project  = $SiteName
    root     = $Root
    demo     = [pscustomobject]@{ files = @(Get-ChildItem -LiteralPath $DemoFull -Recurse -File -Force).Count }
    archives = $results
    visible  = @("$SiteName-complete-with-demo", "$SiteName-complete-with-demo.zip")
} | ConvertTo-Json -Depth 4
