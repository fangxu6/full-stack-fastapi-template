import { AppSidebarMenu } from "@/app/navigation/AppSidebarMenu"
import { AppSidebarUserMenu } from "@/app/navigation/AppSidebarUserMenu"
import { getMenuItemsForUser } from "@/app/navigation/menu-config"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { Logo } from "@/shared/components/branding"
import { SidebarAppearance } from "@/shared/components/theme"

export function AppSidebar() {
  const { user: currentUser } = useAuth()
  const items = getMenuItemsForUser(currentUser)

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:items-center group-data-[collapsible=icon]:px-0">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <AppSidebarMenu items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <AppSidebarUserMenu user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}
