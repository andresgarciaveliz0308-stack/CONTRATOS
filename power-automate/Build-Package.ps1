<#
.SYNOPSIS
    Prepara los flujos para importarlos en Power Automate.

.DESCRIPTION
    Hace dos cosas:

      1. Reemplaza los marcadores de posicion de cada definition.json por los
         valores reales del entorno (URL del sitio e id de cuenta de DocuSign) y
         deja el resultado en ./build/<flujo>/definition.json.

      2. Con -Empaquetar, arma ademas un .zip con el formato de "paquete de
         soluciones heredado" que acepta Power Automate en
         Mis flujos > Importar > Paquete de importacion (heredado).

    NOTA SOBRE EL EMPAQUETADO
    El formato del paquete heredado no es un contrato publico documentado por
    Microsoft y cambia entre versiones del servicio. Si la importacion es
    rechazada, usa el archivo de ./build/ como referencia y construye el flujo
    en el disenador siguiendo el README.md de cada carpeta: ahi estan todas las
    acciones y expresiones, en orden. Los flujos generados por este script no se
    han validado contra un tenant real.

.PARAMETER SiteUrl
    URL real del sitio de SharePoint de Contratos.

.PARAMETER DocuSignAccountId
    Id de la cuenta de DocuSign. Solo lo necesitan los flujos 02 y 03.

.PARAMETER Empaquetar
    Ademas de reemplazar los marcadores, genera los .zip importables.

.EXAMPLE
    ./Build-Package.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos"

.EXAMPLE
    ./Build-Package.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
                        -DocuSignAccountId "12345678-aaaa-bbbb-cccc-1234567890ab" `
                        -Empaquetar
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SiteUrl,
    [string] $DocuSignAccountId = '',
    [switch] $Empaquetar
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$raiz    = $PSScriptRoot
$destino = Join-Path $raiz 'build'

function Write-Paso { param([string]$m) Write-Host "`n=== $m" -ForegroundColor Cyan }
function Write-Ok   { param([string]$m) Write-Host "    [+] $m" -ForegroundColor Green }
function Write-Aviso{ param([string]$m) Write-Host "    [!] $m" -ForegroundColor Yellow }

# La URL no debe terminar en barra: se concatena directamente en las definiciones.
$SiteUrl = $SiteUrl.TrimEnd('/')

# Conectores que usa cada flujo. Determina las dependencias del manifiesto.
$ConectoresPorFlujo = @{
    '01-solicitud-aprobacion' = @('shared_sharepointonline', 'shared_approvals', 'shared_office365')
    '02-docusign-envio'       = @('shared_sharepointonline', 'shared_docusign', 'shared_office365')
    '03-docusign-retorno'     = @('shared_sharepointonline', 'shared_docusign', 'shared_office365')
    '04-alertas-vencimiento'  = @('shared_sharepointonline', 'shared_office365')
    '05-numeracion-contrato'  = @('shared_sharepointonline')
    '06-custodia-prestamos'   = @('shared_sharepointonline', 'shared_office365')
}

$NombresVisibles = @{
    '01-solicitud-aprobacion' = 'Contratos - Solicitud de aprobacion'
    '02-docusign-envio'       = 'Contratos - Envio a firma DocuSign'
    '03-docusign-retorno'     = 'Contratos - Retorno de documento firmado'
    '04-alertas-vencimiento'  = 'Contratos - Alertas de vencimiento'
    '05-numeracion-contrato'  = 'Contratos - Numeracion de contratos'
    '06-custodia-prestamos'   = 'Contratos - Control de prestamos de originales'
}

$NombresConector = @{
    'shared_sharepointonline' = 'SharePoint'
    'shared_approvals'        = 'Approvals'
    'shared_office365'        = 'Office 365 Outlook'
    'shared_docusign'         = 'DocuSign'
}

Write-Host @"

  ============================================================
   Preparacion de los flujos de Power Automate
  ============================================================
   Sitio    : $SiteUrl
   DocuSign : $(if ($DocuSignAccountId) { $DocuSignAccountId } else { '(no configurado)' })
   Empaqueta: $($Empaquetar.IsPresent)
  ============================================================
"@ -ForegroundColor White

if (Test-Path $destino) { Remove-Item $destino -Recurse -Force }
New-Item -ItemType Directory -Path $destino -Force | Out-Null

Write-Paso "Reemplazando marcadores"

$carpetas = Get-ChildItem -Path $raiz -Directory |
            Where-Object { Test-Path (Join-Path $_.FullName 'definition.json') } |
            Sort-Object Name

if (-not $carpetas) { throw "No se encontro ninguna carpeta con definition.json en $raiz" }

$preparados = @()

