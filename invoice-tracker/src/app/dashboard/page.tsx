import { Suspense } from "react"
import { createClient } from "@/supabase/server"
import {
  getDistinctCompanies,
  getMostCommonCategory,
  getSpendingByCategory,
  getSpendingByPeriod,
  getTopCompanies,
  getTotalSpending,
  Invoice
} from "@/lib/analytics"
import UploadInvoice from "@/components/dashboard/UploadInvoice"
import SummaryCards from "@/components/dashboard/SummaryCards"
import SpendingChart from "@/components/dashboard/charts/SpendingChart"
import CategoryChart from "@/components/dashboard/charts/CategoryChart"
import CompanyDistribution from "@/components/dashboard/charts/CompanyDistribution"
import InvoiceTable from "@/components/dashboard/InvoiceTable"
import { Separator } from "@/components/ui/separator"

export default async function DashboardPage() {
  const supabase = await createClient()
  
  const { data: invoicesData, error } = await supabase
    .from('invoices')
    .select('*')
    .order('date', { ascending: false })

  if (error) {
    console.error("Error fetching invoices:", error)
  }

  const invoices = (invoicesData || []) as Invoice[]

  // Calculate Analytics
  const totalSpending = getTotalSpending(invoices)
  const distinctCompanies = getDistinctCompanies(invoices)
  const mostCommonCategory = getMostCommonCategory(invoices)
  
  const spendingOverTime = getSpendingByPeriod(invoices)
  const spendingByCategory = getSpendingByCategory(invoices)
  const topCompanies = getTopCompanies(invoices)

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Upload and manage your invoices here.
        </p>
      </div>
      
      <SummaryCards 
         totalSpending={totalSpending}
         distinctCompanies={distinctCompanies}
         invoiceCount={invoices.length}
         mostCommonCategory={mostCommonCategory}
      />

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-7">
        <div className="col-span-4 lg:col-span-3 space-y-4">
          <UploadInvoice />
           <CompanyDistribution data={topCompanies} />
        </div>
        <div className="col-span-4 lg:col-span-4 space-y-4">
          <SpendingChart data={spendingOverTime} />
          <CategoryChart data={spendingByCategory} />
        </div>
      </div>
      
      <Separator className="my-6" />
      
      <div className="space-y-4">
         <h2 className="text-xl font-semibold">Recent Invoices</h2>
         <InvoiceTable invoices={invoices} />
      </div>
    </div>
  )
}
