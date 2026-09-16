<#
.SYNOPSIS
    Carga los datos iniciales del Sistema de Contratos.

.DESCRIPTION
    Inserta los parametros globales, el catalogo de areas y una matriz de aprobacion
    de ejemplo lista para usar. Opcionalmente carga contratos de demostracion.

    Idempotente: si un registro ya existe (misma clave), lo omite.

    LA MATRIZ DE APROBACION QUE SE CARGA ES UN EJEMPLO. Revisala y ajustala a la
    realidad de la organizacion antes de salir a produccion: los tramos de monto,
    los niveles y los roles son decisiones de negocio.

.PARAMETER SiteUrl
    URL del sitio de Contratos.

.PARAMETER IncluirContratosDemo
    Ademas de la configuracion, crea 5 contratos de ejemplo en distintos estados.
    No usar en produccion.

.PARAMETER ClientId
    Id de la aplicacion de Entra ID para PnP PowerShell.

.EXAMPLE
    ./Seed-DemoData.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos"

.EXAMPLE
    ./Seed-DemoData.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" -IncluirContratosDemo
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SiteUrl,
    [switch] $IncluirContratosDemo,
    [string] $ClientId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Paso { param([string]$m) Write-Host "`n=== $m" -ForegroundColor Cyan }
function Write-Ok   { param([string]$m) Write-Host "    [+] $m" -ForegroundColor Green }
function Write-Skip { param([string]$m) Write-Host "    [=] $m" -ForegroundColor DarkGray }
function Write-Aviso{ param([string]$m) Write-Host "    [!] $m" -ForegroundColor Yellow }

<#
    Agrega un elemento solo si no existe otro con el mismo Title en la lista.
#>
function Add-ElementoUnico {
    param(
        [string]    $Lista,
        [string]    $Title,
        [hashtable] $Valores
    )
    $existentes = Get-PnPListItem -List $Lista -Query `
        "<View><Query><Where><Eq><FieldRef Name='Title' /><Value Type='Text'>$Title</Value></Eq></Where></Query><RowLimit>1</RowLimit></View>" `
        -ErrorAction SilentlyContinue

    if ($null -ne $existentes -and @($existentes).Count -gt 0) {
        Write-Skip "$Lista :: $Title"
        return
    }

    $Valores['Title'] = $Title
    try {
        Add-PnPListItem -List $Lista -Values $Valores -ErrorAction Stop | Out-Null
        Write-Ok "$Lista :: $Title"
    }
    catch { Write-Aviso "$Lista :: $Title -> $($_.Exception.Message)" }
}

# ----------------------------------------------------------------------------

Write-Paso "Conectando a $SiteUrl"
if ($ClientId) { Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId }
else           { Connect-PnPOnline -Url $SiteUrl -Interactive }

$usuarioActual = (Get-PnPProperty -ClientObject (Get-PnPContext).Web -Property CurrentUser).Email
Write-Host "    Usuario actual: $usuarioActual" -ForegroundColor Gray

# ============================================================================
#  PARAMETROS GLOBALES
# ============================================================================

Write-Paso "Parametros globales"

