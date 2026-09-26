/* =====================================================================
 * Contratos AB Mauri - creacion de las 13 listas y sus 134 columnas
 * ---------------------------------------------------------------------
 * COMO SE USA
 *   1. Abre tu sitio de SharePoint en Chrome o Edge, ya con sesion
 *      iniciada:  https://TU-TENANT.sharepoint.com/sites/Contratos
 *   2. F12 -> pestana "Consola"
 *   3. Si el navegador lo pide, escribe  allow pasting  y pulsa Enter
 *   4. Pega TODO este archivo y pulsa Enter
 *
 * QUE HACE
 *   Crea las listas que falten y, en cada una, las columnas que falten,
 *   usando la API REST de SharePoint con tu propia sesion. No envia nada
 *   a ningun otro sitio y no toca datos existentes.
 *
 * POR QUE NO BASTA CON CREARLAS A MANO
 *   Al crear una columna desde la interfaz, SharePoint deriva el nombre
 *   interno del visible y lo codifica ("Nombre del contrato" ->
 *   Nombre_x0020_del_x0020_contrato). Las formulas buscan
 *   NombreContrato, no lo encuentran, y SharePoint devuelve vacio sin
 *   error. Aqui se envia Options=8 (AddFieldInternalNameHint), que es lo
 *   que obliga a respetar el nombre interno del XML.
 *
 * ES SEGURO REPETIRLO
 *   Comprueba antes de crear: lo que ya existe lo deja intacto. Si algo
 *   falla a mitad, corrigelo y vuelve a ejecutar.
 * ===================================================================== */

