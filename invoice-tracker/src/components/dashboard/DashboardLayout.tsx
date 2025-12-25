"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { BarChart3, CloudUpload, FileText, Home, LogOut, Settings } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/components/providers/AuthProvider"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { ModeToggle } from "@/components/ui/mode-toggle"

interface DashboardLayoutProps {
  children: React.ReactNode
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname()
  const { user, signOut } = useAuth()

  const sidebarItems = [
    { href: "/dashboard", icon: Home, label: "Overview" },
    { href: "/dashboard/analytics", icon: BarChart3, label: "Analytics" }, // Future placeholder
    { href: "/dashboard/invoices", icon: FileText, label: "Invoices" }, // Future placeholder
    { href: "/dashboard/upload", icon: CloudUpload, label: "Upload" }, // Explicit upload page if needed
  ]

  // Filter mainly for the single page dashboard requirement initially, but structure allows expansion.
  // For this MVp, everything might be on /dashboard, but I'll add a few links.
  
  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      {/* Sidebar */}
      <aside className="w-full md:w-64 bg-slate-900 text-white flex-shrink-0">
        <div className="p-6">
          <h1 className="text-2xl font-bold tracking-tight text-blue-400">InvoiceTracker</h1>
        </div>
        <nav className="px-4 space-y-2">
          <Link href="/dashboard">
             <Button 
                variant="ghost" 
                className={cn("w-full justify-start text-slate-300 hover:text-white hover:bg-slate-800", pathname === "/dashboard" && "bg-slate-800 text-white")}
             >
                <Home className="mr-2 h-4 w-4" />
                Dashboard
             </Button>
          </Link>
          <div className="pt-4 pb-2 px-2 text-xs text-slate-500 font-semibold uppercase tracking-wider">
             User
          </div>
           <Button 
              variant="ghost" 
              className="w-full justify-start text-red-400 hover:text-red-300 hover:bg-slate-800"
              onClick={() => signOut()}
           >
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
           </Button>
        </nav>
        
        <div className="p-4 mt-auto absolute bottom-0 w-64">
           {user && (
             <div className="flex items-center gap-3 p-2 rounded-lg bg-slate-800/50">
               <Avatar className="h-8 w-8">
                 <AvatarImage src={user.user_metadata?.avatar_url} />
                 <AvatarFallback>{user.email?.charAt(0).toUpperCase()}</AvatarFallback>
               </Avatar>
               <div className="overflow-hidden">
                 <p className="text-sm font-medium truncate text-slate-200">{user.email}</p>
               </div>
             </div>
           )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 bg-slate-50 dark:bg-slate-900">
        <header className="h-16 border-b bg-white dark:bg-slate-950 flex items-center px-6 sticky top-0 z-10 justify-between">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-200">
             {pathname === '/dashboard' ? 'Overview' : pathname.split('/').pop()?.replace(/^\w/, c => c.toUpperCase())}
          </h2>
          <ModeToggle />
        </header>
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
