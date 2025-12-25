import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { DollarSign, BarChart3, Building2, Tag } from "lucide-react"

interface SummaryCardsProps {
  totalSpending: number
  distinctCompanies: number
  invoiceCount: number
  mostCommonCategory: string
}

export default function SummaryCards({ 
  totalSpending, 
  distinctCompanies, 
  invoiceCount, 
  mostCommonCategory 
}: SummaryCardsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Spending</CardTitle>
          <DollarSign className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">€{totalSpending.toFixed(2)}</div>
          <p className="text-xs text-muted-foreground">
             Total amount from all invoices
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Companies</CardTitle>
          <Building2 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{distinctCompanies}</div>
          <p className="text-xs text-muted-foreground">
            Distinct vendors
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Top Category</CardTitle>
          <Tag className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold capitalize">{mostCommonCategory}</div>
          <p className="text-xs text-muted-foreground">
            Most frequent expense
          </p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Total Invoices</CardTitle>
          <BarChart3 className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{invoiceCount}</div>
          <p className="text-xs text-muted-foreground">
            +0% from last month
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