foreach ($carpeta in $carpetas) {
    $nombre = $carpeta.Name
    $json   = Get-Content (Join-Path $carpeta.FullName 'definition.json') -Raw -Encoding UTF8

    $json = $json.Replace('https://CONTOSO.sharepoint.com/sites/Contratos', $SiteUrl)

    if ($json.Contains('DOCUSIGN_ACCOUNT_ID')) {
        if ([string]::IsNullOrWhiteSpace($DocuSignAccountId)) {
            Write-Aviso "$nombre usa DocuSign pero no se indico -DocuSignAccountId: el marcador queda sin reemplazar"
        }
        else {
            $json = $json.Replace('DOCUSIGN_ACCOUNT_ID', $DocuSignAccountId)
        }
    }

    # Falla temprano si el reemplazo dejo el JSON invalido.
    try { $null = $json | ConvertFrom-Json }
    catch { throw "El reemplazo dejo un JSON invalido en ${nombre}: $($_.Exception.Message)" }

    $carpetaDestino = Join-Path $destino $nombre
    New-Item -ItemType Directory -Path $carpetaDestino -Force | Out-Null

    $rutaSalida = Join-Path $carpetaDestino 'definition.json'
    [System.IO.File]::WriteAllText($rutaSalida, $json, [System.Text.UTF8Encoding]::new($false))

    Write-Ok "$nombre"
    $preparados += [pscustomobject]@{ Nombre = $nombre; Json = $json; Carpeta = $carpetaDestino }
}

# ============================================================================
#  EMPAQUETADO
# ============================================================================

if ($Empaquetar) {
    Write-Paso "Generando los paquetes de importacion"
    Write-Aviso "Formato heredado no documentado: si la importacion falla, construye"
    Write-Aviso "el flujo en el disenador siguiendo el README.md de su carpeta."

    Add-Type -AssemblyName System.IO.Compression.FileSystem

    foreach ($flujo in $preparados) {
        $nombre        = $flujo.Nombre
        $nombreVisible = $NombresVisibles[$nombre]
        $conectores    = $ConectoresPorFlujo[$nombre]

        if (-not $nombreVisible) { $nombreVisible = $nombre }
        if (-not $conectores)    { $conectores = @('shared_sharepointonline') }

        $flowId = [guid]::NewGuid().ToString()
        $temp   = Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString())
        $rutaFlujo = Join-Path $temp "Microsoft.Flow/flows/$flowId"
        New-Item -ItemType Directory -Path $rutaFlujo -Force | Out-Null

        # --- Referencias de conexion que el flujo declara
        $connectionReferences = @{}
        foreach ($c in $conectores) {
            $connectionReferences[$c] = @{
                connectionName = $c
                source         = 'Embedded'
                id             = "/providers/Microsoft.PowerApps/apis/$c"
                tier           = 'NotSpecified'
            }
        }

        $recursoFlujo = @{
            id                   = $null
            name                 = $flowId
            type                 = 'Microsoft.Flow/flows'
            suggestedCreationType= 'New'
            creationType         = 'New, Existing, Update'
            details              = @{ displayName = $nombreVisible }
            configurableBy       = 'User'
            hierarchy            = 'Root'
            dependsOn            = @()
        }

        $recursos = @{}
        $dependencias = @()

        foreach ($c in $conectores) {
            $idConector = [guid]::NewGuid().ToString()
            $dependencias += $idConector
            $recursos[$idConector] = @{
                id                    = "/providers/Microsoft.PowerApps/apis/$c"
                name                  = $c
                type                  = 'Microsoft.PowerApps/apis'
                suggestedCreationType = 'Existing'
                creationType          = 'Existing'
                details               = @{
                    displayName = $NombresConector[$c]
                    type        = 'Microsoft.PowerApps/apis'
                }
                configurableBy        = 'System'
                hierarchy             = 'Child'
                dependsOn             = @()
            }
        }

        $recursoFlujo.dependsOn = $dependencias
        $recursos[$flowId] = $recursoFlujo

        $manifiesto = @{
            schema  = '1.0'
            details = @{
                displayName        = $nombreVisible
                description        = "Sistema de Contratos - $nombreVisible"
                createdTime        = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ss.fffffffZ')
                packageTelemetryId = [guid]::NewGuid().ToString()
                creator            = 'Deploy-Contratos'
                sourceEnvironment  = ''
            }
            resources = $recursos
        }

        $definicionFlujo = @{
            name       = $flowId
            id         = "/providers/Microsoft.Flow/flows/$flowId"
            type       = 'Microsoft.Flow/flows'
            properties = @{
                apiId                = '/providers/Microsoft.PowerApps/apis/shared_logicflows'
                displayName          = $nombreVisible
                definition           = ($flujo.Json | ConvertFrom-Json)
                connectionReferences = $connectionReferences
            }
            schemaVersion = '1.0.0.0'
        }

        $utf8 = [System.Text.UTF8Encoding]::new($false)
        [System.IO.File]::WriteAllText(
            (Join-Path $temp 'manifest.json'),
            ($manifiesto | ConvertTo-Json -Depth 20), $utf8)
        [System.IO.File]::WriteAllText(
            (Join-Path $rutaFlujo 'definition.json'),
            ($definicionFlujo | ConvertTo-Json -Depth 40), $utf8)

        $zip = Join-Path $destino "$nombre.zip"
        if (Test-Path $zip) { Remove-Item $zip -Force }
        [System.IO.Compression.ZipFile]::CreateFromDirectory($temp, $zip)
        Remove-Item $temp -Recurse -Force

        Write-Ok "$nombre.zip"
    }
}

Write-Host @"

  ============================================================
   Listo. Resultado en:
     $destino

   Para importar cada flujo:
     Power Automate > Mis flujos > Importar > Paquete de
     importacion (heredado) > seleccionar el .zip > asignar
     las conexiones > Importar.

   Si la importacion falla, construyelo en el disenador con
   el README.md de la carpeta del flujo.
  ============================================================
"@ -ForegroundColor White