(async function () {
  'use strict';

  var OPC_NOMBRE_INTERNO = 8;   // AddFieldInternalNameHint
  var LISTAS = [
 {
  "titulo": "Areas",
  "plantilla": 100,
  "descripcion": "Areas de la organizacion. Resuelven los roles Jefe de area y Gerente de area.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": null,
  "campos": [
   {
    "n": "CodigoArea",
    "xml": "<Field Type=\"Text\" Name=\"CodigoArea\" StaticName=\"CodigoArea\" DisplayName=\"Codigo\" MaxLength=\"20\" />"
   },
   {
    "n": "Responsable",
    "xml": "<Field Type=\"User\" Name=\"Responsable\" StaticName=\"Responsable\" DisplayName=\"Responsable\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Gerente",
    "xml": "<Field Type=\"User\" Name=\"Gerente\" StaticName=\"Gerente\" DisplayName=\"Gerente\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Vicepresidente",
    "xml": "<Field Type=\"User\" Name=\"Vicepresidente\" StaticName=\"Vicepresidente\" DisplayName=\"Vicepresidente\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "CentroCosto",
    "xml": "<Field Type=\"Text\" Name=\"CentroCosto\" StaticName=\"CentroCosto\" DisplayName=\"Centro de costo\" MaxLength=\"50\" />"
   },
   {
    "n": "Activo",
    "xml": "<Field Type=\"Boolean\" Name=\"Activo\" StaticName=\"Activo\" DisplayName=\"Activo\"><Default>1</Default></Field>"
   }
  ]
 },
 {
  "titulo": "Parametros",
  "plantilla": 100,
  "descripcion": "Configuracion global del sistema.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": null,
  "campos": [
   {
    "n": "Valor",
    "xml": "<Field Type=\"Text\" Name=\"Valor\" StaticName=\"Valor\" DisplayName=\"Valor\" Required=\"TRUE\" MaxLength=\"255\" />"
   },
   {
    "n": "Descripcion",
    "xml": "<Field Type=\"Note\" Name=\"Descripcion\" StaticName=\"Descripcion\" DisplayName=\"Descripcion\" NumLines=\"3\" RichText=\"FALSE\" />"
   },
   {
    "n": "Tipo",
    "xml": "<Field Type=\"Choice\" Name=\"Tipo\" StaticName=\"Tipo\" DisplayName=\"Tipo\"><CHOICES><CHOICE>Texto</CHOICE><CHOICE>Numero</CHOICE><CHOICE>Fecha</CHOICE><CHOICE>Booleano</CHOICE><CHOICE>Correo</CHOICE></CHOICES><Default>Texto</Default></Field>"
   }
  ]
 },
 {
  "titulo": "Categorias",
  "plantilla": 100,
  "descripcion": "Carpetas administrables que determinan que campos y clausulas se piden.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": null,
  "campos": [
   {
    "n": "CategoriaPadre",
    "xml": "<Field Type=\"Lookup\" Name=\"CategoriaPadre\" StaticName=\"CategoriaPadre\" DisplayName=\"Categoria padre\" ShowField=\"Title\" />",
    "lookup": "Categorias"
   },
   {
    "n": "Icono",
    "xml": "<Field Type=\"Text\" Name=\"Icono\" StaticName=\"Icono\" DisplayName=\"Icono\" MaxLength=\"60\" />"
   },
   {
    "n": "Color",
    "xml": "<Field Type=\"Text\" Name=\"Color\" StaticName=\"Color\" DisplayName=\"Color\" MaxLength=\"10\" />"
   },
   {
    "n": "ResponsableAdicional",
    "xml": "<Field Type=\"User\" Name=\"ResponsableAdicional\" StaticName=\"ResponsableAdicional\" DisplayName=\"Responsable adicional\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Orden",
    "xml": "<Field Type=\"Number\" Name=\"Orden\" StaticName=\"Orden\" DisplayName=\"Orden\" Decimals=\"0\"><Default>0</Default></Field>"
   },
   {
    "n": "Activo",
    "xml": "<Field Type=\"Boolean\" Name=\"Activo\" StaticName=\"Activo\" DisplayName=\"Activo\"><Default>1</Default></Field>"
   }
  ]
 },
 {
  "titulo": "CamposPersonalizados",
  "plantilla": 100,
  "descripcion": "Esquema de campos adicionales por categoria.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Nombre tecnico",
  "campos": [
   {
    "n": "Categoria",
    "xml": "<Field Type=\"Lookup\" Name=\"Categoria\" StaticName=\"Categoria\" DisplayName=\"Categoria\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Categorias"
   },
   {
    "n": "Etiqueta",
    "xml": "<Field Type=\"Text\" Name=\"Etiqueta\" StaticName=\"Etiqueta\" DisplayName=\"Etiqueta\" Required=\"TRUE\" MaxLength=\"150\" />"
   },
   {
    "n": "TipoDato",
    "xml": "<Field Type=\"Choice\" Name=\"TipoDato\" StaticName=\"TipoDato\" DisplayName=\"Tipo de dato\" Required=\"TRUE\"><CHOICES><CHOICE>Texto</CHOICE><CHOICE>Numero</CHOICE><CHOICE>Fecha</CHOICE><CHOICE>Booleano</CHOICE><CHOICE>Opcion</CHOICE></CHOICES></Field>"
   },
   {
    "n": "Opciones",
    "xml": "<Field Type=\"Text\" Name=\"Opciones\" StaticName=\"Opciones\" DisplayName=\"Opciones\" MaxLength=\"255\" />"
   },
   {
    "n": "Seccion",
    "xml": "<Field Type=\"Text\" Name=\"Seccion\" StaticName=\"Seccion\" DisplayName=\"Seccion\" MaxLength=\"100\" />"
   },
   {
    "n": "Obligatorio",
    "xml": "<Field Type=\"Boolean\" Name=\"Obligatorio\" StaticName=\"Obligatorio\" DisplayName=\"Obligatorio\"><Default>0</Default></Field>"
   },
   {
    "n": "Orden",
    "xml": "<Field Type=\"Number\" Name=\"Orden\" StaticName=\"Orden\" DisplayName=\"Orden\" Decimals=\"0\"><Default>0</Default></Field>"
   },
   {
    "n": "Ayuda",
    "xml": "<Field Type=\"Text\" Name=\"Ayuda\" StaticName=\"Ayuda\" DisplayName=\"Ayuda\" MaxLength=\"255\" />"
   },
   {
    "n": "Activo",
    "xml": "<Field Type=\"Boolean\" Name=\"Activo\" StaticName=\"Activo\" DisplayName=\"Activo\"><Default>1</Default></Field>"
   }
  ]
 },
 {
  "titulo": "Contratos",
  "plantilla": 100,
  "descripcion": "Maestro de contratos. Una fila = un contrato.",
  "versionado": true,
  "versionesMenores": false,
  "tituloTitle": "Codigo",
  "campos": [
   {
    "n": "NombreContrato",
    "xml": "<Field Type=\"Text\" Name=\"NombreContrato\" StaticName=\"NombreContrato\" DisplayName=\"Nombre del contrato\" Required=\"TRUE\" Indexed=\"TRUE\" MaxLength=\"255\" />"
   },
   {
    "n": "TipoContrato",
    "xml": "<Field Type=\"Choice\" Name=\"TipoContrato\" StaticName=\"TipoContrato\" DisplayName=\"Tipo de contrato\" Required=\"TRUE\" Indexed=\"TRUE\"><CHOICES><CHOICE>Servicios</CHOICE><CHOICE>Suministro de bienes</CHOICE><CHOICE>Obra</CHOICE><CHOICE>Arrendamiento</CHOICE><CHOICE>Confidencialidad (NDA)</CHOICE><CHOICE>Licencia de software</CHOICE><CHOICE>Distribucion</CHOICE><CHOICE>Agencia / Representacion</CHOICE><CHOICE>Laboral</CHOICE><CHOICE>Seguros</CHOICE><CHOICE>Financiero</CHOICE><CHOICE>Convenio / Adendum marco</CHOICE><CHOICE>Otro</CHOICE></CHOICES></Field>"
   },
   {
    "n": "ObjetoContrato",
    "xml": "<Field Type=\"Note\" Name=\"ObjetoContrato\" StaticName=\"ObjetoContrato\" DisplayName=\"Objeto del contrato\" NumLines=\"6\" RichText=\"FALSE\" />"
   },
   {
    "n": "ContratoPadre",
    "xml": "<Field Type=\"Lookup\" Name=\"ContratoPadre\" StaticName=\"ContratoPadre\" DisplayName=\"Contrato relacionado\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "Categoria",
    "xml": "<Field Type=\"Lookup\" Name=\"Categoria\" StaticName=\"Categoria\" DisplayName=\"Categoria\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Categorias"
   },
   {
    "n": "Contraparte",
    "xml": "<Field Type=\"Text\" Name=\"Contraparte\" StaticName=\"Contraparte\" DisplayName=\"Contraparte\" Required=\"TRUE\" Indexed=\"TRUE\" MaxLength=\"255\" />"
   },
   {
    "n": "ContraparteRUC",
    "xml": "<Field Type=\"Text\" Name=\"ContraparteRUC\" StaticName=\"ContraparteRUC\" DisplayName=\"RUC / Doc. identidad\" MaxLength=\"20\" />"
   },
   {
    "n": "TipoContraparte",
    "xml": "<Field Type=\"Choice\" Name=\"TipoContraparte\" StaticName=\"TipoContraparte\" DisplayName=\"Tipo de contraparte\"><CHOICES><CHOICE>Proveedor</CHOICE><CHOICE>Cliente</CHOICE><CHOICE>Empleado</CHOICE><CHOICE>Socio comercial</CHOICE><CHOICE>Entidad publica</CHOICE><CHOICE>Otro</CHOICE></CHOICES><Default>Proveedor</Default></Field>"
   },
   {
    "n": "ContraparteContacto",
    "xml": "<Field Type=\"Text\" Name=\"ContraparteContacto\" StaticName=\"ContraparteContacto\" DisplayName=\"Contacto (firmante)\" MaxLength=\"150\" />"
   },
   {
    "n": "ContraparteCorreo",
    "xml": "<Field Type=\"Text\" Name=\"ContraparteCorreo\" StaticName=\"ContraparteCorreo\" DisplayName=\"Correo del firmante\" MaxLength=\"150\" />"
   },
   {
    "n": "AreaSolicitante",
    "xml": "<Field Type=\"Lookup\" Name=\"AreaSolicitante\" StaticName=\"AreaSolicitante\" DisplayName=\"Area solicitante\" Required=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Areas"
   },
   {
    "n": "Solicitante",
    "xml": "<Field Type=\"User\" Name=\"Solicitante\" StaticName=\"Solicitante\" DisplayName=\"Solicitante\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "ResponsableContrato",
    "xml": "<Field Type=\"User\" Name=\"ResponsableContrato\" StaticName=\"ResponsableContrato\" DisplayName=\"Responsable del contrato\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Moneda",
    "xml": "<Field Type=\"Choice\" Name=\"Moneda\" StaticName=\"Moneda\" DisplayName=\"Moneda\"><CHOICES><CHOICE>PEN</CHOICE><CHOICE>USD</CHOICE><CHOICE>EUR</CHOICE></CHOICES><Default>PEN</Default></Field>"
   },
   {
    "n": "Monto",
    "xml": "<Field Type=\"Number\" Name=\"Monto\" StaticName=\"Monto\" DisplayName=\"Monto\" Decimals=\"2\" />"
   },
   {
    "n": "MontoPEN",
    "xml": "<Field Type=\"Number\" Name=\"MontoPEN\" StaticName=\"MontoPEN\" DisplayName=\"Monto en PEN\" Decimals=\"2\" />"
   },
   {
    "n": "TipoCambio",
    "xml": "<Field Type=\"Number\" Name=\"TipoCambio\" StaticName=\"TipoCambio\" DisplayName=\"Tipo de cambio\" Decimals=\"4\" />"
   },
   {
    "n": "SinMontoDeterminado",
    "xml": "<Field Type=\"Boolean\" Name=\"SinMontoDeterminado\" StaticName=\"SinMontoDeterminado\" DisplayName=\"Monto no determinado\"><Default>0</Default></Field>"
   },
   {
    "n": "FechaInicio",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaInicio\" StaticName=\"FechaInicio\" DisplayName=\"Fecha de inicio\" Required=\"TRUE\" Format=\"DateOnly\" />"
   },
   {
    "n": "FechaFin",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaFin\" StaticName=\"FechaFin\" DisplayName=\"Fecha de fin\" Indexed=\"TRUE\" Format=\"DateOnly\" />"
   },
   {
    "n": "VigenciaIndefinida",
    "xml": "<Field Type=\"Boolean\" Name=\"VigenciaIndefinida\" StaticName=\"VigenciaIndefinida\" DisplayName=\"Vigencia indefinida\"><Default>0</Default></Field>"
   },
   {
    "n": "RenovacionAutomatica",
    "xml": "<Field Type=\"Boolean\" Name=\"RenovacionAutomatica\" StaticName=\"RenovacionAutomatica\" DisplayName=\"Renovacion automatica\"><Default>0</Default></Field>"
   },
   {
    "n": "DiasPreaviso",
    "xml": "<Field Type=\"Number\" Name=\"DiasPreaviso\" StaticName=\"DiasPreaviso\" DisplayName=\"Dias de preaviso\" Decimals=\"0\"><Default>30</Default></Field>"
   },
   {
    "n": "FechaPreaviso",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaPreaviso\" StaticName=\"FechaPreaviso\" DisplayName=\"Fecha de preaviso\" Indexed=\"TRUE\" Format=\"DateOnly\" />"
   },
   {
    "n": "Estado",
    "xml": "<Field Type=\"Choice\" Name=\"Estado\" StaticName=\"Estado\" DisplayName=\"Estado\" Indexed=\"TRUE\"><CHOICES><CHOICE>Borrador</CHOICE><CHOICE>En revision legal</CHOICE><CHOICE>En aprobacion</CHOICE><CHOICE>Aprobado</CHOICE><CHOICE>En firma</CHOICE><CHOICE>Vigente</CHOICE><CHOICE>Por vencer</CHOICE><CHOICE>Vencido</CHOICE><CHOICE>Renovado</CHOICE><CHOICE>Terminado</CHOICE><CHOICE>Rechazado</CHOICE><CHOICE>Anulado</CHOICE></CHOICES><Default>Borrador</Default></Field>"
   },
   {
    "n": "NivelAprobacionRequerido",
    "xml": "<Field Type=\"Number\" Name=\"NivelAprobacionRequerido\" StaticName=\"NivelAprobacionRequerido\" DisplayName=\"Nivel requerido\" Decimals=\"0\"><Default>0</Default></Field>"
   },
   {
    "n": "NivelAprobacionActual",
    "xml": "<Field Type=\"Number\" Name=\"NivelAprobacionActual\" StaticName=\"NivelAprobacionActual\" DisplayName=\"Nivel actual\" Decimals=\"0\"><Default>0</Default></Field>"
   },
   {
    "n": "CicloAprobacion",
    "xml": "<Field Type=\"Number\" Name=\"CicloAprobacion\" StaticName=\"CicloAprobacion\" DisplayName=\"Ciclo de aprobacion\" Decimals=\"0\"><Default>0</Default></Field>"
   },
   {
    "n": "FechaEnvioAprobacion",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaEnvioAprobacion\" StaticName=\"FechaEnvioAprobacion\" DisplayName=\"Enviado a aprobacion\" Format=\"DateTime\" />"
   },
   {
    "n": "FechaAprobacionFinal",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaAprobacionFinal\" StaticName=\"FechaAprobacionFinal\" DisplayName=\"Aprobacion final\" Format=\"DateTime\" />"
   },
   {
    "n": "MotivoRechazo",
    "xml": "<Field Type=\"Note\" Name=\"MotivoRechazo\" StaticName=\"MotivoRechazo\" DisplayName=\"Motivo de rechazo\" NumLines=\"4\" RichText=\"FALSE\" />"
   },
   {
    "n": "DocuSignEnvelopeId",
    "xml": "<Field Type=\"Text\" Name=\"DocuSignEnvelopeId\" StaticName=\"DocuSignEnvelopeId\" DisplayName=\"Sobre DocuSign\" MaxLength=\"100\" />"
   },
   {
    "n": "DocuSignEstado",
    "xml": "<Field Type=\"Choice\" Name=\"DocuSignEstado\" StaticName=\"DocuSignEstado\" DisplayName=\"Estado DocuSign\"><CHOICES><CHOICE>No enviado</CHOICE><CHOICE>Enviado</CHOICE><CHOICE>Entregado</CHOICE><CHOICE>Firmado</CHOICE><CHOICE>Completado</CHOICE><CHOICE>Rechazado</CHOICE><CHOICE>Anulado</CHOICE></CHOICES><Default>No enviado</Default></Field>"
   },
   {
    "n": "FechaFirma",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaFirma\" StaticName=\"FechaFirma\" DisplayName=\"Fecha de firma\" Format=\"DateTime\" />"
   },
   {
    "n": "EstadoCustodia",
    "xml": "<Field Type=\"Choice\" Name=\"EstadoCustodia\" StaticName=\"EstadoCustodia\" DisplayName=\"Estado de custodia\" Indexed=\"TRUE\"><CHOICES><CHOICE>Pendiente de recepcion</CHOICE><CHOICE>En custodia</CHOICE><CHOICE>Prestado</CHOICE><CHOICE>Solo digital</CHOICE><CHOICE>Dado de baja</CHOICE></CHOICES><Default>Pendiente de recepcion</Default></Field>"
   },
   {
    "n": "Custodio",
    "xml": "<Field Type=\"User\" Name=\"Custodio\" StaticName=\"Custodio\" DisplayName=\"Custodio\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "UbicacionFisica",
    "xml": "<Field Type=\"Text\" Name=\"UbicacionFisica\" StaticName=\"UbicacionFisica\" DisplayName=\"Ubicacion fisica\" MaxLength=\"150\" />"
   },
   {
    "n": "FechaRecepcionOriginal",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaRecepcionOriginal\" StaticName=\"FechaRecepcionOriginal\" DisplayName=\"Recepcion del original\" Format=\"DateOnly\" />"
   },
   {
    "n": "Clasificacion",
    "xml": "<Field Type=\"Choice\" Name=\"Clasificacion\" StaticName=\"Clasificacion\" DisplayName=\"Clasificacion\"><CHOICES><CHOICE>Publico</CHOICE><CHOICE>Interno</CHOICE><CHOICE>Confidencial</CHOICE><CHOICE>Restringido</CHOICE></CHOICES><Default>Interno</Default></Field>"
   },
   {
    "n": "ObligacionesClave",
    "xml": "<Field Type=\"Note\" Name=\"ObligacionesClave\" StaticName=\"ObligacionesClave\" DisplayName=\"Obligaciones clave\" NumLines=\"6\" RichText=\"FALSE\" />"
   },
   {
    "n": "Penalidades",
    "xml": "<Field Type=\"Note\" Name=\"Penalidades\" StaticName=\"Penalidades\" DisplayName=\"Penalidades\" NumLines=\"4\" RichText=\"FALSE\" />"
   },
   {
    "n": "TieneGarantia",
    "xml": "<Field Type=\"Boolean\" Name=\"TieneGarantia\" StaticName=\"TieneGarantia\" DisplayName=\"Tiene garantia\"><Default>0</Default></Field>"
   },
   {
    "n": "TipoGarantia",
    "xml": "<Field Type=\"Choice\" Name=\"TipoGarantia\" StaticName=\"TipoGarantia\" DisplayName=\"Tipo de garantia\"><CHOICES><CHOICE>Carta fianza</CHOICE><CHOICE>Retencion</CHOICE><CHOICE>Deposito en garantia</CHOICE><CHOICE>Poliza de caucion</CHOICE><CHOICE>Otra</CHOICE></CHOICES></Field>"
   },
   {
    "n": "MontoGarantia",
    "xml": "<Field Type=\"Number\" Name=\"MontoGarantia\" StaticName=\"MontoGarantia\" DisplayName=\"Monto de garantia\" Decimals=\"2\" />"
   },
   {
    "n": "VencimientoGarantia",
    "xml": "<Field Type=\"DateTime\" Name=\"VencimientoGarantia\" StaticName=\"VencimientoGarantia\" DisplayName=\"Vencimiento de garantia\" Format=\"DateOnly\" />"
   },
   {
    "n": "Notas",
    "xml": "<Field Type=\"Note\" Name=\"Notas\" StaticName=\"Notas\" DisplayName=\"Notas\" NumLines=\"6\" RichText=\"FALSE\" />"
   }
  ]
 },
 {
  "titulo": "DocumentosContratos",
  "plantilla": 101,
  "descripcion": "Biblioteca de custodia digital.",
  "versionado": true,
  "versionesMenores": true,
  "tituloTitle": null,
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "TipoDocumento",
    "xml": "<Field Type=\"Choice\" Name=\"TipoDocumento\" StaticName=\"TipoDocumento\" DisplayName=\"Tipo de documento\" Required=\"TRUE\"><CHOICES><CHOICE>Contrato original</CHOICE><CHOICE>Adenda</CHOICE><CHOICE>Anexo</CHOICE><CHOICE>Cotizacion</CHOICE><CHOICE>Orden de compra</CHOICE><CHOICE>Carta fianza</CHOICE><CHOICE>Acta de recepcion</CHOICE><CHOICE>Sustento de aprobacion</CHOICE><CHOICE>Sobre firmado</CHOICE><CHOICE>Otro</CHOICE></CHOICES><Default>Contrato original</Default></Field>"
   },
   {
    "n": "VersionDocumento",
    "xml": "<Field Type=\"Text\" Name=\"VersionDocumento\" StaticName=\"VersionDocumento\" DisplayName=\"Version del documento\" MaxLength=\"30\" />"
   },
   {
    "n": "FechaDocumento",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaDocumento\" StaticName=\"FechaDocumento\" DisplayName=\"Fecha del documento\" Format=\"DateOnly\" />"
   },
   {
    "n": "EsPrincipal",
    "xml": "<Field Type=\"Boolean\" Name=\"EsPrincipal\" StaticName=\"EsPrincipal\" DisplayName=\"Es documento principal\"><Default>0</Default></Field>"
   },
   {
    "n": "EstaFirmado",
    "xml": "<Field Type=\"Boolean\" Name=\"EstaFirmado\" StaticName=\"EstaFirmado\" DisplayName=\"Esta firmado\"><Default>0</Default></Field>"
   },
   {
    "n": "EsConfidencial",
    "xml": "<Field Type=\"Boolean\" Name=\"EsConfidencial\" StaticName=\"EsConfidencial\" DisplayName=\"Confidencial\"><Default>0</Default></Field>"
   }
  ]
 },
 {
  "titulo": "MatrizAprobacion",
  "plantilla": 100,
  "descripcion": "Reglas de aprobacion por tipo de contrato y monto.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Regla",
  "campos": [
   {
    "n": "TipoContrato",
    "xml": "<Field Type=\"Choice\" Name=\"TipoContrato\" StaticName=\"TipoContrato\" DisplayName=\"Tipo de contrato\" Required=\"TRUE\"><CHOICES><CHOICE>Todos</CHOICE><CHOICE>Servicios</CHOICE><CHOICE>Suministro de bienes</CHOICE><CHOICE>Obra</CHOICE><CHOICE>Arrendamiento</CHOICE><CHOICE>Confidencialidad (NDA)</CHOICE><CHOICE>Licencia de software</CHOICE><CHOICE>Distribucion</CHOICE><CHOICE>Agencia / Representacion</CHOICE><CHOICE>Laboral</CHOICE><CHOICE>Seguros</CHOICE><CHOICE>Financiero</CHOICE><CHOICE>Convenio / Adendum marco</CHOICE><CHOICE>Otro</CHOICE></CHOICES><Default>Todos</Default></Field>"
   },
   {
    "n": "MontoDesdePEN",
    "xml": "<Field Type=\"Number\" Name=\"MontoDesdePEN\" StaticName=\"MontoDesdePEN\" DisplayName=\"Monto desde (PEN)\" Required=\"TRUE\" Decimals=\"2\"><Default>0</Default></Field>"
   },
   {
    "n": "MontoHastaPEN",
    "xml": "<Field Type=\"Number\" Name=\"MontoHastaPEN\" StaticName=\"MontoHastaPEN\" DisplayName=\"Monto hasta (PEN)\" Required=\"TRUE\" Decimals=\"2\" />"
   },
   {
    "n": "Nivel",
    "xml": "<Field Type=\"Number\" Name=\"Nivel\" StaticName=\"Nivel\" DisplayName=\"Nivel\" Required=\"TRUE\" Decimals=\"0\" />"
   },
   {
    "n": "RolAprobador",
    "xml": "<Field Type=\"Choice\" Name=\"RolAprobador\" StaticName=\"RolAprobador\" DisplayName=\"Rol del aprobador\" Required=\"TRUE\"><CHOICES><CHOICE>Jefe de area</CHOICE><CHOICE>Gerente de area</CHOICE><CHOICE>Vicepresidencia de area</CHOICE><CHOICE>Legal</CHOICE><CHOICE>Finanzas</CHOICE><CHOICE>Compras</CHOICE><CHOICE>Gerencia General</CHOICE><CHOICE>Directorio</CHOICE><CHOICE>Usuario especifico</CHOICE></CHOICES></Field>"
   },
   {
    "n": "AprobadorUsuario",
    "xml": "<Field Type=\"User\" Name=\"AprobadorUsuario\" StaticName=\"AprobadorUsuario\" DisplayName=\"Aprobador (usuario)\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "AprobadorGrupo",
    "xml": "<Field Type=\"Text\" Name=\"AprobadorGrupo\" StaticName=\"AprobadorGrupo\" DisplayName=\"Aprobador (grupo)\" MaxLength=\"255\" />"
   },
   {
    "n": "Obligatorio",
    "xml": "<Field Type=\"Boolean\" Name=\"Obligatorio\" StaticName=\"Obligatorio\" DisplayName=\"Obligatorio\"><Default>1</Default></Field>"
   },
   {
    "n": "SLAHoras",
    "xml": "<Field Type=\"Number\" Name=\"SLAHoras\" StaticName=\"SLAHoras\" DisplayName=\"SLA (horas)\" Decimals=\"0\"><Default>48</Default></Field>"
   },
   {
    "n": "Activo",
    "xml": "<Field Type=\"Boolean\" Name=\"Activo\" StaticName=\"Activo\" DisplayName=\"Activo\"><Default>1</Default></Field>"
   }
  ]
 },
 {
  "titulo": "Aprobaciones",
  "plantilla": 100,
  "descripcion": "Historial inmutable de decisiones.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Referencia",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "Nivel",
    "xml": "<Field Type=\"Number\" Name=\"Nivel\" StaticName=\"Nivel\" DisplayName=\"Nivel\" Decimals=\"0\" />"
   },
   {
    "n": "Ciclo",
    "xml": "<Field Type=\"Number\" Name=\"Ciclo\" StaticName=\"Ciclo\" DisplayName=\"Ciclo\" Decimals=\"0\"><Default>1</Default></Field>"
   },
   {
    "n": "RolAprobador",
    "xml": "<Field Type=\"Text\" Name=\"RolAprobador\" StaticName=\"RolAprobador\" DisplayName=\"Rol del aprobador\" MaxLength=\"100\" />"
   },
   {
    "n": "AprobadorAsignado",
    "xml": "<Field Type=\"User\" Name=\"AprobadorAsignado\" StaticName=\"AprobadorAsignado\" DisplayName=\"Aprobador asignado\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "ResueltoPor",
    "xml": "<Field Type=\"User\" Name=\"ResueltoPor\" StaticName=\"ResueltoPor\" DisplayName=\"Resuelto por\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Decision",
    "xml": "<Field Type=\"Choice\" Name=\"Decision\" StaticName=\"Decision\" DisplayName=\"Decision\" Indexed=\"TRUE\"><CHOICES><CHOICE>Pendiente</CHOICE><CHOICE>Aprobado</CHOICE><CHOICE>Rechazado</CHOICE><CHOICE>Devuelto</CHOICE><CHOICE>Delegado</CHOICE><CHOICE>Omitido</CHOICE><CHOICE>Vencido</CHOICE></CHOICES><Default>Pendiente</Default></Field>"
   },
   {
    "n": "Comentarios",
    "xml": "<Field Type=\"Note\" Name=\"Comentarios\" StaticName=\"Comentarios\" DisplayName=\"Comentarios\" NumLines=\"4\" RichText=\"FALSE\" />"
   },
   {
    "n": "FechaSolicitud",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaSolicitud\" StaticName=\"FechaSolicitud\" DisplayName=\"Fecha de solicitud\" Format=\"DateTime\" />"
   },
   {
    "n": "FechaDecision",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaDecision\" StaticName=\"FechaDecision\" DisplayName=\"Fecha de decision\" Format=\"DateTime\" />"
   },
   {
    "n": "HorasTranscurridas",
    "xml": "<Field Type=\"Number\" Name=\"HorasTranscurridas\" StaticName=\"HorasTranscurridas\" DisplayName=\"Horas transcurridas\" Decimals=\"1\" />"
   },
   {
    "n": "InstanciaFlujo",
    "xml": "<Field Type=\"Text\" Name=\"InstanciaFlujo\" StaticName=\"InstanciaFlujo\" DisplayName=\"Instancia del flujo\" MaxLength=\"100\" />"
   }
  ]
 },
 {
  "titulo": "Adendas",
  "plantilla": 100,
  "descripcion": "Modificaciones a contratos vigentes.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Codigo",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "NumeroAdenda",
    "xml": "<Field Type=\"Number\" Name=\"NumeroAdenda\" StaticName=\"NumeroAdenda\" DisplayName=\"Numero de adenda\" Decimals=\"0\" />"
   },
   {
    "n": "TipoAdenda",
    "xml": "<Field Type=\"Choice\" Name=\"TipoAdenda\" StaticName=\"TipoAdenda\" DisplayName=\"Tipo de adenda\" Required=\"TRUE\"><CHOICES><CHOICE>Prorroga de plazo</CHOICE><CHOICE>Ampliacion de monto</CHOICE><CHOICE>Reduccion de monto</CHOICE><CHOICE>Cambio de alcance</CHOICE><CHOICE>Cesion de posicion</CHOICE><CHOICE>Resolucion anticipada</CHOICE><CHOICE>Otro</CHOICE></CHOICES></Field>"
   },
   {
    "n": "FechaAdenda",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaAdenda\" StaticName=\"FechaAdenda\" DisplayName=\"Fecha de la adenda\" Format=\"DateOnly\" />"
   },
   {
    "n": "MontoDelta",
    "xml": "<Field Type=\"Number\" Name=\"MontoDelta\" StaticName=\"MontoDelta\" DisplayName=\"Variacion de monto\" Decimals=\"2\" />"
   },
   {
    "n": "NuevaFechaFin",
    "xml": "<Field Type=\"DateTime\" Name=\"NuevaFechaFin\" StaticName=\"NuevaFechaFin\" DisplayName=\"Nueva fecha de fin\" Format=\"DateOnly\" />"
   },
   {
    "n": "Descripcion",
    "xml": "<Field Type=\"Note\" Name=\"Descripcion\" StaticName=\"Descripcion\" DisplayName=\"Descripcion\" NumLines=\"6\" RichText=\"FALSE\" />"
   },
   {
    "n": "Estado",
    "xml": "<Field Type=\"Choice\" Name=\"Estado\" StaticName=\"Estado\" DisplayName=\"Estado\"><CHOICES><CHOICE>Borrador</CHOICE><CHOICE>En aprobacion</CHOICE><CHOICE>Aprobada</CHOICE><CHOICE>Rechazada</CHOICE></CHOICES><Default>Borrador</Default></Field>"
   }
  ]
 },
 {
  "titulo": "MovimientosCustodia",
  "plantilla": 100,
  "descripcion": "Cadena de custodia del original fisico.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Referencia",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "TipoMovimiento",
    "xml": "<Field Type=\"Choice\" Name=\"TipoMovimiento\" StaticName=\"TipoMovimiento\" DisplayName=\"Tipo de movimiento\" Required=\"TRUE\"><CHOICES><CHOICE>Recepcion de original</CHOICE><CHOICE>Prestamo</CHOICE><CHOICE>Devolucion</CHOICE><CHOICE>Traslado</CHOICE><CHOICE>Digitalizacion</CHOICE><CHOICE>Baja / Destruccion</CHOICE></CHOICES></Field>"
   },
   {
    "n": "FechaMovimiento",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaMovimiento\" StaticName=\"FechaMovimiento\" DisplayName=\"Fecha del movimiento\" Required=\"TRUE\" Format=\"DateTime\" />"
   },
   {
    "n": "SolicitadoPor",
    "xml": "<Field Type=\"User\" Name=\"SolicitadoPor\" StaticName=\"SolicitadoPor\" DisplayName=\"Solicitado por\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "EntregadoPor",
    "xml": "<Field Type=\"User\" Name=\"EntregadoPor\" StaticName=\"EntregadoPor\" DisplayName=\"Entregado por\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "UbicacionOrigen",
    "xml": "<Field Type=\"Text\" Name=\"UbicacionOrigen\" StaticName=\"UbicacionOrigen\" DisplayName=\"Ubicacion origen\" MaxLength=\"150\" />"
   },
   {
    "n": "UbicacionDestino",
    "xml": "<Field Type=\"Text\" Name=\"UbicacionDestino\" StaticName=\"UbicacionDestino\" DisplayName=\"Ubicacion destino\" MaxLength=\"150\" />"
   },
   {
    "n": "FechaCompromisoDevolucion",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaCompromisoDevolucion\" StaticName=\"FechaCompromisoDevolucion\" DisplayName=\"Compromiso de devolucion\" Indexed=\"TRUE\" Format=\"DateOnly\" />"
   },
   {
    "n": "FechaDevolucionReal",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaDevolucionReal\" StaticName=\"FechaDevolucionReal\" DisplayName=\"Devolucion real\" Indexed=\"TRUE\" Format=\"DateOnly\" />"
   },
   {
    "n": "ActaFirmada",
    "xml": "<Field Type=\"Boolean\" Name=\"ActaFirmada\" StaticName=\"ActaFirmada\" DisplayName=\"Acta firmada\"><Default>0</Default></Field>"
   },
   {
    "n": "Observaciones",
    "xml": "<Field Type=\"Note\" Name=\"Observaciones\" StaticName=\"Observaciones\" DisplayName=\"Observaciones\" NumLines=\"4\" RichText=\"FALSE\" />"
   }
  ]
 },
 {
  "titulo": "Alertas",
  "plantilla": 100,
  "descripcion": "Bitacora de notificaciones, evita duplicados.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Referencia",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "TipoAlerta",
    "xml": "<Field Type=\"Choice\" Name=\"TipoAlerta\" StaticName=\"TipoAlerta\" DisplayName=\"Tipo de alerta\" Required=\"TRUE\"><CHOICES><CHOICE>Preaviso de vencimiento</CHOICE><CHOICE>Vencimiento</CHOICE><CHOICE>Renovacion automatica</CHOICE><CHOICE>Vencimiento de garantia</CHOICE><CHOICE>Prestamo vencido</CHOICE><CHOICE>Aprobacion pendiente</CHOICE><CHOICE>SLA vencido</CHOICE></CHOICES></Field>"
   },
   {
    "n": "DiasAnticipacion",
    "xml": "<Field Type=\"Number\" Name=\"DiasAnticipacion\" StaticName=\"DiasAnticipacion\" DisplayName=\"Dias de anticipacion\" Decimals=\"0\" />"
   },
   {
    "n": "FechaEnvio",
    "xml": "<Field Type=\"DateTime\" Name=\"FechaEnvio\" StaticName=\"FechaEnvio\" DisplayName=\"Fecha de envio\" Format=\"DateTime\" />"
   },
   {
    "n": "Destinatarios",
    "xml": "<Field Type=\"Text\" Name=\"Destinatarios\" StaticName=\"Destinatarios\" DisplayName=\"Destinatarios\" MaxLength=\"255\" />"
   },
   {
    "n": "Canal",
    "xml": "<Field Type=\"Choice\" Name=\"Canal\" StaticName=\"Canal\" DisplayName=\"Canal\"><CHOICES><CHOICE>Correo</CHOICE><CHOICE>Teams</CHOICE><CHOICE>Ambos</CHOICE></CHOICES><Default>Correo</Default></Field>"
   }
  ]
 },
 {
  "titulo": "Bitacora",
  "plantilla": 100,
  "descripcion": "Auditoria funcional de acciones de la app.",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Referencia",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "Accion",
    "xml": "<Field Type=\"Text\" Name=\"Accion\" StaticName=\"Accion\" DisplayName=\"Accion\" MaxLength=\"100\" />"
   },
   {
    "n": "Usuario",
    "xml": "<Field Type=\"User\" Name=\"Usuario\" StaticName=\"Usuario\" DisplayName=\"Usuario\" UserSelectionMode=\"PeopleOnly\" />"
   },
   {
    "n": "Fecha",
    "xml": "<Field Type=\"DateTime\" Name=\"Fecha\" StaticName=\"Fecha\" DisplayName=\"Fecha\" Format=\"DateTime\" />"
   },
   {
    "n": "Detalle",
    "xml": "<Field Type=\"Note\" Name=\"Detalle\" StaticName=\"Detalle\" DisplayName=\"Detalle\" NumLines=\"4\" RichText=\"FALSE\" />"
   }
  ]
 },
 {
  "titulo": "ContratosCamposValor",
  "plantilla": 100,
  "descripcion": "Valor de cada campo personalizado (patron EAV).",
  "versionado": false,
  "versionesMenores": false,
  "tituloTitle": "Referencia",
  "campos": [
   {
    "n": "Contrato",
    "xml": "<Field Type=\"Lookup\" Name=\"Contrato\" StaticName=\"Contrato\" DisplayName=\"Contrato\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "Contratos"
   },
   {
    "n": "Campo",
    "xml": "<Field Type=\"Lookup\" Name=\"Campo\" StaticName=\"Campo\" DisplayName=\"Campo\" Required=\"TRUE\" Indexed=\"TRUE\" ShowField=\"Title\" />",
    "lookup": "CamposPersonalizados"
   },
   {
    "n": "ValorTexto",
    "xml": "<Field Type=\"Text\" Name=\"ValorTexto\" StaticName=\"ValorTexto\" DisplayName=\"Valor texto\" MaxLength=\"255\" />"
   },
   {
    "n": "ValorNumero",
    "xml": "<Field Type=\"Number\" Name=\"ValorNumero\" StaticName=\"ValorNumero\" DisplayName=\"Valor numero\" Decimals=\"4\" />"
   },
   {
    "n": "ValorFecha",
    "xml": "<Field Type=\"DateTime\" Name=\"ValorFecha\" StaticName=\"ValorFecha\" DisplayName=\"Valor fecha\" Format=\"DateOnly\" />"
   },
   {
    "n": "ValorBooleano",
    "xml": "<Field Type=\"Boolean\" Name=\"ValorBooleano\" StaticName=\"ValorBooleano\" DisplayName=\"Valor booleano\" />"
   }
  ]
 }
];

  var sitio = _spPageContextInfo && _spPageContextInfo.webAbsoluteUrl
    ? _spPageContextInfo.webAbsoluteUrl
    : location.origin + location.pathname.split('/_layouts')[0]
        .split('/Lists')[0].replace(/\/[^/]*\.aspx$/, '').replace(/\/$/, '');

  console.log('%cSitio: ' + sitio, 'font-weight:bold');

  var digest = null;
  async function obtenerDigest() {
    var r = await fetch(sitio + '/_api/contextinfo', {
      method: 'POST',
      headers: { 'Accept': 'application/json;odata=verbose' },
      credentials: 'include'
    });
    if (!r.ok) throw new Error('No se pudo obtener el digest (' + r.status + '). Verifica que la URL del sitio sea la correcta.');
    var j = await r.json();
    digest = j.d.GetContextWebInformation.FormDigestValue;
  }

  function cab(extra) {
    var h = {
      'Accept': 'application/json;odata=verbose',
      'Content-Type': 'application/json;odata=verbose',
      'X-RequestDigest': digest
    };
    for (var k in (extra || {})) h[k] = extra[k];
    return h;
  }

  async function pedir(url, opciones) {
    var r = await fetch(sitio + url, Object.assign({ credentials: 'include' }, opciones));
    if (!r.ok) {
      var t = await r.text();
      var m = t;
      try { m = JSON.parse(t).error.message.value; } catch (e) {}
      var err = new Error(m);
      err.status = r.status;
      throw err;
    }
    return r.status === 204 ? null : r.json();
  }

  async function existeLista(titulo) {
    try {
      var j = await pedir("/_api/web/lists/getbytitle('" + titulo + "')?$select=Id,Title", {
        headers: { 'Accept': 'application/json;odata=verbose' }
      });
      return j.d.Id;
    } catch (e) { return null; }
  }

  async function crearLista(L) {
    var cuerpo = {
      '__metadata': { 'type': 'SP.List' },
      'Title': L.titulo,
      'BaseTemplate': L.plantilla,
      'Description': L.descripcion,
      'AllowContentTypes': false,
      'ContentTypesEnabled': false
    };
    if (L.versionado) cuerpo.EnableVersioning = true;
    if (L.versionesMenores) cuerpo.EnableMinorVersions = true;
    var j = await pedir('/_api/web/lists', {
      method: 'POST', headers: cab(), body: JSON.stringify(cuerpo)
    });
    return j.d.Id;
  }

  async function columnasDe(titulo) {
    var j = await pedir("/_api/web/lists/getbytitle('" + titulo +
      "')/fields?$select=InternalName&$top=500", {
      headers: { 'Accept': 'application/json;odata=verbose' }
    });
    var s = {};
    j.d.results.forEach(function (f) { s[f.InternalName] = true; });
    return s;
  }

  async function crearColumna(titulo, xml) {
    return pedir("/_api/web/lists/getbytitle('" + titulo + "')/fields/createfieldasxml", {
      method: 'POST', headers: cab(),
      body: JSON.stringify({
        'parameters': {
          '__metadata': { 'type': 'SP.XmlSchemaFieldCreationInformation' },
          'SchemaXml': xml,
          'Options': OPC_NOMBRE_INTERNO
        }
      })
    });
  }

  async function renombrarTitle(titulo, nuevo) {
    return pedir("/_api/web/lists/getbytitle('" + titulo + "')/fields/getbytitle('Title')", {
      method: 'POST',
      headers: cab({ 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' }),
      body: JSON.stringify({
        '__metadata': { 'type': 'SP.Field' }, 'Title': nuevo, 'Required': false
      })
    });
  }

  // ---------------------------------------------------------------- 1/3
  await obtenerDigest();
  console.log('%c1/3  Creando las listas', 'font-weight:bold;font-size:13px');

  var ids = {};
  for (var i = 0; i < LISTAS.length; i++) {
    var L = LISTAS[i];
    var id = await existeLista(L.titulo);
    if (id) {
      console.log('   ya existia   ' + L.titulo);
    } else {
      try {
        id = await crearLista(L);
        console.log('%c   creada       ' + L.titulo, 'color:#2f6b3f');
      } catch (e) {
        console.error('   FALLO        ' + L.titulo + ' -> ' + e.message);
        continue;
      }
    }
    ids[L.titulo] = id;
    if (L.tituloTitle) {
      try { await renombrarTitle(L.titulo, L.tituloTitle); } catch (e) {}
    }
  }

  // ---------------------------------------------------------------- 2/3
  console.log('%c2/3  Creando las columnas', 'font-weight:bold;font-size:13px');

  var creadas = 0, saltadas = 0, fallidas = [];
  for (var i = 0; i < LISTAS.length; i++) {
    var L = LISTAS[i];
    if (!ids[L.titulo]) { console.warn('   se omite ' + L.titulo + ' (la lista no existe)'); continue; }

    var ya = await columnasDe(L.titulo);
    var n = 0;
    for (var k = 0; k < L.campos.length; k++) {
      var c = L.campos[k];
      if (ya[c.n]) { saltadas++; continue; }

      var xml = c.xml;
      if (c.lookup) {
        var destino = ids[c.lookup];
        if (!destino) {
          fallidas.push(L.titulo + '.' + c.n + ' (falta la lista ' + c.lookup + ')');
          continue;
        }
        xml = xml.replace('<Field ', '<Field List="{' + destino + '}" ');
      }
      try {
        await crearColumna(L.titulo, xml);
        creadas++; n++;
      } catch (e) {
        fallidas.push(L.titulo + '.' + c.n + ' -> ' + e.message);
      }
    }
    console.log('   ' + L.titulo + ': ' + n + ' nuevas de ' + L.campos.length);
  }

  // ---------------------------------------------------------------- 3/3
  console.log('%c3/3  Resultado', 'font-weight:bold;font-size:13px');
  console.log('   columnas creadas     : ' + creadas);
  console.log('   ya existian          : ' + saltadas);
  if (fallidas.length) {
    console.warn('   con problemas (' + fallidas.length + '):');
    fallidas.forEach(function (f) { console.warn('     - ' + f); });
    console.warn('   Corrige y vuelve a ejecutar: lo ya creado se respeta.');
  } else {
    console.log('%c   Sin errores. Comprueba un par de nombres internos antes de seguir.',
      'color:#2f6b3f;font-weight:bold');
  }
  console.log('%cListo. Siguiente paso: permisos y datos iniciales.',
    'font-weight:bold;font-size:13px');
})();
