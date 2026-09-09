/**
 * Exportación estándar de reportes (constitución §Principio XII): toda pantalla
 * de reporte ofrece CSV, Excel y PDF. CSV y Excel salen del mismo arreglo de
 * filas; PDF abre una vista imprimible. Sin librerías externas (CSP del proyecto).
 *
 *   filas: string[][]  — la primera fila es el encabezado.
 */

function descargar(blob, nombre) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = nombre
  a.click()
  URL.revokeObjectURL(url)
}

const escaparCsv = (v) => {
  const s = v == null ? '' : String(v)
  return /[",\n;]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

export function exportarCSV(nombreBase, filas) {
  const texto = filas.map((f) => f.map(escaparCsv).join(',')).join('\r\n')
  // BOM para que Excel/LibreOffice detecten UTF-8
  descargar(new Blob(['﻿' + texto], { type: 'text/csv;charset=utf-8;' }), `${nombreBase}.csv`)
}

const escaparHtml = (v) =>
  String(v ?? '').replace(
    /[&<>"]/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c],
  )

/** Excel lee una tabla HTML servida como .xls sin problemas y sin dependencias. */
export function exportarExcel(nombreBase, filas) {
  const [cab, ...cuerpo] = filas
  const thead = `<tr>${(cab || []).map((c) => `<th>${escaparHtml(c)}</th>`).join('')}</tr>`
  const tbody = cuerpo
    .map((f) => `<tr>${f.map((c) => `<td>${escaparHtml(c)}</td>`).join('')}</tr>`)
    .join('')
  const html =
    `<html><head><meta charset="utf-8"></head><body>` +
    `<table border="1">${thead}${tbody}</table></body></html>`
  descargar(
    new Blob(['﻿' + html], { type: 'application/vnd.ms-excel;charset=utf-8;' }),
    `${nombreBase}.xls`,
  )
}

/** PDF = ventana imprimible (el usuario elige "Guardar como PDF" en el diálogo). */
export function exportarPDF(titulo, filas) {
  const [cab, ...cuerpo] = filas
  const thead = `<tr>${(cab || []).map((c) => `<th>${escaparHtml(c)}</th>`).join('')}</tr>`
  const tbody = cuerpo
    .map((f) => `<tr>${f.map((c) => `<td>${escaparHtml(c)}</td>`).join('')}</tr>`)
    .join('')
  const w = window.open('', '_blank', 'noopener,width=1024,height=768')
  if (!w) return
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>${escaparHtml(titulo)}</title>
    <style>
      body{font:12px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#0f172a;padding:24px}
      h1{font-size:16px;margin:0 0 4px}
      .meta{color:#64748b;font-size:11px;margin-bottom:16px}
      table{border-collapse:collapse;width:100%}
      th,td{border:1px solid #cbd5e1;padding:6px 8px;text-align:left}
      thead{background:#0a3632;color:#fff}
      tbody tr:nth-child(even){background:#f1f5f9}
      @media print{.noprint{display:none}}
    </style></head><body>
    <h1>${escaparHtml(titulo)}</h1>
    <div class="meta">Generado el ${new Date().toLocaleString('es-EC')} · ${cuerpo.length} registros</div>
    <button class="noprint" onclick="window.print()" style="margin-bottom:12px;padding:6px 14px;cursor:pointer">Imprimir / Guardar PDF</button>
    <table><thead>${thead}</thead><tbody>${tbody}</tbody></table>
    <scr` + `ipt>window.onload=function(){setTimeout(function(){window.print()},250)}</scr` + `ipt>
    </body></html>`)
  w.document.close()
}

/**
 * Menú de 3 formatos. `filas` es el arreglo (encabezado + datos). Para reportes
 * muy extensos (`filas.length` > `umbralCsvUnico`, por defecto 5000) sólo CSV.
 */
export function opcionesExportacion(titulo, nombreBase, filas, { umbralCsvUnico = 5000 } = {}) {
  const extenso = filas.length > umbralCsvUnico
  const base = [{ id: 'csv', label: 'CSV', fn: () => exportarCSV(nombreBase, filas) }]
  if (extenso) return base
  return [
    { id: 'pdf', label: 'PDF', fn: () => exportarPDF(titulo, filas) },
    { id: 'excel', label: 'Excel (.xls)', fn: () => exportarExcel(nombreBase, filas) },
    ...base,
  ]
}