$parametros = @(
    @{ K = 'MONEDA_BASE';            V = 'PEN';                   T = 'Texto';    D = 'Moneda en la que se evalua la matriz de aprobacion.' }
    @{ K = 'TC_USD';                 V = '3.7500';                T = 'Numero';   D = 'Tipo de cambio USD -> moneda base. Actualizar periodicamente.' }
    @{ K = 'TC_EUR';                 V = '4.0500';                T = 'Numero';   D = 'Tipo de cambio EUR -> moneda base. Actualizar periodicamente.' }
    @{ K = 'DIAS_PREAVISO_DEFAULT';  V = '30';                    T = 'Numero';   D = 'Dias de preaviso asignados por defecto a un contrato nuevo.' }
    @{ K = 'DIAS_ALERTA_ESCALONADA'; V = '90,60,30,15,7,1';       T = 'Texto';    D = 'Hitos de alerta antes del vencimiento, separados por coma.' }
    @{ K = 'CORREO_LEGAL';           V = 'legal@empresa.com';     T = 'Correo';   D = 'Buzon del area legal. CAMBIAR.' }
    @{ K = 'CORREO_ADMIN_CONTRATOS'; V = 'contratos@empresa.com'; T = 'Correo';   D = 'Buzon del administrador del sistema. CAMBIAR.' }
    @{ K = 'TEAMS_CANAL_ALERTAS';    V = '';                      T = 'Texto';    D = 'Id del canal de Teams para alertas. Vacio = solo correo.' }
    @{ K = 'SLA_APROBACION_HORAS';   V = '48';                    T = 'Numero';   D = 'SLA por defecto cuando la regla de la matriz no lo define.' }
    @{ K = 'DOCUSIGN_HABILITADO';    V = 'true';                  T = 'Booleano'; D = 'Interruptor general de la firma electronica.' }
    @{ K = 'DOCUSIGN_TEMPLATE_ID';   V = '';                      T = 'Texto';    D = 'GUID de la plantilla de DocuSign. Vacio = sobre libre.' }
    @{ K = 'RETENCION_ANIOS';        V = '10';                    T = 'Numero';   D = 'Anios de retencion del expediente tras la terminacion.' }
    @{ K = 'PREFIJO_CODIGO';         V = 'CTR';                   T = 'Texto';    D = 'Prefijo del correlativo de contratos.' }
    # --- Roles que lee la app de Power Apps para mostrar u ocultar acciones.
    #     Correos separados por punto y coma. COMPLETAR antes de usar la app.
    @{ K = 'ADMINS';                 V = '';                      T = 'Texto';    D = 'Correos con acceso a la pantalla de administracion, separados por ";".' }
    @{ K = 'CUSTODIOS';              V = '';                      T = 'Texto';    D = 'Correos que pueden registrar prestamos y devoluciones, separados por ";".' }
    @{ K = 'LEGAL';                  V = '';                      T = 'Texto';    D = 'Correos que pueden dar el visto bueno legal, separados por ";".' }
)

foreach ($p in $parametros) {
    Add-ElementoUnico -Lista 'Parametros' -Title $p.K -Valores @{
        Valor = $p.V; Tipo = $p.T; Descripcion = $p.D
    }
}

# ============================================================================
#  CATALOGO DE AREAS
# ============================================================================

Write-Paso "Catalogo de areas"

$areas = @(
    @{ N = 'Administracion y Finanzas'; C = 'AFI'; CC = 'CC-1000' }
    @{ N = 'Operaciones';               C = 'OPE'; CC = 'CC-2000' }
    @{ N = 'Comercial';                 C = 'COM'; CC = 'CC-3000' }
    @{ N = 'Recursos Humanos';          C = 'RRH'; CC = 'CC-4000' }
    @{ N = 'Tecnologia de Informacion'; C = 'TIN'; CC = 'CC-5000' }
    @{ N = 'Legal';                     C = 'LEG'; CC = 'CC-6000' }
    @{ N = 'Cadena de Suministro';      C = 'CSU'; CC = 'CC-7000' }
    @{ N = 'Gerencia General';          C = 'GGE'; CC = 'CC-0100' }
)

foreach ($a in $areas) {
    Add-ElementoUnico -Lista 'Areas' -Title $a.N -Valores @{
        CodigoArea = $a.C; CentroCosto = $a.CC; Activo = $true
    }
}

Write-Aviso "Asigna 'Responsable' y 'Gerente' en cada area: de ahi salen los aprobadores"
Write-Aviso "de los roles 'Jefe de area' y 'Gerente de area' de la matriz."

# ============================================================================
#  MATRIZ DE APROBACION  (EJEMPLO - AJUSTAR A LA ORGANIZACION)
# ============================================================================

Write-Paso "Matriz de aprobacion (ejemplo)"

$SIN_TOPE = 999999999

# Tramos de monto en moneda base y los niveles que exige cada uno.
$tramos = @(
    @{
        Etiqueta = '0-20k'; Desde = 0; Hasta = 20000
        Niveles = @(
            @{ N = 1; Rol = 'Jefe de area'; SLA = 48 }
        )
    }
    @{
        Etiqueta = '20k-100k'; Desde = 20000; Hasta = 100000
        Niveles = @(
            @{ N = 1; Rol = 'Jefe de area';    SLA = 48 }
            @{ N = 2; Rol = 'Gerente de area'; SLA = 48 }
            @{ N = 3; Rol = 'Legal';           SLA = 72 }
        )
    }
    @{
        Etiqueta = '100k-500k'; Desde = 100000; Hasta = 500000
        Niveles = @(
            @{ N = 1; Rol = 'Jefe de area';    SLA = 48 }
            @{ N = 2; Rol = 'Gerente de area'; SLA = 48 }
            @{ N = 3; Rol = 'Legal';           SLA = 72 }
            @{ N = 4; Rol = 'Finanzas';        SLA = 48 }
            @{ N = 5; Rol = 'Gerencia General';SLA = 72 }
        )
    }
    @{
        Etiqueta = '500k+'; Desde = 500000; Hasta = $SIN_TOPE
        Niveles = @(
            @{ N = 1; Rol = 'Jefe de area';     SLA = 48 }
            @{ N = 2; Rol = 'Gerente de area';  SLA = 48 }
            @{ N = 3; Rol = 'Legal';            SLA = 72 }
            @{ N = 4; Rol = 'Finanzas';         SLA = 48 }
            @{ N = 5; Rol = 'Gerencia General'; SLA = 72 }
            @{ N = 6; Rol = 'Directorio';       SLA = 120 }
        )
    }
)

