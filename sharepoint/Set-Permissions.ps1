<#
.SYNOPSIS
    Configura los grupos de seguridad y los permisos del sitio de Contratos.

.DESCRIPTION
    Crea seis grupos de SharePoint con niveles de permiso ajustados al rol de cada
    uno, rompe la herencia en las listas de configuracion y en el historial de
    aprobaciones, y crea dos niveles de permiso personalizados:

      - "Aportar sin eliminar"  : agregar y editar, pero NO borrar. Se aplica a
                                  Contratos y a la biblioteca documental, para que
                                  nadie pueda destruir un expediente.
      - "Solo agregar"          : crear elementos nuevos y leer, sin editar ni
                                  borrar los existentes. Se aplica al historial de
                                  Aprobaciones y a la Bitacora, que deben ser
                                  inmutables para servir como evidencia.

    El script es idempotente.

.PARAMETER SiteUrl
    URL del sitio de Contratos.

.PARAMETER ClientId
    Id de la aplicacion de Entra ID para PnP PowerShell.

.EXAMPLE
    ./Set-Permissions.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SiteUrl,
    [string] $ClientId
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Write-Paso { param([string]$m) Write-Host "`n=== $m" -ForegroundColor Cyan }
function Write-Ok   { param([string]$m) Write-Host "    [+] $m" -ForegroundColor Green }
function Write-Skip { param([string]$m) Write-Host "    [=] $m (ya existe)" -ForegroundColor DarkGray }
function Write-Aviso{ param([string]$m) Write-Host "    [!] $m" -ForegroundColor Yellow }

# ----------------------------------------------------------------------------

Write-Paso "Conectando a $SiteUrl"
if ($ClientId) { Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId }
else           { Connect-PnPOnline -Url $SiteUrl -Interactive }

# ============================================================================
#  NIVELES DE PERMISO PERSONALIZADOS
# ============================================================================

Write-Paso "Niveles de permiso personalizados"

function Add-NivelPermiso {
    param(
        [string]   $Nombre,
        [string]   $Descripcion,
        [string]   $BasadoEn,
        [string[]] $Excluir
    )
    $existe = Get-PnPRoleDefinition -Identity $Nombre -ErrorAction SilentlyContinue
    if ($null -ne $existe) { Write-Skip "Nivel '$Nombre'"; return }

    try {
        Add-PnPRoleDefinition -RoleName $Nombre `
                              -Description $Descripcion `
                              -Clone $BasadoEn `
                              -Exclude $Excluir `
                              -ErrorAction Stop | Out-Null
        Write-Ok "Nivel '$Nombre'"
    }
    catch {
        Write-Aviso "Nivel '$Nombre': $($_.Exception.Message)"
    }
}

# Aportar sin eliminar: Contribute menos los permisos de borrado.
Add-NivelPermiso -Nombre 'Aportar sin eliminar' `
    -Descripcion 'Puede agregar y editar elementos y documentos, pero no eliminarlos.' `
    -BasadoEn 'Contribute' `
    -Excluir @('DeleteListItems', 'DeleteVersions')

# Solo agregar: crear y leer, sin editar ni borrar. Para historiales inmutables.
Add-NivelPermiso -Nombre 'Solo agregar' `
    -Descripcion 'Puede crear elementos nuevos y leerlos, pero no modificarlos ni eliminarlos.' `
    -BasadoEn 'Contribute' `
    -Excluir @('EditListItems', 'DeleteListItems', 'DeleteVersions')

# ============================================================================
#  GRUPOS
# ============================================================================

Write-Paso "Grupos de SharePoint"

$Grupos = @(
    @{ Nombre = 'Contratos - Administradores'; Desc = 'Administra el sistema: matriz de aprobacion, parametros, catalogos y correccion de datos.' }
    @{ Nombre = 'Contratos - Legal';           Desc = 'Revisa y da visto bueno legal a los contratos antes de la aprobacion.' }
    @{ Nombre = 'Contratos - Aprobadores';     Desc = 'Resuelve las tareas de aprobacion asignadas por el workflow.' }
    @{ Nombre = 'Contratos - Custodios';       Desc = 'Gestiona el archivo fisico: recepcion, prestamos, devoluciones y bajas.' }
    @{ Nombre = 'Contratos - Solicitantes';    Desc = 'Registra contratos y da seguimiento a los de su area.' }
    @{ Nombre = 'Contratos - Consulta';        Desc = 'Acceso de solo lectura al maestro de contratos.' }
)

