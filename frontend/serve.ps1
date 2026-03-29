$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add('http://localhost:5500/')
$listener.Start()
Write-Host "Serving $root on http://localhost:5500/"

$mime = @{
    '.html' = 'text/html; charset=utf-8'
    '.css'  = 'text/css; charset=utf-8'
    '.js'   = 'application/javascript; charset=utf-8'
    '.svg'  = 'image/svg+xml'
    '.png'  = 'image/png'
    '.jpg'  = 'image/jpeg'
    '.jpeg' = 'image/jpeg'
    '.ico'  = 'image/x-icon'
    '.json' = 'application/json; charset=utf-8'
}

while ($listener.IsListening) {
    $context = $listener.GetContext()
    try {
        $path = $context.Request.Url.AbsolutePath.TrimStart('/')
        if ([string]::IsNullOrWhiteSpace($path)) {
            $path = 'index.html'
        }

        $filePath = Join-Path $root $path
        if (!(Test-Path $filePath -PathType Leaf)) {
            $context.Response.StatusCode = 404
            $bytes = [System.Text.Encoding]::UTF8.GetBytes('Not Found')
            $context.Response.OutputStream.Write($bytes, 0, $bytes.Length)
            $context.Response.Close()
            continue
        }

        $ext = [System.IO.Path]::GetExtension($filePath).ToLowerInvariant()
        if ($mime.ContainsKey($ext)) {
            $context.Response.ContentType = $mime[$ext]
        }

        $fileBytes = [System.IO.File]::ReadAllBytes($filePath)
        $context.Response.ContentLength64 = $fileBytes.Length
        $context.Response.OutputStream.Write($fileBytes, 0, $fileBytes.Length)
        $context.Response.Close()
    } catch {
        try { $context.Response.StatusCode = 500; $context.Response.Close() } catch {}
    }
}
