"use client"

import { useState } from "react"
import { format } from "date-fns"
import { MoreHorizontal, Trash } from "lucide-react"
import { toast } from "sonner"
import { createClient } from "@/supabase/client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Invoice } from "@/lib/analytics"
import { useRouter } from "next/navigation"

interface InvoiceTableProps {
  invoices: Invoice[]
}

export default function InvoiceTable({ invoices }: InvoiceTableProps) {
  const [isDeleting, setIsDeleting] = useState<string | null>(null)
  const supabase = createClient()
  const router = useRouter()

  const handleDelete = async (id: string) => {
    setIsDeleting(id)
    try {
      const { error } = await supabase.from('invoices').delete().eq('id', id)
      if (error) throw error
      toast.success("Invoice deleted")
      router.refresh()
    } catch (error) {
      toast.error("Failed to delete invoice")
    } finally {
      setIsDeleting(null)
    }
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Date</TableHead>
            <TableHead>Company</TableHead>
            <TableHead>Category</TableHead>
            <TableHead>Amount</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {invoices.length === 0 ? (
             <TableRow>
                <TableCell colSpan={5} className="h-24 text-center">
                  No invoices found.
                </TableCell>
             </TableRow>
          ) : (
            invoices.map((invoice) => (
              <TableRow key={invoice.id}>
                <TableCell>
                  {format(new Date(invoice.date), "MMM d, yyyy")}
                </TableCell>
                <TableCell className="font-medium">{invoice.company_name}</TableCell>
                <TableCell>{invoice.category}</TableCell>
              <TableCell className="text-right font-medium">
                {new Intl.NumberFormat('en-IE', { style: 'currency', currency: invoice.currency || 'EUR' }).format(invoice.amount)}
              </TableCell>
              <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0">
                        <span className="sr-only">Open menu</span>
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem 
                        onClick={() => handleDelete(invoice.id)}
                        className="text-red-600 focus:text-red-600"
                        disabled={isDeleting === invoice.id}
                      >
                        <Trash className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
