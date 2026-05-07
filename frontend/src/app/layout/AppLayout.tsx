import { Outlet } from "@tanstack/react-router"

import { AppFooter } from "@/app/layout/AppFooter"
import { AppHeader } from "@/app/layout/AppHeader"
import { AppSidebar } from "@/app/navigation/AppSidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export function AppLayout() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <AppHeader />
        <main className="flex-1 p-6 md:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
        <AppFooter />
      </SidebarInset>
    </SidebarProvider>
  )
}
