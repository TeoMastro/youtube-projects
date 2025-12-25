import { startOfMonth, subMonths, format, parseISO, isSameMonth } from 'date-fns'

export type Invoice = {
  id: string
  company_name: string
  amount: number
  currency: string
  date: string
  category: string | null
  created_at: string
}

export function getTotalSpending(invoices: Invoice[]): number {
  return invoices.reduce((acc, curr) => acc + Number(curr.amount), 0)
}

export function getDistinctCompanies(invoices: Invoice[]): number {
  const companies = new Set(invoices.map(i => i.company_name.toLowerCase()))
  return companies.size
}

export function getMostCommonCategory(invoices: Invoice[]): string {
    if (invoices.length === 0) return "N/A"
    
    const counts: Record<string, number> = {}
    invoices.forEach(i => {
        const cat = i.category || "Uncategorized"
        counts[cat] = (counts[cat] || 0) + 1
    })
    
    return Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0]
}

export function getSpendingByPeriod(invoices: Invoice[], days: number = 30) {
    // Basic implementation grouping by date
    // specific logic can be expanded
    const grouped: Record<string, number> = {}
    
    invoices.forEach(inv => {
        const date = inv.date.split('T')[0] // simplified
        grouped[date] = (grouped[date] || 0) + Number(inv.amount)
    })
    
    return Object.entries(grouped).map(([date, amount]) => ({
        date,
        amount
    })).sort((a, b) => a.date.localeCompare(b.date))
}

export function getSpendingByCategory(invoices: Invoice[]) {
    const grouped: Record<string, number> = {}
    
    invoices.forEach(inv => {
        const cat = inv.category || "Uncategorized"
        grouped[cat] = (grouped[cat] || 0) + Number(inv.amount)
    })
    
    return Object.entries(grouped)
        .map(([category, amount]) => ({ category, amount }))
        .sort((a, b) => b.amount - a.amount)
}

export function getTopCompanies(invoices: Invoice[], limit: number = 5) {
     const grouped: Record<string, number> = {}
    
    invoices.forEach(inv => {
        const comp = inv.company_name
        grouped[comp] = (grouped[comp] || 0) + Number(inv.amount)
    })
    
    return Object.entries(grouped)
        .map(([company, amount]) => ({ company, amount }))
        .sort((a, b) => b.amount - a.amount)
        .slice(0, limit)
}

export function getMonthlyComparison(invoices: Invoice[]) {
    const currentMonth = new Date()
    const lastMonth = subMonths(currentMonth, 1)
    
    const currentMonthTotal = invoices
        .filter(i => isSameMonth(parseISO(i.date), currentMonth))
        .reduce((acc, curr) => acc + Number(curr.amount), 0)
        
    const lastMonthTotal = invoices
        .filter(i => isSameMonth(parseISO(i.date), lastMonth))
        .reduce((acc, curr) => acc + Number(curr.amount), 0)
        
    return [
        { name: format(lastMonth, 'MMM'), amount: lastMonthTotal },
        { name: format(currentMonth, 'MMM'), amount: currentMonthTotal },
    ]
}
