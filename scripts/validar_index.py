#!/usr/bin/env python3
"""Valida un index.html del Weekly Fondos antes de publicarlo.

Uso:
    python3 scripts/validar_index.py <index_nuevo> [--publicado index.html] [--instalar]

Con --instalar, si no hay errores copia el archivo nuevo sobre el publicado
(agregando el BOM UTF-8 si el archivo llegó sin él, como pasa con los adjuntos
del chat), listo para hacer el commit.

Compara el archivo que generó la macro Weekly_Master.xlsm contra el que está
publicado en el repo y avisa lo que conviene revisar antes de subirlo.

Código de salida:
    0  sin observaciones
    1  hay advertencias: mostrarlas al usuario y pedir confirmación
    2  hay errores: NO publicar
    3  el archivo es idéntico al publicado: no hay nada que subir
"""
import argparse
import datetime as dt
import re
import sys

CAMPOS = ("tna", "tir", "dur", "vol", "pn", "r7d", "ytd")
TAGS_SIN_FUSIONAR = ('<script src="chart.min.js"></script>', '<script src="data_actual.js"></script>')


def leer(ruta):
    crudo = open(ruta, "rb").read()
    return crudo, crudo.decode("utf-8-sig", errors="replace")


def parsear(texto):
    m = re.search(r'const REPORT_DATE = "(\d{2})/(\d{2})/(\d{4})"', texto)
    fecha = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None
    m = re.search(r"const PATRIMONIO_TOTAL = ([\d.]+|null)", texto)
    total = float(m.group(1)) if m and m.group(1) != "null" else None
    fondos = {}
    m = re.search(r"const FONDOS = \[(.*?)\r?\n\];", texto, flags=re.S)
    if m:
        for linea in m.group(1).splitlines():
            n = re.search(r'\{nombre:"([^"]+)"', linea)
            if not n:
                continue
            datos = {}
            for campo in CAMPOS:
                v = re.search(r"[,{]%s:(null|-?[\d.eE+-]+)[,}]" % campo, linea)
                datos[campo] = None if (not v or v.group(1) == "null") else float(v.group(1))
            fondos[n.group(1)] = datos
    return fecha, total, fondos


def sin_datos(texto):
    """El HTML sin el bloque de datos, para comparar solo el código."""
    t = re.sub(r"const REPORT_DATE.*?const COMENTARIOS_ASSET_CLASS = \[.*?\];", "", texto, flags=re.S)
    return t.replace("\r\n", "\n")


