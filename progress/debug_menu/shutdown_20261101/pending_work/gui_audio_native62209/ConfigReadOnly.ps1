function Get-Sound32DebugIniSoundKeysFromText([string]$Text) {
    $found=[Collections.Generic.List[string]]::new()
    $section=''
    foreach($line in ($Text -split "`r`n|`n|`r")){
        $row=([string]$line).Trim().TrimStart([char]0xFEFF)
        if([string]::IsNullOrWhiteSpace($row) -or $row.StartsWith(';') -or $row.StartsWith('#')){continue}
        if($row -match '^\[(?<name>[^\]]+)\]$'){$section=$Matches.name.Trim();continue}
        if($section -ine 'Debug'){continue}
        $eq=$row.IndexOf('=')
        $key=if($eq -ge 0){$row.Substring(0,$eq).Trim()}else{$row.Trim()}
        $normalized=ConvertTo-Sound32DebugIniPath $key
        if($normalized.StartsWith('sound',[StringComparison]::OrdinalIgnoreCase)){$found.Add($key)}
    }
    return $found.ToArray()
}

function ConvertTo-Sound32DebugIniPath([string]$Text) {
    $normalized=[Text.StringBuilder]::new()
    foreach($character in ([string]$Text).Trim().ToCharArray()){
        $current=$character
        if($current -ceq [char]'\'){$current=[char]'/' }
        if($current -ceq [char]'/' -and ($normalized.Length -eq 0 -or $normalized[$normalized.Length-1] -ceq [char]'/')){continue}
        [void]$normalized.Append([char]::ToLowerInvariant($current))
    }
    while($normalized.Length -gt 0 -and $normalized[$normalized.Length-1] -ceq [char]'/'){$null=$normalized.Remove($normalized.Length-1,1)}
    return $normalized.ToString()
}

function Get-Sound32Win32DebugSectionEntries([string]$Path) {
    if(!(Test-Path -LiteralPath $Path -PathType Leaf)){throw ('private config.ini is missing: '+$Path)}
    if($null -eq ('BrnSound32PrivateIniReader' -as [type])){
        $source=@'
using System;
using System.Runtime.InteropServices;
public static class BrnSound32PrivateIniReader
{
    [DllImport("kernel32.dll", EntryPoint="GetPrivateProfileSectionA", CharSet=CharSet.Ansi, SetLastError=true)]
    public static extern uint GetPrivateProfileSectionA(string section, [Out] byte[] buffer, uint size, string fileName);
}
'@
        Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop | Out-Null
    }
    $full=[IO.Path]::GetFullPath($Path)
    $buffer=[byte[]]::new(65536)
    $count=[BrnSound32PrivateIniReader]::GetPrivateProfileSectionA('Debug',$buffer,[uint32]$buffer.Length,$full)
    if($count -ge ($buffer.Length-2)){throw 'Win32 GetPrivateProfileSectionA returned a truncated Debug section'}
    $entries=[Collections.Generic.List[string]]::new()
    $limit=[int]$count;$start=0
    for($i=0;$i -le $limit;$i++){
        if($i -eq $limit -or $buffer[$i] -eq 0){
            if($i -gt $start){$entries.Add([Text.Encoding]::Default.GetString($buffer,$start,$i-$start))}
            if($i -eq $limit){break}
            $start=$i+1
        }
    }
    return $entries.ToArray()
}

function Get-Sound32DebugIniSoundKeys([string]$Path) {
    $found=[Collections.Generic.List[string]]::new()
    foreach($entry in @(Get-Sound32Win32DebugSectionEntries $Path)){
        $equals=([string]$entry).IndexOf('=')
        $key=if($equals -ge 0){([string]$entry).Substring(0,$equals)}else{[string]$entry}
        $normalized=ConvertTo-Sound32DebugIniPath $key
        if($normalized.StartsWith('sound',[StringComparison]::OrdinalIgnoreCase)){$found.Add($key.Trim())}
    }
    return $found.ToArray()
}
