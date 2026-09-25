#!/usr/bin/env python3
"""Extrae el esquema completo de Deploy-Contratos.ps1 a JSON."""
import json
import re
from pathlib import Path

RAIZ = Path("/home/user/CONTRATOS")
DEPLOY = RAIZ / "sharepoint" / "Deploy-Contratos.ps1"
texto = DEPLOY.read_text(encoding="utf-8")

# Catalogos declarados como variables al inicio ($TiposContrato = @( ... )).
# El cierre es un ')' solo en su linea: los valores pueden traer parentesis
# dentro ('Confidencialidad (NDA)'), asi que no sirve cortar en el primer ')'.
catalogos = {}
for m in re.finditer(r"^\$(\w+)\s*=\s*@\(\s*$", texto, re.MULTILINE):
    nombre = m.group(1)
    resto = texto[m.end():]
    fin = re.search(r"^\)\s*$", resto, re.MULTILINE)
    cuerpo = resto[: fin.start()] if fin else resto
    vals = re.findall(r"'([^']*)'", cuerpo)
    if vals:
        catalogos[nombre] = vals

# Mapa variable-de-lista -> nombre de lista, para resolver LookupList
var_a_lista = {}
for m in re.finditer(r"\$(\w+)\s*=\s*New-ListaSiNoExiste\s+-Title\s+'([^']+)'", texto):
    var_a_lista[m.group(1)] = m.group(2)

# Bloques por lista
partes = re.split(r"\$(\w+)\s*=\s*New-ListaSiNoExiste\s+-Title\s+'([^']+)'", texto)
# partes = [pre, var1, nombre1, cuerpo1, var2, nombre2, cuerpo2, ...]

listas = []
for i in range(1, len(partes), 3):
    var, nombre, cuerpo = partes[i], partes[i + 1], partes[i + 2]

    # Recorta el cuerpo en el siguiente Add-Vista o fin de bloque de columnas
    corte = cuerpo.find(") | ForEach-Object { Add-Columna")
    cuerpo_cols = cuerpo[:corte] if corte > 0 else cuerpo

    es_biblioteca = "-Url 'DocumentosContratos'" in cuerpo[:200]

    # Renombrado de Title
    ren = re.search(r"Set-PnPField -List '[^']+' -Identity 'Title' -Values @\{ Title = '([^']+)'", cuerpo)
    title_display = ren.group(1) if ren else None
    title_required = None
    if ren:
        req = re.search(r"Identity 'Title'.*?Required = \$(\w+)", cuerpo, re.S)
        title_required = (req.group(1) == "true") if req else None

    columnas = []
    for linea in cuerpo_cols.splitlines():
        linea = linea.strip()
        if not linea.startswith("@{") or "Name =" not in linea:
            continue
        col = {}
        col["name"] = re.search(r"Name\s*=\s*'([^']+)'", linea).group(1)
        d = re.search(r"Display\s*=\s*'([^']+)'", linea)
        col["display"] = d.group(1) if d else col["name"]
        t = re.search(r"Type\s*=\s*'([^']+)'", linea)
        col["type"] = t.group(1) if t else "Text"

        # Choices = (@('Todos') + $TiposContrato)  -> literales seguidos del catalogo
        ch_comp = re.search(r"Choices\s*=\s*\(@\(([^)]*)\)\s*\+\s*\$(\w+)\)", linea)
        ch = re.search(r"Choices\s*=\s*\$(\w+)", linea)
        ch2 = re.search(r"Choices\s*=\s*@\(([^)]*)\)", linea)
        if ch_comp:
            col["choices"] = (re.findall(r"'([^']*)'", ch_comp.group(1))
                              + catalogos.get(ch_comp.group(2), []))
            col["choices_from"] = f"'Todos' + ${ch_comp.group(2)}"
        elif ch:
            col["choices"] = catalogos.get(ch.group(1), [])
            col["choices_from"] = ch.group(1)
        elif ch2:
            col["choices"] = re.findall(r"'([^']*)'", ch2.group(1))

        lk = re.search(r"LookupList\s*=\s*\$(\w+)\.Id", linea)
        if lk:
            col["lookup"] = var_a_lista.get(lk.group(1), lk.group(1))
        elif re.search(r"LookupList\s*=\s*\$null", linea):
            # Autorreferencia: el script la resuelve despues, apuntando a su propia lista.
            col["lookup"] = nombre
            col["autorreferencia"] = True
        lf = re.search(r"LookupField\s*=\s*'([^']+)'", linea)
        if lf:
            col["lookup_field"] = lf.group(1)

        for clave, patron, conv in [
            ("max_length", r"MaxLength\s*=\s*(\d+)", int),
            ("decimals", r"Decimals\s*=\s*(\d+)", int),
            ("num_lines", r"NumLines\s*=\s*(\d+)", int),
        ]:
            mm = re.search(patron, linea)
            if mm:
                col[clave] = conv(mm.group(1))

        if re.search(r"Required\s*=\s*\$true", linea):
            col["required"] = True
        if re.search(r"Indexed\s*=\s*\$true", linea):
            col["indexed"] = True
        if re.search(r"DateOnly\s*=\s*\$true", linea):
            col["date_only"] = True
        dm = re.search(r"Default\s*=\s*'([^']*)'", linea)
        if dm:
            col["default"] = dm.group(1)
        else:
            dn = re.search(r"Default\s*=\s*(\d+)", linea)
            if dn:
                col["default"] = dn.group(1)

        columnas.append(col)

    listas.append({
        "nombre": nombre,
        "es_biblioteca": es_biblioteca,
        "title_display": title_display,
        "title_required": title_required,
        "columnas": columnas,
    })

print(json.dumps({"listas": listas, "catalogos": catalogos}, ensure_ascii=False, indent=1))