def fmt(d):
    return d.strftime("%d/%m/%Y") if d else "?"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("nuevo")
    ap.add_argument("--publicado", default="index.html")
    ap.add_argument("--instalar", action="store_true", help="si no hay errores, copia el nuevo sobre el publicado")
    a = ap.parse_args()

    crudo_n, txt_n = leer(a.nuevo)
    crudo_p, txt_p = leer(a.publicado)
    if crudo_n.lstrip(b"\xef\xbb\xbf") == crudo_p.lstrip(b"\xef\xbb\xbf"):
        print("SIN CAMBIOS: el archivo es idéntico al publicado. No hay nada que subir.")
        return 3

    errores, avisos, info = [], [], []
    fecha_n, total_n, fondos_n = parsear(txt_n)
    fecha_p, total_p, fondos_p = parsear(txt_p)

    # --- integridad del archivo
    if fecha_n is None:
        errores.append("No se encontró REPORT_DATE con formato DD/MM/AAAA.")
    if not fondos_n:
        errores.append("No se pudo leer ningún fondo del bloque FONDOS.")
    for tag in TAGS_SIN_FUSIONAR:
        if tag in txt_n:
            errores.append("Quedó sin fusionar %s: el archivo no es el HTML autocontenido." % tag)
    BOM = b"\xef\xbb\xbf"
    if not crudo_n.startswith(BOM):
        info.append("El archivo llegó sin BOM UTF-8 (normal en adjuntos del chat); se agrega al instalar.")
    if len(crudo_n) < 0.8 * len(crudo_p):
        errores.append("El archivo pesa %.0f KB contra %.0f KB del publicado: parece incompleto." % (len(crudo_n) / 1024, len(crudo_p) / 1024))
    if total_n is None:
        avisos.append("PATRIMONIO_TOTAL está vacío.")

    # --- fecha de cierre
    hoy = dt.date.today()
    if fecha_n:
        if fecha_n > hoy:
            errores.append("La fecha de cierre %s es futura." % fmt(fecha_n))
        if fecha_p and fecha_n < fecha_p:
            errores.append("La fecha de cierre %s es anterior a la publicada (%s)." % (fmt(fecha_n), fmt(fecha_p)))
        elif fecha_p and fecha_n == fecha_p:
            avisos.append("La fecha de cierre es la misma que la publicada (%s): es una re-corrida de la misma semana." % fmt(fecha_n))
        if (hoy - fecha_n).days > 10:
            avisos.append("La fecha de cierre %s tiene más de 10 días." % fmt(fecha_n))

    # --- código / template
    if sin_datos(txt_n) != sin_datos(txt_p):
        avisos.append("El código del tablero (template) cambió respecto del publicado. Confirmar que el cambio en template.html es intencional.")

    # --- fondos
    nuevos = sorted(set(fondos_n) - set(fondos_p))
    quitados = sorted(set(fondos_p) - set(fondos_n))
    if nuevos:
        avisos.append("Fondos nuevos: " + ", ".join(nuevos))
    if quitados:
        avisos.append("Fondos que ya no están: " + ", ".join(quitados))

    if total_n and total_p:
        var = total_n / total_p - 1
        info.append("Patrimonio total: %s -> %s millones (%+.1f%%)" % ("{:,.0f}".format(total_p), "{:,.0f}".format(total_n), var * 100))
        if abs(var) > 0.10:
            avisos.append("El patrimonio total varió %+.1f%% contra el publicado." % (var * 100))

    misma_semana = bool(fecha_n and fecha_p and fecha_n == fecha_p)
    repetidos = {c: [] for c in ("vol", "pn", "r7d", "ytd")}
    vacios, saltos = [], []
    for nombre, d in fondos_n.items():
        faltan = [c for c in ("pn", "r7d", "ytd") if d[c] is None]
        if faltan:
            vacios.append("%s (%s)" % (nombre, ", ".join(faltan)))
        p = fondos_p.get(nombre)
        if not p:
            continue
        for c in repetidos:
            if d[c] is not None and d[c] != 0 and d[c] == p[c]:
                repetidos[c].append(nombre)
        if d["pn"] and p["pn"] and abs(d["pn"] / p["pn"] - 1) > 0.30:
            saltos.append("%s (%+.0f%%)" % (nombre, (d["pn"] / p["pn"] - 1) * 100))

    if not misma_semana:
        etiquetas = {"vol": "Volatilidad", "pn": "Patrimonio", "r7d": "Rendimiento 7 días", "ytd": "YTD"}
        con_dato = {c: sum(1 for d in fondos_n.values() if d[c] not in (None, 0)) for c in repetidos}
        for c, lista in repetidos.items():
            if not lista:
                continue
            if len(lista) == con_dato[c] and len(lista) > 3:
                avisos.append("%s: los %d fondos con dato repiten exactamente el valor publicado. Revisar si se actualizó en la Tabla." % (etiquetas[c], len(lista)))
            else:
                avisos.append("%s sin cambio contra lo publicado en: %s" % (etiquetas[c], ", ".join(lista)))
    if vacios:
        avisos.append("Datos vacíos: " + "; ".join(vacios))
    if saltos:
        avisos.append("Patrimonio con variación mayor a 30%: " + ", ".join(saltos))

    # --- salida
    print("Cierre publicado: %s | Cierre nuevo: %s | Fondos: %d" % (fmt(fecha_p), fmt(fecha_n), len(fondos_n)))
    for linea in info:
        print(linea)
    if errores:
        print("\nERRORES (no publicar):")
        for e in errores:
            print("  - " + e)
    if avisos:
        print("\nADVERTENCIAS (mostrar al usuario y pedir confirmación):")
        for w in avisos:
            print("  - " + w)
    if not errores and not avisos:
        print("\nOK: sin observaciones.")
    if a.instalar and not errores:
        with open(a.publicado, "wb") as f:
            f.write(crudo_n if crudo_n.startswith(BOM) else BOM + crudo_n)
        print("\nInstalado en %s. Falta commit y push." % a.publicado)
    return 2 if errores else (1 if avisos else 0)


if __name__ == "__main__":
    sys.exit(main())
