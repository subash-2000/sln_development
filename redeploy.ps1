param(
    [string]$Server = '13.60.31.242',
    [string]$User = 'ec2-user',
    [string]$KeyFile = "$PSScriptRoot\sln.ppk",
    [string]$HostKey = 'SHA256:ZJRJGYcmLXFemmzYs57qP2Qk+Ehe8cn+UHBtZ27JNJ8'
)

$ErrorActionPreference = 'Stop'
$plink = 'C:\Program Files\PuTTY\plink.exe'
$pscp = 'C:\Program Files\PuTTY\pscp.exe'
$archive = Join-Path ([System.IO.Path]::GetTempPath()) 'sln-wms-release.tar.gz'
$npmCache = Join-Path $PSScriptRoot '.deployment-cache\npm'

foreach ($path in @($plink, $pscp, $KeyFile)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Required file not found: $path" }
}

Push-Location $PSScriptRoot
try {
    $env:VITE_API_BASE_URL = '/api/v1'
    $env:VITE_APP_ENV = 'production'
    if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'warehouse_frontend\node_modules'))) {
        & npm.cmd --cache $npmCache --prefix warehouse_frontend ci --legacy-peer-deps
        if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
    }
    $viteCmd = Join-Path $PSScriptRoot 'warehouse_frontend\node_modules\.bin\vite.cmd'
    if (Test-Path -LiteralPath $viteCmd) {
        & npm.cmd --prefix warehouse_frontend run build
    }
    else {
        & node (Join-Path $PSScriptRoot 'warehouse_frontend\node_modules\vite\bin\vite.js') build `
            (Join-Path $PSScriptRoot 'warehouse_frontend')
    }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }

    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
    tar -czf $archive `
        --exclude='.git' `
        --exclude='node_modules' `
        --exclude='.deployment-cache' `
        --exclude='.venv' `
        --exclude='venv' `
        --exclude='__pycache__' `
        --exclude='*.pyc' `
        --exclude='.env' `
        --exclude='.env.local' `
        --exclude='warehouse/uploads' `
        --exclude='sln.ppk' `
        --exclude='sln.pem' `
        --exclude='*.zip' `
        warehouse warehouse_frontend deploy
    if ($LASTEXITCODE -ne 0) { throw 'Creating deployment archive failed.' }

    & $pscp -batch -hostkey $HostKey -i $KeyFile $archive "${User}@${Server}:/tmp/sln-wms-release.tar.gz"
    if ($LASTEXITCODE -ne 0) { throw 'Uploading deployment archive failed.' }
    & $pscp -batch -hostkey $HostKey -i $KeyFile (Join-Path $PSScriptRoot 'deploy\server-deploy.sh') "${User}@${Server}:/tmp/sln-wms-bootstrap.sh"
    if ($LASTEXITCODE -ne 0) { throw 'Uploading bootstrap script failed.' }
    & $plink -batch -hostkey $HostKey -i $KeyFile "${User}@${Server}" "sudo install -m 0700 /tmp/sln-wms-bootstrap.sh /opt/sln-wms-bootstrap.sh && sudo bash /opt/sln-wms-bootstrap.sh"
    if ($LASTEXITCODE -ne 0) { throw 'Remote deployment failed.' }
}
finally {
    Pop-Location
    Remove-Item -LiteralPath $archive -Force -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_API_BASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:VITE_APP_ENV -ErrorAction SilentlyContinue
}

