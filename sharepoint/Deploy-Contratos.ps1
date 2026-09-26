<#
.SYNOPSIS
    Aprovisiona el sitio de SharePoint Online del Sistema de Contratos.

.DESCRIPTION
    Crea (opcionalmente) el sitio, y dentro de el las 13 listas y la biblioteca
    documental descritas en docs/02-modelo-datos.md, con todas sus columnas,
    opciones, valores por defecto, indices y vistas.

    El script es IDEMPOTENTE: se puede ejecutar las veces que haga falta. Si una
    lista o columna ya existe, la omite y continua. No borra ni sobrescribe datos.

.PARAMETER SiteUrl
    URL completa del sitio destino.
    Ej: https://contoso.sharepoint.com/sites/Contratos

.PARAMETER CreateSite
    Crea el sitio si no existe (Team Site sin grupo de M365).

.PARAMETER Owner
    UPN del propietario del sitio. Obligatorio si se usa -CreateSite.

.PARAMETER ClientId
    Id de la aplicacion de Entra ID registrada para PnP PowerShell.
    Desde PnP.PowerShell v2 es obligatorio para la conexion interactiva.

.EXAMPLE
    ./Deploy-Contratos.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
                           -CreateSite -Owner "admin@contoso.com" -ClientId "xxxx-xxxx"

.NOTES
    Requiere: PowerShell 7+, modulo PnP.PowerShell 2.x
        Install-Module PnP.PowerShell -Scope CurrentUser
    Permisos: administrador de la coleccion de sitios (o de SharePoint si se crea el sitio).
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $SiteUrl,

    [switch] $CreateSite,

    [string] $Owner,

    [string] $ClientId,

    [ValidateSet('es-ES', 'en-US')]
    [string] $Locale = 'es-ES'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

# ============================================================================
#  UTILIDADES
# ============================================================================

$script:Creados = 0
$script:Omitidos = 0

function Write-Paso   { param([string]$m) Write-Host "`n=== $m" -ForegroundColor Cyan }
function Write-Ok     { param([string]$m) Write-Host "    [+] $m" -ForegroundColor Green;  $script:Creados++ }
function Write-Skip   { param([string]$m) Write-Host "    [=] $m (ya existe)" -ForegroundColor DarkGray; $script:Omitidos++ }
function Write-Info   { param([string]$m) Write-Host "    ... $m" -ForegroundColor Gray }
function Write-Aviso  { param([string]$m) Write-Host "    [!] $m" -ForegroundColor Yellow }

<#
    Crea una lista si no existe. Devuelve el objeto lista.