foreach ($t in $tramos) {
    foreach ($niv in $t.Niveles) {
        $regla = "Todos $($t.Etiqueta) - N$($niv.N) $($niv.Rol)"
        Add-ElementoUnico -Lista 'MatrizAprobacion' -Title $regla -Valores @{
            TipoContrato  = 'Todos'
            MontoDesdePEN = $t.Desde
            MontoHastaPEN = $t.Hasta
            Nivel         = $niv.N
            RolAprobador  = $niv.Rol
            Obligatorio   = $true
            SLAHoras      = $niv.SLA
            Activo        = $true
        }
    }
}

# --- Reglas especificas por tipo de contrato. Ganan sobre las de 'Todos'.

# Un NDA no tiene monto y solo necesita visto bueno legal.
Add-ElementoUnico -Lista 'MatrizAprobacion' -Title 'NDA - N1 Legal' -Valores @{
    TipoContrato  = 'Confidencialidad (NDA)'
    MontoDesdePEN = 0
    MontoHastaPEN = $SIN_TOPE
    Nivel         = 1
    RolAprobador  = 'Legal'
    Obligatorio   = $true
    SLAHoras      = 48
    Activo        = $true
}

# Los contratos laborales pasan por RRHH (gerente del area) y Gerencia General.
$laboral = @(
    @{ N = 1; Rol = 'Jefe de area';     SLA = 48 }
    @{ N = 2; Rol = 'Gerente de area';  SLA = 48 }
    @{ N = 3; Rol = 'Gerencia General'; SLA = 72 }
)
foreach ($niv in $laboral) {
    Add-ElementoUnico -Lista 'MatrizAprobacion' -Title "Laboral - N$($niv.N) $($niv.Rol)" -Valores @{
        TipoContrato  = 'Laboral'
        MontoDesdePEN = 0
        MontoHastaPEN = $SIN_TOPE
        Nivel         = $niv.N
        RolAprobador  = $niv.Rol
        Obligatorio   = $true
        SLAHoras      = $niv.SLA
        Activo        = $true
    }
}

# Compras y suministro suman el visto bueno de Cadena de Suministro.
foreach ($tipo in @('Suministro de bienes', 'Obra')) {
    Add-ElementoUnico -Lista 'MatrizAprobacion' -Title "$tipo - N2 Compras" -Valores @{
        TipoContrato  = $tipo
        MontoDesdePEN = 20000
        MontoHastaPEN = $SIN_TOPE
        Nivel         = 2
        RolAprobador  = 'Compras'
        Obligatorio   = $true
        SLAHoras      = 48
        Activo        = $true
    }
}

Write-Aviso "Para los roles Legal, Finanzas, Compras, Gerencia General y Directorio"
Write-Aviso "debes completar 'Aprobador (usuario)' o 'Aprobador (grupo)' en cada regla."

# ============================================================================
#  CONTRATOS DE DEMOSTRACION
# ============================================================================

