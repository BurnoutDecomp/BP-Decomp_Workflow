function Get-BrnWindowsFileLinkCount([string]$Path) {
    if ($null -eq ('BrnPrivateFileIdentity' -as [type])) {
        $source = @'
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

public static class BrnPrivateFileIdentity
{
    [StructLayout(LayoutKind.Sequential)]
    private struct FILETIME { public uint Low; public uint High; }

    [StructLayout(LayoutKind.Sequential)]
    private struct BY_HANDLE_FILE_INFORMATION
    {
        public uint Attributes;
        public FILETIME Creation;
        public FILETIME LastAccess;
        public FILETIME LastWrite;
        public uint VolumeSerial;
        public uint SizeHigh;
        public uint SizeLow;
        public uint LinkCount;
        public uint FileIndexHigh;
        public uint FileIndexLow;
    }

    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern SafeFileHandle CreateFileW(string name, uint access, uint share,
        IntPtr security, uint creation, uint flags, IntPtr template);

    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool GetFileInformationByHandle(SafeFileHandle handle,
        out BY_HANDLE_FILE_INFORMATION info);

    public static uint GetLinkCount(string path)
    {
        using (SafeFileHandle handle = CreateFileW(path, 0u, 0x1u | 0x2u | 0x4u,
            IntPtr.Zero, 3u, 0x02000000u, IntPtr.Zero))
        {
            if (handle == null || handle.IsInvalid)
                throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateFileW failed");
            BY_HANDLE_FILE_INFORMATION info;
            if (!GetFileInformationByHandle(handle, out info))
                throw new Win32Exception(Marshal.GetLastWin32Error(), "GetFileInformationByHandle failed");
            return info.LinkCount;
        }
    }
}
'@
        Add-Type -TypeDefinition $source -Language CSharp -ErrorAction Stop | Out-Null
    }
    return [uint32][BrnPrivateFileIdentity]::GetLinkCount([IO.Path]::GetFullPath($Path))
}

function Assert-BrnNoReparsePath([string]$Path,[string]$Label,[switch]$RequireLeaf) {
    $full = [IO.Path]::GetFullPath($Path)
    $root = [IO.Path]::GetPathRoot($full)
    if ([string]::IsNullOrWhiteSpace($root)) { throw "$Label has no absolute path root: $Path" }
    $relative = $full.Substring($root.Length)
    $parts = @($relative -split '\\' | Where-Object { $_ -ne '' })
    $cursor = $root
    for ($i=0; $i -lt $parts.Count; ++$i) {
        $cursor = Join-Path $cursor $parts[$i]
        if (!(Test-Path -LiteralPath $cursor)) {
            if ($RequireLeaf -and $i -eq ($parts.Count-1)) { throw "$Label is missing: $full" }
            break
        }
        $item = Get-Item -LiteralPath $cursor -Force
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "$Label path contains a reparse point: $cursor" }
        if ($i -lt ($parts.Count-1) -and !$item.PSIsContainer) { throw "$Label path ancestor is not a directory: $cursor" }
    }
    if ($RequireLeaf -and !(Test-Path -LiteralPath $full)) { throw "$Label is missing: $full" }
    return $full
}

function Assert-BrnStageOutsideShippingOut([string]$StageRoot,[string]$ShippingOut,[string]$Label='private stage') {
    $stage = [IO.Path]::GetFullPath($StageRoot).TrimEnd('\')
    $protected = [IO.Path]::GetFullPath($ShippingOut).TrimEnd('\')
    $protectedPrefix = $protected + '\'
    if ($stage -ieq $protected -or $stage.StartsWith($protectedPrefix,[StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must be outside the immutable shipping_out tree: $stage"
    }
    return $stage
}

function Assert-BrnPrivateProfile([string]$Path,[string]$Label) {
    $full = Assert-BrnNoReparsePath $Path $Label
    if (!(Test-Path -LiteralPath $full -PathType Leaf)) { return [pscustomobject]@{path=$full;status='absent_before_fixture_copy';link_count=0} }
    $item = Get-Item -LiteralPath $full -Force
    if ($item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "$Label is not a regular private profile file: $full" }
    $links = Get-BrnWindowsFileLinkCount $full
    if ($links -ne 1) { throw "$Label has $links filesystem links; refusing shared/hard-linked profile path: $full" }
    return [pscustomobject]@{path=$full;status='regular_single_link_private_file';link_count=$links;bytes=[long]$item.Length;
        sha256=(Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()}
}