#>
function New-ListaSiNoExiste {
    param(
        [string] $Title,
        [string] $Url,
        [ValidateSet('GenericList', 'DocumentLibrary')]
        [string] $Template = 'GenericList',
        [string] $Description = '',
        [switch] $EnableVersioning,
        [switch] $EnableMinorVersions,
        [switch] $DisableAttachments
    )

    $lista = Get-PnPList -Identity $Url -ErrorAction SilentlyContinue
    if ($null -ne $lista) {
        Write-Skip "Lista '$Title'"
    }
    else {
        $lista = New-PnPList -Title $Title -Url $Url -Template $Template `
                             -OnQuickLaunch -ErrorAction Stop
        Write-Ok "Lista '$Title'"
    }

    $valores = @{ Description = $Description }
    if ($EnableVersioning)    { $valores['EnableVersioning'] = $true; $valores['MajorVersionLimit'] = 500 }
    if ($EnableMinorVersions) { $valores['EnableMinorVersions'] = $true; $valores['MajorWithMinorVersionsLimit'] = 20 }
    if ($DisableAttachments)  { $valores['EnableAttachments'] = $false }

    Set-PnPList -Identity $lista.Title -Values $valores -ErrorAction SilentlyContinue | Out-Null

    # Se devuelve recargada para tener el Id disponible en los lookups.
    return (Get-PnPList -Identity $Url)
}

<#
    Escapa los caracteres reservados de XML.
#>
function ConvertTo-XmlSafe {
    param([string] $Text)
    return ($Text -replace '&', '&amp;' -replace '<', '&lt;' -replace '>', '&gt;' -replace '"', '&quot;')
}

<#
    Construye el XML de una columna y la agrega a la lista si no existe.

    -Definicion es un hashtable con:
        Name        (obligatorio) nombre interno
        Display     (obligatorio) nombre visible
        Type        Text|Note|Number|Currency|DateTime|Boolean|Choice|User|Lookup|URL
        Required    $true/$false
        Choices     array de opciones (Choice)
        Default     valor por defecto
        MaxLength   (Text)
        Decimals    (Number)
        NumLines    (Note)
        DateOnly    $true => Format="DateOnly"
        LookupList  GUID de la lista destino (Lookup)
        LookupField columna a mostrar (Lookup), por defecto Title
        Indexed     $true => se indexa la columna
        Hidden      $true => columna oculta en formularios
        AddToView   $true => se agrega a la vista predeterminada
#>
function Add-Columna {
    param(
        [Parameter(Mandatory)] $Lista,
        [Parameter(Mandatory)] [hashtable] $Definicion
    )

    $nombre = $Definicion.Name
    $existe = Get-PnPField -List $Lista.Title -Identity $nombre -ErrorAction SilentlyContinue
    if ($null -ne $existe) {
        Write-Skip "    columna $nombre"
        return
    }

    $tipo     = $Definicion.Type
    $display  = ConvertTo-XmlSafe $Definicion.Display
    $required = if ($Definicion.ContainsKey('Required') -and $Definicion.Required) { 'TRUE' } else { 'FALSE' }

    $attrs = "Type=`"$tipo`" DisplayName=`"$display`" Name=`"$nombre`" StaticName=`"$nombre`" Required=`"$required`""

    switch ($tipo) {
        'Text' {
            $max = if ($Definicion.ContainsKey('MaxLength')) { $Definicion.MaxLength } else { 255 }
            $attrs += " MaxLength=`"$max`""
        }
        'Note' {
            $lineas = if ($Definicion.ContainsKey('NumLines')) { $Definicion.NumLines } else { 6 }
            $attrs += " NumLines=`"$lineas`" RichText=`"FALSE`" AppendOnly=`"FALSE`""
        }
        'Number' {
            $dec = if ($Definicion.ContainsKey('Decimals')) { $Definicion.Decimals } else { 2 }
            $attrs += " Decimals=`"$dec`""
            # Solo se acota el minimo cuando la definicion lo pide: MontoDelta admite negativos.
            if ($Definicion.ContainsKey('Min')) { $attrs += " Min=`"$($Definicion.Min)`"" }
        }
        'Currency' {
            $attrs += " Decimals=`"2`" LCID=`"10250`""
        }
        'DateTime' {
            $fmt = if ($Definicion.ContainsKey('DateOnly') -and $Definicion.DateOnly) { 'DateOnly' } else { 'DateTime' }
            $attrs += " Format=`"$fmt`""
        }
        'Boolean' { }
        'Choice' {
            $attrs += " Format=`"Dropdown`" FillInChoice=`"FALSE`""
        }
        'User' {
            $attrs += " UserSelectionMode=`"PeopleOnly`" UserSelectionScope=`"0`" List=`"UserInfo`""
        }
        'Lookup' {
            $campo = if ($Definicion.ContainsKey('LookupField')) { $Definicion.LookupField } else { 'Title' }
            $attrs += " List=`"{$($Definicion.LookupList)}`" ShowField=`"$campo`""
        }
        'URL' {
            $attrs += " Format=`"Hyperlink`""
        }
    }

    if ($Definicion.ContainsKey('Indexed') -and $Definicion.Indexed) { $attrs += " Indexed=`"TRUE`"" }
    if ($Definicion.ContainsKey('Hidden')  -and $Definicion.Hidden)  { $attrs += " Hidden=`"TRUE`"" }

    $interior = ''
    if ($tipo -eq 'Choice' -and $Definicion.ContainsKey('Choices')) {
        $opciones = ($Definicion.Choices | ForEach-Object { "<CHOICE>$(ConvertTo-XmlSafe $_)</CHOICE>" }) -join ''
        $interior += "<CHOICES>$opciones</CHOICES>"
    }
    if ($Definicion.ContainsKey('Default')) {
        $interior += "<Default>$(ConvertTo-XmlSafe ([string]$Definicion.Default))</Default>"
    }

    $xml = if ($interior) { "<Field $attrs>$interior</Field>" } else { "<Field $attrs />" }

    $agregarAVista = $Definicion.ContainsKey('AddToView') -and $Definicion.AddToView

    try {
        if ($agregarAVista) {
            Add-PnPFieldFromXml -List $Lista.Title -FieldXml $xml -ErrorAction Stop | Out-Null
        }
        else {
            Add-PnPFieldFromXml -List $Lista.Title -FieldXml $xml -ErrorAction Stop | Out-Null
            # Add-PnPFieldFromXml agrega a la vista por defecto; se retira si no corresponde.
            $vista = Get-PnPView -List $Lista.Title -Identity 'All Items' -ErrorAction SilentlyContinue
            if ($null -eq $vista) { $vista = Get-PnPView -List $Lista.Title | Where-Object { $_.DefaultView } | Select-Object -First 1 }
            if ($null -ne $vista -and $vista.ViewFields -contains $nombre) {
                $campos = @($vista.ViewFields | Where-Object { $_ -ne $nombre })
                Set-PnPView -List $Lista.Title -Identity $vista.Title -Values @{ ViewFields = $campos } -ErrorAction SilentlyContinue | Out-Null
            }
        }
        Write-Ok "    columna $nombre ($tipo)"
    }
    catch {
        Write-Aviso "    columna $nombre : $($_.Exception.Message)"
    }
}

<#
    Crea una vista si no existe.
#>
function Add-Vista {
    param(
        [Parameter(Mandatory)] $Lista,
        [Parameter(Mandatory)] [string] $Titulo,
        [Parameter(Mandatory)] [string[]] $Campos,
        [string] $Query = '',
        [int] $RowLimit = 100,
        [switch] $Predeterminada
    )

    $existe = Get-PnPView -List $Lista.Title -Identity $Titulo -ErrorAction SilentlyContinue
    if ($null -ne $existe) { Write-Skip "    vista '$Titulo'"; return }

    try {
        Add-PnPView -List $Lista.Title -Title $Titulo -Fields $Campos `
                    -Query $Query -RowLimit $RowLimit `
                    -SetAsDefault:$Predeterminada -ErrorAction Stop | Out-Null
        Write-Ok "    vista '$Titulo'"
    }
    catch {
        Write-Aviso "    vista '$Titulo' : $($_.Exception.Message)"
    }
}

# ============================================================================
#  CONEXION
# ============================================================================

Write-Host @"

  ============================================================
   SISTEMA DE CONTRATOS  ·  Aprovisionamiento de SharePoint
  ============================================================
   Sitio destino : $SiteUrl
   Crear sitio   : $($CreateSite.IsPresent)
  ============================================================
"@ -ForegroundColor White

if ($CreateSite) {
    if ([string]::IsNullOrWhiteSpace($Owner)) {
        throw "El parametro -Owner es obligatorio cuando se usa -CreateSite."
    }

    Write-Paso "Creando el sitio"

    $uri        = [System.Uri]$SiteUrl
    $adminUrl   = "https://$($uri.Host -replace '\.sharepoint\.com$', '-admin.sharepoint.com')"

    Write-Info "Conectando al centro de administracion: $adminUrl"
    if ($ClientId) { Connect-PnPOnline -Url $adminUrl -Interactive -ClientId $ClientId }
    else           { Connect-PnPOnline -Url $adminUrl -Interactive }

    $existente = Get-PnPTenantSite -Identity $SiteUrl -ErrorAction SilentlyContinue
    if ($null -ne $existente) {
        Write-Skip "Sitio $SiteUrl"
    }
    else {
        New-PnPSite -Type TeamSiteWithoutMicrosoft365Group `
                    -Title 'Contratos' `
                    -Url $SiteUrl `
                    -Owner $Owner `
                    -Lcid $(if ($Locale -eq 'es-ES') { 3082 } else { 1033 }) `
                    -ErrorAction Stop | Out-Null
        Write-Ok "Sitio creado: $SiteUrl"
        Write-Info "Esperando 30 s a que el sitio quede disponible..."
        Start-Sleep -Seconds 30
    }
}

Write-Paso "Conectando al sitio"
if ($ClientId) { Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId }
else           { Connect-PnPOnline -Url $SiteUrl -Interactive }

$web = Get-PnPWeb
Write-Info "Conectado a '$($web.Title)'"

# ============================================================================
#  CATALOGOS COMPARTIDOS
# ============================================================================

$TiposContrato = @(
    'Servicios', 'Suministro de bienes', 'Obra', 'Arrendamiento',
    'Confidencialidad (NDA)', 'Licencia de software', 'Distribucion',
    'Agencia / Representacion', 'Laboral', 'Seguros', 'Financiero',
    'Convenio / Adendum marco', 'Otro'
)

$EstadosContrato = @(
    'Borrador', 'En revision legal', 'En aprobacion', 'Aprobado', 'En firma',
    'Vigente', 'Por vencer', 'Vencido', 'Renovado', 'Terminado',
    'Rechazado', 'Anulado'
)

# ============================================================================
#  1. AREAS   (se crea primero: es destino de un lookup)
# ============================================================================

Write-Paso "1/13  Lista 'Areas'"
$lstAreas = New-ListaSiNoExiste -Title 'Areas' -Url 'Lists/Areas' `
    -Description 'Catalogo de areas de la organizacion. Resuelve los roles Jefe y Gerente de area.' `
    -DisableAttachments

@(
    @{ Name = 'CodigoArea';  Display = 'Codigo';          Type = 'Text';    MaxLength = 20; AddToView = $true }
    @{ Name = 'Responsable';    Display = 'Responsable';    Type = 'User'; AddToView = $true }
    @{ Name = 'Gerente';        Display = 'Gerente';        Type = 'User'; AddToView = $true }
    # Los tres roles que varian segun el area del contrato salen de aqui, no de
    # la matriz: la matriz dice "Gerente de area" y el flujo busca el del area
    # que corresponda. Por eso agregar un area nueva no obliga a tocar reglas.
    @{ Name = 'Vicepresidente'; Display = 'Vicepresidente'; Type = 'User'; AddToView = $true }
    @{ Name = 'CentroCosto'; Display = 'Centro de costo'; Type = 'Text';    MaxLength = 50 }
    @{ Name = 'Activo';      Display = 'Activo';          Type = 'Boolean'; Default = 1; AddToView = $true }
) | ForEach-Object { Add-Columna -Lista $lstAreas -Definicion $_ }

# ============================================================================
#  2. PARAMETROS
# ============================================================================

Write-Paso "2/13  Lista 'Parametros'"
$lstParam = New-ListaSiNoExiste -Title 'Parametros' -Url 'Lists/Parametros' `
    -Description 'Configuracion global del sistema. Title = clave.' `
    -DisableAttachments

@(
    @{ Name = 'Valor';       Display = 'Valor';       Type = 'Text'; MaxLength = 255; Required = $true; AddToView = $true }
    @{ Name = 'Descripcion'; Display = 'Descripcion'; Type = 'Note'; NumLines = 3;    AddToView = $true }
    @{ Name = 'Tipo';        Display = 'Tipo';        Type = 'Choice'; Choices = @('Texto','Numero','Fecha','Booleano','Correo'); Default = 'Texto' }
) | ForEach-Object { Add-Columna -Lista $lstParam -Definicion $_ }

# ============================================================================
#  3. CATEGORIAS   (carpetas administrables, esquema configurable)
# ============================================================================

Write-Paso "3/13  Lista 'Categorias'"
$lstCategorias = New-ListaSiNoExiste -Title 'Categorias' -Url 'Lists/Categorias' `
    -Description 'Carpetas administrables (Logistica, Comercial, RRHH, Legal...). Determinan que campos y clausulas se piden en cada contrato.' `
    -DisableAttachments

@(
    @{ Name = 'CategoriaPadre';      Display = 'Categoria padre';      Type = 'Lookup'; LookupList = $null; LookupField = 'Title' }
    @{ Name = 'Icono';               Display = 'Icono';                Type = 'Text'; MaxLength = 60 }
    @{ Name = 'Color';               Display = 'Color';                Type = 'Text'; MaxLength = 10 }
    @{ Name = 'ResponsableAdicional';Display = 'Responsable adicional';Type = 'User' }
    @{ Name = 'Orden';               Display = 'Orden';                Type = 'Number'; Decimals = 0; Default = 0; AddToView = $true }
    @{ Name = 'Activo';              Display = 'Activo';               Type = 'Boolean'; Default = 1; AddToView = $true }
) | ForEach-Object {
    # CategoriaPadre es un lookup de la lista sobre si misma: recien existe su Id
    # despues de New-ListaSiNoExiste, asi que se resuelve aqui en vez de en la
    # definicion literal de arriba.
    if ($_.Name -eq 'CategoriaPadre') { $_.LookupList = $lstCategorias.Id }
    Add-Columna -Lista $lstCategorias -Definicion $_
}

# ============================================================================
#  4. CAMPOS PERSONALIZADOS   (esquema por categoria)
# ============================================================================

Write-Paso "4/13  Lista 'CamposPersonalizados'"
$lstCampos = New-ListaSiNoExiste -Title 'CamposPersonalizados' -Url 'Lists/CamposPersonalizados' `
    -Description 'Define los campos adicionales y clausulas de cada categoria. Editar esta lista equivale a agregar una columna, sin tocar SharePoint.' `
    -DisableAttachments

Set-PnPField -List 'CamposPersonalizados' -Identity 'Title' -Values @{ Title = 'Nombre tecnico' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Categoria';   Display = 'Categoria';    Type = 'Lookup'; LookupList = $lstCategorias.Id; LookupField = 'Title'; Indexed = $true; AddToView = $true }
    @{ Name = 'Etiqueta';    Display = 'Etiqueta';     Type = 'Text'; MaxLength = 150; Required = $true; AddToView = $true }
    @{ Name = 'TipoDato';    Display = 'Tipo de dato'; Type = 'Choice'; Choices = @('Texto','Numero','Fecha','Booleano','Opcion'); Required = $true; AddToView = $true }
    @{ Name = 'Opciones';    Display = 'Opciones';     Type = 'Text'; MaxLength = 255 }
    @{ Name = 'Seccion';     Display = 'Seccion';      Type = 'Text'; MaxLength = 100; AddToView = $true }
    @{ Name = 'Obligatorio'; Display = 'Obligatorio';  Type = 'Boolean'; Default = 0 }
    @{ Name = 'Orden';       Display = 'Orden';        Type = 'Number'; Decimals = 0; Default = 0 }
    @{ Name = 'Ayuda';       Display = 'Ayuda';        Type = 'Text'; MaxLength = 255 }
    @{ Name = 'Activo';      Display = 'Activo';       Type = 'Boolean'; Default = 1; AddToView = $true }
) | ForEach-Object { Add-Columna -Lista $lstCampos -Definicion $_ }

# ============================================================================
#  5. CONTRATOS   (maestro)
# ============================================================================

Write-Paso "5/13  Lista 'Contratos'"
$lstContratos = New-ListaSiNoExiste -Title 'Contratos' -Url 'Lists/Contratos' `
    -Description 'Maestro de contratos. Una fila = un contrato.' `
    -EnableVersioning

Set-PnPField -List 'Contratos' -Identity 'Title' -Values @{ Title = 'Codigo'; Required = $false } -ErrorAction SilentlyContinue | Out-Null

@(
    # --- Identificacion
    @{ Name = 'NombreContrato';  Display = 'Nombre del contrato'; Type = 'Text'; MaxLength = 255; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'TipoContrato';    Display = 'Tipo de contrato';    Type = 'Choice'; Choices = $TiposContrato; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'ObjetoContrato';  Display = 'Objeto del contrato'; Type = 'Note'; NumLines = 6 }
    @{ Name = 'ContratoPadre';   Display = 'Contrato relacionado'; Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title' }
    @{ Name = 'Categoria';       Display = 'Categoria';            Type = 'Lookup'; LookupList = $lstCategorias.Id; LookupField = 'Title'; Indexed = $true; AddToView = $true }

    # --- Contraparte
    @{ Name = 'Contraparte';         Display = 'Contraparte';           Type = 'Text'; MaxLength = 255; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'ContraparteRUC';      Display = 'RUC / Doc. identidad';  Type = 'Text'; MaxLength = 20 }
    @{ Name = 'TipoContraparte';     Display = 'Tipo de contraparte';   Type = 'Choice'; Choices = @('Proveedor','Cliente','Empleado','Socio comercial','Entidad publica','Otro'); Default = 'Proveedor' }
    @{ Name = 'ContraparteContacto'; Display = 'Contacto (firmante)';   Type = 'Text'; MaxLength = 150 }
    @{ Name = 'ContraparteCorreo';   Display = 'Correo del firmante';   Type = 'Text'; MaxLength = 150 }

    # --- Organizacion
    @{ Name = 'AreaSolicitante';     Display = 'Area solicitante';         Type = 'Lookup'; LookupList = $lstAreas.Id; Required = $true; AddToView = $true }
    @{ Name = 'Solicitante';         Display = 'Solicitante';              Type = 'User' }
    @{ Name = 'ResponsableContrato'; Display = 'Responsable del contrato'; Type = 'User'; AddToView = $true }

    # --- Economicos
    @{ Name = 'Moneda';               Display = 'Moneda';             Type = 'Choice'; Choices = @('PEN','USD','EUR'); Default = 'PEN'; AddToView = $true }
    @{ Name = 'Monto';                Display = 'Monto';              Type = 'Number'; Decimals = 2; AddToView = $true }
    @{ Name = 'MontoPEN';             Display = 'Monto en PEN';       Type = 'Number'; Decimals = 2 }
    @{ Name = 'TipoCambio';           Display = 'Tipo de cambio';     Type = 'Number'; Decimals = 4 }
    @{ Name = 'SinMontoDeterminado';  Display = 'Monto no determinado'; Type = 'Boolean'; Default = 0 }

    # --- Vigencia
    @{ Name = 'FechaInicio';         Display = 'Fecha de inicio';      Type = 'DateTime'; DateOnly = $true; Required = $true; AddToView = $true }
    @{ Name = 'FechaFin';            Display = 'Fecha de fin';         Type = 'DateTime'; DateOnly = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'VigenciaIndefinida';  Display = 'Vigencia indefinida';  Type = 'Boolean'; Default = 0 }
    @{ Name = 'RenovacionAutomatica';Display = 'Renovacion automatica';Type = 'Boolean'; Default = 0 }
    @{ Name = 'DiasPreaviso';        Display = 'Dias de preaviso';     Type = 'Number'; Decimals = 0; Default = 30 }
    @{ Name = 'FechaPreaviso';       Display = 'Fecha de preaviso';    Type = 'DateTime'; DateOnly = $true; Indexed = $true }

    # --- Estado y aprobacion
    @{ Name = 'Estado';                   Display = 'Estado';                   Type = 'Choice'; Choices = $EstadosContrato; Default = 'Borrador'; Indexed = $true; AddToView = $true }
    @{ Name = 'NivelAprobacionRequerido'; Display = 'Nivel requerido';          Type = 'Number'; Decimals = 0; Default = 0 }
    @{ Name = 'NivelAprobacionActual';    Display = 'Nivel actual';             Type = 'Number'; Decimals = 0; Default = 0 }
    @{ Name = 'CicloAprobacion';          Display = 'Ciclo de aprobacion';      Type = 'Number'; Decimals = 0; Default = 0 }
    @{ Name = 'FechaEnvioAprobacion';     Display = 'Enviado a aprobacion';     Type = 'DateTime' }
    @{ Name = 'FechaAprobacionFinal';     Display = 'Aprobacion final';         Type = 'DateTime' }
    @{ Name = 'MotivoRechazo';            Display = 'Motivo de rechazo';        Type = 'Note'; NumLines = 4 }

    # --- Firma electronica
    @{ Name = 'DocuSignEnvelopeId'; Display = 'Sobre DocuSign';  Type = 'Text'; MaxLength = 100 }
    @{ Name = 'DocuSignEstado';     Display = 'Estado DocuSign'; Type = 'Choice'; Choices = @('No enviado','Enviado','Entregado','Firmado','Completado','Rechazado','Anulado'); Default = 'No enviado' }
    @{ Name = 'FechaFirma';         Display = 'Fecha de firma';  Type = 'DateTime' }

    # --- Custodia
    @{ Name = 'EstadoCustodia';        Display = 'Estado de custodia';   Type = 'Choice'; Choices = @('Pendiente de recepcion','En custodia','Prestado','Solo digital','Dado de baja'); Default = 'Pendiente de recepcion'; Indexed = $true; AddToView = $true }
    @{ Name = 'Custodio';              Display = 'Custodio';             Type = 'User' }
    @{ Name = 'UbicacionFisica';       Display = 'Ubicacion fisica';     Type = 'Text'; MaxLength = 150 }
    @{ Name = 'FechaRecepcionOriginal';Display = 'Recepcion del original';Type = 'DateTime'; DateOnly = $true }

    # --- Riesgo y cumplimiento
    @{ Name = 'Clasificacion';       Display = 'Clasificacion';          Type = 'Choice'; Choices = @('Publico','Interno','Confidencial','Restringido'); Default = 'Interno' }
    @{ Name = 'ObligacionesClave';   Display = 'Obligaciones clave';     Type = 'Note'; NumLines = 6 }
    @{ Name = 'Penalidades';         Display = 'Penalidades';            Type = 'Note'; NumLines = 4 }
    @{ Name = 'TieneGarantia';       Display = 'Tiene garantia';         Type = 'Boolean'; Default = 0 }
    @{ Name = 'TipoGarantia';        Display = 'Tipo de garantia';       Type = 'Choice'; Choices = @('Carta fianza','Retencion','Deposito en garantia','Poliza de caucion','Otra') }
    @{ Name = 'MontoGarantia';       Display = 'Monto de garantia';      Type = 'Number'; Decimals = 2 }
    @{ Name = 'VencimientoGarantia'; Display = 'Vencimiento de garantia';Type = 'DateTime'; DateOnly = $true }
    @{ Name = 'Notas';               Display = 'Notas';                  Type = 'Note'; NumLines = 6 }
) | ForEach-Object { Add-Columna -Lista $lstContratos -Definicion $_ }

Add-Vista -Lista $lstContratos -Titulo 'Vigentes' `
    -Campos @('Title','NombreContrato','Contraparte','TipoContrato','Moneda','Monto','FechaFin','ResponsableContrato') `
    -Query '<Where><Eq><FieldRef Name="Estado" /><Value Type="Choice">Vigente</Value></Eq></Where><OrderBy><FieldRef Name="FechaFin" Ascending="TRUE" /></OrderBy>'

Add-Vista -Lista $lstContratos -Titulo 'En aprobacion' `
    -Campos @('Title','NombreContrato','Contraparte','MontoPEN','NivelAprobacionActual','NivelAprobacionRequerido','FechaEnvioAprobacion') `
    -Query '<Where><Eq><FieldRef Name="Estado" /><Value Type="Choice">En aprobacion</Value></Eq></Where><OrderBy><FieldRef Name="FechaEnvioAprobacion" Ascending="TRUE" /></OrderBy>'

Add-Vista -Lista $lstContratos -Titulo 'Por vencer' `
    -Campos @('Title','NombreContrato','Contraparte','FechaFin','DiasPreaviso','RenovacionAutomatica','ResponsableContrato') `
    -Query '<Where><And><Neq><FieldRef Name="VigenciaIndefinida" /><Value Type="Boolean">1</Value></Neq><Leq><FieldRef Name="FechaPreaviso" /><Value Type="DateTime"><Today /></Value></Leq></And></Where><OrderBy><FieldRef Name="FechaFin" Ascending="TRUE" /></OrderBy>'

Add-Vista -Lista $lstContratos -Titulo 'Custodia fisica' `
    -Campos @('Title','NombreContrato','EstadoCustodia','Custodio','UbicacionFisica','FechaRecepcionOriginal') `
    -Query '<Where><Neq><FieldRef Name="EstadoCustodia" /><Value Type="Choice">Solo digital</Value></Neq></Where>'

# ============================================================================
#  6. BIBLIOTECA DocumentosContratos
# ============================================================================

Write-Paso "6/13  Biblioteca 'DocumentosContratos'"
$lstDocs = New-ListaSiNoExiste -Title 'DocumentosContratos' -Url 'DocumentosContratos' `
    -Template DocumentLibrary `
    -Description 'Custodia digital. Todos los documentos del expediente de cada contrato.' `
    -EnableVersioning -EnableMinorVersions

@(
    @{ Name = 'Contrato';        Display = 'Contrato';          Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'TipoDocumento';   Display = 'Tipo de documento'; Type = 'Choice'; Choices = @('Contrato original','Adenda','Anexo','Cotizacion','Orden de compra','Carta fianza','Acta de recepcion','Sustento de aprobacion','Sobre firmado','Otro'); Default = 'Contrato original'; Required = $true; AddToView = $true }
    @{ Name = 'VersionDocumento';Display = 'Version del documento'; Type = 'Text'; MaxLength = 30 }
    @{ Name = 'FechaDocumento';  Display = 'Fecha del documento';  Type = 'DateTime'; DateOnly = $true; AddToView = $true }
    @{ Name = 'EsPrincipal';     Display = 'Es documento principal'; Type = 'Boolean'; Default = 0; AddToView = $true }
    @{ Name = 'EstaFirmado';     Display = 'Esta firmado';          Type = 'Boolean'; Default = 0 }
    @{ Name = 'EsConfidencial';  Display = 'Confidencial';          Type = 'Boolean'; Default = 0 }
) | ForEach-Object { Add-Columna -Lista $lstDocs -Definicion $_ }

# ============================================================================
#  7. MATRIZ DE APROBACION
# ============================================================================

Write-Paso "7/13  Lista 'MatrizAprobacion'"
$lstMatriz = New-ListaSiNoExiste -Title 'MatrizAprobacion' -Url 'Lists/MatrizAprobacion' `
    -Description 'Reglas del workflow. Cambiar quien aprueba NO requiere modificar el flujo.' `
    -EnableVersioning -DisableAttachments

Set-PnPField -List 'MatrizAprobacion' -Identity 'Title' -Values @{ Title = 'Regla' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'TipoContrato';     Display = 'Tipo de contrato'; Type = 'Choice'; Choices = (@('Todos') + $TiposContrato); Default = 'Todos'; Required = $true; AddToView = $true }
    @{ Name = 'MontoDesdePEN';    Display = 'Monto desde (PEN)';Type = 'Number'; Decimals = 2; Default = 0; Required = $true; AddToView = $true }
    @{ Name = 'MontoHastaPEN';    Display = 'Monto hasta (PEN)';Type = 'Number'; Decimals = 2; Required = $true; AddToView = $true }
    @{ Name = 'Nivel';            Display = 'Nivel';            Type = 'Number'; Decimals = 0; Required = $true; AddToView = $true }
    @{ Name = 'RolAprobador';     Display = 'Rol del aprobador';Type = 'Choice'; Choices = @('Jefe de area','Gerente de area','Vicepresidencia de area','Legal','Finanzas','Compras','Gerencia General','Directorio','Usuario especifico'); Required = $true; AddToView = $true }
    @{ Name = 'AprobadorUsuario'; Display = 'Aprobador (usuario)'; Type = 'User'; AddToView = $true }
    @{ Name = 'AprobadorGrupo';   Display = 'Aprobador (grupo)';   Type = 'Text'; MaxLength = 255 }
    @{ Name = 'Obligatorio';      Display = 'Obligatorio';         Type = 'Boolean'; Default = 1 }
    @{ Name = 'SLAHoras';         Display = 'SLA (horas)';         Type = 'Number'; Decimals = 0; Default = 48 }
    @{ Name = 'Activo';           Display = 'Activo';              Type = 'Boolean'; Default = 1; AddToView = $true }
) | ForEach-Object { Add-Columna -Lista $lstMatriz -Definicion $_ }

# ============================================================================
#  8. APROBACIONES (historial)
# ============================================================================

Write-Paso "8/13  Lista 'Aprobaciones'"
$lstAprob = New-ListaSiNoExiste -Title 'Aprobaciones' -Url 'Lists/Aprobaciones' `
    -Description 'Historial inmutable de decisiones de aprobacion. Evidencia de auditoria.' `
    -DisableAttachments

Set-PnPField -List 'Aprobaciones' -Identity 'Title' -Values @{ Title = 'Referencia' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato';          Display = 'Contrato';            Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'Nivel';             Display = 'Nivel';               Type = 'Number'; Decimals = 0; AddToView = $true }
    @{ Name = 'Ciclo';             Display = 'Ciclo';               Type = 'Number'; Decimals = 0; Default = 1 }
    @{ Name = 'RolAprobador';      Display = 'Rol del aprobador';   Type = 'Text'; MaxLength = 100; AddToView = $true }
    @{ Name = 'AprobadorAsignado'; Display = 'Aprobador asignado';  Type = 'User'; AddToView = $true }
    @{ Name = 'ResueltoPor';       Display = 'Resuelto por';        Type = 'User' }
    @{ Name = 'Decision';          Display = 'Decision';            Type = 'Choice'; Choices = @('Pendiente','Aprobado','Rechazado','Devuelto','Delegado','Omitido','Vencido'); Default = 'Pendiente'; Indexed = $true; AddToView = $true }
    @{ Name = 'Comentarios';       Display = 'Comentarios';         Type = 'Note'; NumLines = 4; AddToView = $true }
    @{ Name = 'FechaSolicitud';    Display = 'Fecha de solicitud';  Type = 'DateTime' }
    @{ Name = 'FechaDecision';     Display = 'Fecha de decision';   Type = 'DateTime'; AddToView = $true }
    @{ Name = 'HorasTranscurridas';Display = 'Horas transcurridas'; Type = 'Number'; Decimals = 1 }
    @{ Name = 'InstanciaFlujo';    Display = 'Instancia del flujo'; Type = 'Text'; MaxLength = 100 }
) | ForEach-Object { Add-Columna -Lista $lstAprob -Definicion $_ }

Add-Vista -Lista $lstAprob -Titulo 'Pendientes' `
    -Campos @('Title','Contrato','Nivel','RolAprobador','AprobadorAsignado','FechaSolicitud') `
    -Query '<Where><Eq><FieldRef Name="Decision" /><Value Type="Choice">Pendiente</Value></Eq></Where><OrderBy><FieldRef Name="FechaSolicitud" Ascending="TRUE" /></OrderBy>'

# ============================================================================
#  9. ADENDAS
# ============================================================================

Write-Paso "9/13  Lista 'Adendas'"
$lstAdendas = New-ListaSiNoExiste -Title 'Adendas' -Url 'Lists/Adendas' `
    -Description 'Modificaciones contractuales. Reevaluan la matriz sobre el monto acumulado.' `
    -EnableVersioning

Set-PnPField -List 'Adendas' -Identity 'Title' -Values @{ Title = 'Codigo' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato';      Display = 'Contrato';            Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'NumeroAdenda';  Display = 'Numero de adenda';    Type = 'Number'; Decimals = 0; AddToView = $true }
    @{ Name = 'TipoAdenda';    Display = 'Tipo de adenda';      Type = 'Choice'; Choices = @('Prorroga de plazo','Ampliacion de monto','Reduccion de monto','Cambio de alcance','Cesion de posicion','Resolucion anticipada','Otro'); Required = $true; AddToView = $true }
    @{ Name = 'FechaAdenda';   Display = 'Fecha de la adenda';  Type = 'DateTime'; DateOnly = $true; AddToView = $true }
    @{ Name = 'MontoDelta';    Display = 'Variacion de monto';  Type = 'Number'; Decimals = 2; AddToView = $true }
    @{ Name = 'NuevaFechaFin'; Display = 'Nueva fecha de fin';  Type = 'DateTime'; DateOnly = $true; AddToView = $true }
    @{ Name = 'Descripcion';   Display = 'Descripcion';         Type = 'Note'; NumLines = 6 }
    @{ Name = 'Estado';        Display = 'Estado';              Type = 'Choice'; Choices = @('Borrador','En aprobacion','Aprobada','Rechazada'); Default = 'Borrador'; AddToView = $true }
) | ForEach-Object { Add-Columna -Lista $lstAdendas -Definicion $_ }

# ============================================================================
#  10. MOVIMIENTOS DE CUSTODIA
# ============================================================================

Write-Paso "10/13 Lista 'MovimientosCustodia'"
$lstCustodia = New-ListaSiNoExiste -Title 'MovimientosCustodia' -Url 'Lists/MovimientosCustodia' `
    -Description 'Cadena de custodia del documento original: recepcion, prestamos, devoluciones y bajas.'

Set-PnPField -List 'MovimientosCustodia' -Identity 'Title' -Values @{ Title = 'Referencia' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato';                  Display = 'Contrato';                 Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'TipoMovimiento';            Display = 'Tipo de movimiento';       Type = 'Choice'; Choices = @('Recepcion de original','Prestamo','Devolucion','Traslado','Digitalizacion','Baja / Destruccion'); Required = $true; AddToView = $true }
    @{ Name = 'FechaMovimiento';           Display = 'Fecha del movimiento';     Type = 'DateTime'; Required = $true; AddToView = $true }
    @{ Name = 'SolicitadoPor';             Display = 'Solicitado por';           Type = 'User'; AddToView = $true }
    @{ Name = 'EntregadoPor';              Display = 'Entregado por';            Type = 'User' }
    @{ Name = 'UbicacionOrigen';           Display = 'Ubicacion origen';         Type = 'Text'; MaxLength = 150 }
    @{ Name = 'UbicacionDestino';          Display = 'Ubicacion destino';        Type = 'Text'; MaxLength = 150 }
    @{ Name = 'FechaCompromisoDevolucion'; Display = 'Compromiso de devolucion'; Type = 'DateTime'; DateOnly = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'FechaDevolucionReal';       Display = 'Devolucion real';          Type = 'DateTime'; DateOnly = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'ActaFirmada';               Display = 'Acta firmada';             Type = 'Boolean'; Default = 0 }
    @{ Name = 'Observaciones';             Display = 'Observaciones';            Type = 'Note'; NumLines = 4 }
) | ForEach-Object { Add-Columna -Lista $lstCustodia -Definicion $_ }

Add-Vista -Lista $lstCustodia -Titulo 'Prestamos abiertos' `
    -Campos @('Title','Contrato','SolicitadoPor','FechaMovimiento','FechaCompromisoDevolucion') `
    -Query '<Where><And><Eq><FieldRef Name="TipoMovimiento" /><Value Type="Choice">Prestamo</Value></Eq><IsNull><FieldRef Name="FechaDevolucionReal" /></IsNull></And></Where><OrderBy><FieldRef Name="FechaCompromisoDevolucion" Ascending="TRUE" /></OrderBy>'

# ============================================================================
#  11. ALERTAS
# ============================================================================

Write-Paso "11/13 Lista 'Alertas'"
$lstAlertas = New-ListaSiNoExiste -Title 'Alertas' -Url 'Lists/Alertas' `
    -Description 'Bitacora de notificaciones enviadas. Evita duplicados.' `
    -DisableAttachments

Set-PnPField -List 'Alertas' -Identity 'Title' -Values @{ Title = 'Referencia' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato';          Display = 'Contrato';             Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Indexed = $true; AddToView = $true }
    @{ Name = 'TipoAlerta';        Display = 'Tipo de alerta';       Type = 'Choice'; Choices = @('Preaviso de vencimiento','Vencimiento','Renovacion automatica','Vencimiento de garantia','Prestamo vencido','Aprobacion pendiente','SLA vencido'); Required = $true; AddToView = $true }
    @{ Name = 'DiasAnticipacion';  Display = 'Dias de anticipacion'; Type = 'Number'; Decimals = 0; AddToView = $true }
    @{ Name = 'FechaEnvio';        Display = 'Fecha de envio';       Type = 'DateTime'; AddToView = $true }
    @{ Name = 'Destinatarios';     Display = 'Destinatarios';        Type = 'Text'; MaxLength = 255 }
    @{ Name = 'Canal';             Display = 'Canal';                Type = 'Choice'; Choices = @('Correo','Teams','Ambos'); Default = 'Correo' }
) | ForEach-Object { Add-Columna -Lista $lstAlertas -Definicion $_ }

# ============================================================================
#  12. BITACORA
# ============================================================================

Write-Paso "12/13 Lista 'Bitacora'"
$lstBitacora = New-ListaSiNoExiste -Title 'Bitacora' -Url 'Lists/Bitacora' `
    -Description 'Auditoria funcional de las acciones realizadas desde la aplicacion.' `
    -DisableAttachments

Set-PnPField -List 'Bitacora' -Identity 'Title' -Values @{ Title = 'Referencia' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato'; Display = 'Contrato'; Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Indexed = $true; AddToView = $true }
    @{ Name = 'Accion';   Display = 'Accion';   Type = 'Text'; MaxLength = 100; AddToView = $true }
    @{ Name = 'Usuario';  Display = 'Usuario';  Type = 'User'; AddToView = $true }
    @{ Name = 'Fecha';    Display = 'Fecha';    Type = 'DateTime'; AddToView = $true }
    @{ Name = 'Detalle';  Display = 'Detalle';  Type = 'Note'; NumLines = 4 }
) | ForEach-Object { Add-Columna -Lista $lstBitacora -Definicion $_ }

# ============================================================================
#  13. CONTRATOS CAMPOS VALOR   (EAV: valores del esquema dinamico)
# ============================================================================

Write-Paso "13/13 Lista 'ContratosCamposValor'"
$lstCamposValor = New-ListaSiNoExiste -Title 'ContratosCamposValor' -Url 'Lists/ContratosCamposValor' `
    -Description 'Valor de cada campo personalizado, uno por fila (patron EAV). Es como se guardan los campos y clausulas que el administrador agrega desde CamposPersonalizados.' `
    -DisableAttachments

Set-PnPField -List 'ContratosCamposValor' -Identity 'Title' -Values @{ Title = 'Referencia' } -ErrorAction SilentlyContinue | Out-Null

@(
    @{ Name = 'Contrato';      Display = 'Contrato';      Type = 'Lookup'; LookupList = $lstContratos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'Campo';         Display = 'Campo';         Type = 'Lookup'; LookupList = $lstCampos.Id; LookupField = 'Title'; Required = $true; Indexed = $true; AddToView = $true }
    @{ Name = 'ValorTexto';    Display = 'Valor texto';   Type = 'Text'; MaxLength = 255 }
    @{ Name = 'ValorNumero';   Display = 'Valor numero';  Type = 'Number'; Decimals = 4; Min = -999999999 }
    @{ Name = 'ValorFecha';    Display = 'Valor fecha';   Type = 'DateTime'; DateOnly = $true }
    @{ Name = 'ValorBooleano'; Display = 'Valor booleano';Type = 'Boolean' }
) | ForEach-Object { Add-Columna -Lista $lstCamposValor -Definicion $_ }

# ============================================================================
#  CIERRE
# ============================================================================

Write-Paso "Resumen"
Write-Host "    Elementos creados : $script:Creados"  -ForegroundColor Green
Write-Host "    Ya existentes     : $script:Omitidos" -ForegroundColor DarkGray

Write-Host @"

  ============================================================
   Aprovisionamiento terminado.

   Siguientes pasos:
     1) ./Set-Permissions.ps1 -SiteUrl "$SiteUrl"
     2) ./Seed-DemoData.ps1   -SiteUrl "$SiteUrl"
     3) Importar los flujos de ../power-automate/
     4) Abrir la app de ../canvas-app/ y reconectar los origenes

   Documentacion: ../docs/03-despliegue.md
  ============================================================
"@ -ForegroundColor White

Disconnect-PnPOnline