if ($IncluirContratosDemo) {
    Write-Paso "Contratos de demostracion"

    $areaOpe = Get-PnPListItem -List 'Areas' -Query "<View><Query><Where><Eq><FieldRef Name='Title' /><Value Type='Text'>Operaciones</Value></Eq></Where></Query></View>"
    $idArea  = if ($null -ne $areaOpe -and @($areaOpe).Count -gt 0) { @($areaOpe)[0].Id } else { 1 }

    $hoy = Get-Date

    $demos = @(
        @{
            Cod = 'CTR-2026-0001'; Nom = 'Servicio de mantenimiento de planta'
            Tipo = 'Servicios'; Parte = 'Servicios Industriales SAC'; RUC = '20123456789'
            Moneda = 'PEN'; Monto = 85000; Estado = 'Vigente'
            Inicio = $hoy.AddMonths(-8); Fin = $hoy.AddDays(45)
            Custodia = 'En custodia'; Ubic = 'Archivador 01 / Caja 03 / Folio 112'
        }
        @{
            Cod = 'CTR-2026-0002'; Nom = 'Suministro de materia prima 2026'
            Tipo = 'Suministro de bienes'; Parte = 'Insumos del Norte EIRL'; RUC = '20987654321'
            Moneda = 'USD'; Monto = 120000; Estado = 'En aprobacion'
            Inicio = $hoy.AddDays(15); Fin = $hoy.AddMonths(12)
            Custodia = 'Pendiente de recepcion'; Ubic = ''
        }
        @{
            Cod = 'CTR-2026-0003'; Nom = 'Acuerdo de confidencialidad - proyecto Andes'
            Tipo = 'Confidencialidad (NDA)'; Parte = 'Consultora Estrategica SA'; RUC = '20456789123'
            Moneda = 'PEN'; Monto = 0; Estado = 'Vigente'
            Inicio = $hoy.AddMonths(-2); Fin = $hoy.AddMonths(22)
            Custodia = 'Solo digital'; Ubic = ''
        }
        @{
            Cod = 'CTR-2026-0004'; Nom = 'Arrendamiento de almacen zona sur'
            Tipo = 'Arrendamiento'; Parte = 'Inmobiliaria Pacifico SAC'; RUC = '20321654987'
            Moneda = 'PEN'; Monto = 540000; Estado = 'Vigente'
            Inicio = $hoy.AddMonths(-14); Fin = $hoy.AddDays(20)
            Custodia = 'Prestado'; Ubic = 'Archivador 02 / Caja 07 / Folio 034'
        }
        @{
            Cod = 'CTR-2026-0005'; Nom = 'Licencia de software ERP - modulo logistica'
            Tipo = 'Licencia de software'; Parte = 'Tech Solutions Peru SAC'; RUC = '20741852963'
            Moneda = 'USD'; Monto = 45000; Estado = 'Borrador'
            Inicio = $hoy.AddDays(30); Fin = $hoy.AddMonths(36)
            Custodia = 'Pendiente de recepcion'; Ubic = ''
        }
    )

    foreach ($d in $demos) {
        $tc = switch ($d.Moneda) { 'USD' { 3.75 } 'EUR' { 4.05 } default { 1 } }
        Add-ElementoUnico -Lista 'Contratos' -Title $d.Cod -Valores @{
            NombreContrato       = $d.Nom
            TipoContrato         = $d.Tipo
            Contraparte          = $d.Parte
            ContraparteRUC       = $d.RUC
            TipoContraparte      = 'Proveedor'
            AreaSolicitante      = $idArea
            Moneda               = $d.Moneda
            Monto                = $d.Monto
            MontoPEN             = [math]::Round($d.Monto * $tc, 2)
            TipoCambio           = $tc
            FechaInicio          = $d.Inicio
            FechaFin             = $d.Fin
            DiasPreaviso         = 30
            FechaPreaviso        = $d.Fin.AddDays(-30)
            Estado               = $d.Estado
            EstadoCustodia       = $d.Custodia
            UbicacionFisica      = $d.Ubic
            Clasificacion        = 'Interno'
            ObjetoContrato       = "Contrato de demostracion generado por Seed-DemoData.ps1."
        }
    }

    Write-Aviso "Los contratos CTR-2026-0001 y CTR-2026-0004 vencen dentro del preaviso:"
    Write-Aviso "sirven para probar el flujo 04 de alertas de vencimiento."
}

# ============================================================================

Write-Host @"

  ============================================================
   Datos iniciales cargados.

   REVISA ANTES DE PRODUCCION:
     - Parametros : ADMINS, CUSTODIOS y LEGAL estan VACIOS. Sin ellos
       la app oculta las acciones de administracion y custodia.
     - Parametros : correos, tipos de cambio y DOCUSIGN_TEMPLATE_ID
     - Areas      : Responsable y Gerente de cada area
     - MatrizAprobacion : tramos de monto y aprobadores de los
       roles Legal, Finanzas, Compras, Gerencia General y Directorio
  ============================================================
"@ -ForegroundColor White

Disconnect-PnPOnline
