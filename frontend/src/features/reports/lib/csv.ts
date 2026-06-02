import Papa from 'papaparse'

export function downloadCSV(rows: Record<string, string | number | null | undefined>[], filename: string): void {
  const csv = Papa.unparse(rows)
  const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function csvFilename(report: string, dateFrom: string, dateTo: string): string {
  return `${report}_${dateFrom}_${dateTo}.csv`
}
