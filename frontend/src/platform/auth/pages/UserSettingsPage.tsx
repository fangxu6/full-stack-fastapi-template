import ChangePasswordForm from "@/platform/auth/components/ChangePasswordForm"
import DeleteAccountDialog from "@/platform/auth/components/DeleteAccountDialog"
import UserProfileCard from "@/platform/auth/components/UserProfileCard"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/shared/components/ui/tabs"

const tabsConfig = [
  { value: "my-profile", title: "My profile", component: UserProfileCard },
  { value: "password", title: "Password", component: ChangePasswordForm },
  {
    value: "danger-zone",
    title: "Danger zone",
    component: DeleteAccountDialog,
  },
]

export function UserSettingsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">User Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences
        </p>
      </div>

      <Tabs defaultValue="my-profile">
        <TabsList>
          {tabsConfig.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.title}
            </TabsTrigger>
          ))}
        </TabsList>
        {tabsConfig.map((tab) => (
          <TabsContent key={tab.value} value={tab.value}>
            <tab.component />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  )
}