foreach ($g in $Grupos) {
    $existe = Get-PnPGroup -Identity $g.Nombre -ErrorAction SilentlyContinue
    if ($null -ne $existe) { Write-Skip "Grupo '$($g.Nombre)'"; continue }

    New-PnPGroup -Title $g.Nombre -Description $g.Desc `
                 -AllowMembersEditMembership:$false `
                 -AllowRequestToJoinLeave:$false `
                 -ErrorAction Stop | Out-Null
    Write-Ok "Grupo '$($g.Nombre)'"
}

# Nadie recibe permisos a nivel de sitio salvo administradores y consulta.
Write-Paso "Permisos a nivel de sitio"

function Set-PermisoSitio {
    param([string] $Grupo, [string] $Nivel)
    try {
        Set-PnPGroupPermissions -Identity $Grupo -AddRole $Nivel -ErrorAction Stop
        Write-Ok "$Grupo -> $Nivel (sitio)"
    }
    catch { Write-Aviso "$Grupo -> $Nivel : $($_.Exception.Message)" }
}

Set-PermisoSitio -Grupo 'Contratos - Administradores' -Nivel 'Full Control'
Set-PermisoSitio -Grupo 'Contratos - Legal'           -Nivel 'Read'
Set-PermisoSitio -Grupo 'Contratos - Aprobadores'     -Nivel 'Read'
Set-PermisoSitio -Grupo 'Contratos - Custodios'       -Nivel 'Read'
Set-PermisoSitio -Grupo 'Contratos - Solicitantes'    -Nivel 'Read'
Set-PermisoSitio -Grupo 'Contratos - Consulta'        -Nivel 'Read'

# ============================================================================
#  PERMISOS POR LISTA
# ============================================================================

Write-Paso "Permisos por lista"

<#
    Rompe la herencia de una lista y aplica el mapa de permisos indicado.
    $Permisos es un hashtable  @{ 'Grupo' = 'Nivel' }.
#>
function Set-PermisosLista {
    param(
        [string]    $Lista,
        [hashtable] $Permisos,
        [switch]    $CopiarHerencia
    )

    Write-Host "  -- $Lista" -ForegroundColor White

    try {
        Set-PnPList -Identity $Lista -BreakRoleInheritance -CopyRoleAssignments:$CopiarHerencia -ErrorAction Stop
    }
    catch {
        # Si ya estaba rota la herencia, SharePoint lanza error: se ignora.
        Write-Host "     (herencia ya rota)" -ForegroundColor DarkGray
    }

    foreach ($grupo in $Permisos.Keys) {
        try {
            Set-PnPListPermission -Identity $Lista -Group $grupo -AddRole $Permisos[$grupo] -ErrorAction Stop
            Write-Ok "$grupo -> $($Permisos[$grupo])"
        }
        catch { Write-Aviso "$grupo -> $($Permisos[$grupo]) : $($_.Exception.Message)" }
    }
}

# --- Contratos: nadie borra. Solo el administrador.
Set-PermisosLista -Lista 'Contratos' -CopiarHerencia -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Aportar sin eliminar'
    'Contratos - Solicitantes'    = 'Aportar sin eliminar'
    'Contratos - Custodios'       = 'Aportar sin eliminar'
    'Contratos - Aprobadores'     = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Biblioteca documental: igual que Contratos. El expediente no se destruye.
Set-PermisosLista -Lista 'DocumentosContratos' -CopiarHerencia -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Aportar sin eliminar'
    'Contratos - Solicitantes'    = 'Aportar sin eliminar'
    'Contratos - Custodios'       = 'Aportar sin eliminar'
    'Contratos - Aprobadores'     = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Aprobaciones: historial inmutable. Solo el flujo (cuenta de servicio) y el admin escriben.
Set-PermisosLista -Lista 'Aprobaciones' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Aprobadores'     = 'Read'
    'Contratos - Legal'           = 'Read'
    'Contratos - Solicitantes'    = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Bitacora: solo agregar, jamas editar.
Set-PermisosLista -Lista 'Bitacora' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Solo agregar'
    'Contratos - Solicitantes'    = 'Solo agregar'
    'Contratos - Custodios'       = 'Solo agregar'
    'Contratos - Aprobadores'     = 'Solo agregar'
}

# --- Matriz de aprobacion: define quien aprueba. Solo administradores la editan.
Set-PermisosLista -Lista 'MatrizAprobacion' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Read'
    'Contratos - Aprobadores'     = 'Read'
    'Contratos - Solicitantes'    = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Parametros y Areas: configuracion. Lectura para todos, escritura para el admin.
foreach ($lista in @('Parametros', 'Areas')) {
    Set-PermisosLista -Lista $lista -Permisos @{
        'Contratos - Administradores' = 'Full Control'
        'Contratos - Legal'           = 'Read'
        'Contratos - Aprobadores'     = 'Read'
        'Contratos - Custodios'       = 'Read'
        'Contratos - Solicitantes'    = 'Read'
        'Contratos - Consulta'        = 'Read'
    }
}

# --- Custodia: la gestionan los custodios.
Set-PermisosLista -Lista 'MovimientosCustodia' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Custodios'       = 'Aportar sin eliminar'
    'Contratos - Legal'           = 'Read'
    'Contratos - Solicitantes'    = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Adendas: mismas reglas que Contratos.
Set-PermisosLista -Lista 'Adendas' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Aportar sin eliminar'
    'Contratos - Solicitantes'    = 'Aportar sin eliminar'
    'Contratos - Aprobadores'     = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# --- Alertas: las escribe el flujo; el resto solo consulta.
Set-PermisosLista -Lista 'Alertas' -Permisos @{
    'Contratos - Administradores' = 'Full Control'
    'Contratos - Legal'           = 'Read'
    'Contratos - Solicitantes'    = 'Read'
    'Contratos - Consulta'        = 'Read'
}

# ============================================================================
#  CIERRE
# ============================================================================

Write-Host @"

  ============================================================
   Permisos configurados.

   PENDIENTE (manual, requiere decidir personas):
     1) Agregar los usuarios a cada grupo desde
        Configuracion del sitio > Permisos del sitio.
     2) Definir la cuenta de servicio que ejecutara los flujos
        y agregarla a 'Contratos - Administradores'. Los flujos
        escriben en Aprobaciones y Bitacora, que son de solo
        lectura para el resto.
     3) Si se usa la clasificacion 'Restringido', aplicar permisos
        a nivel de elemento. Ver docs/05-seguridad-permisos.md.
  ============================================================
"@ -ForegroundColor White

Disconnect-PnPOnline
