import { redirect } from "@tanstack/react-router";

import { UsersService } from "@/client";
import { isLoggedIn } from "@/hooks/useAuth";
import { canAccessAdmin } from "@/shared/permissions";

export async function requireLogin() {
  if (!isLoggedIn()) {
    throw redirect({
      to: "/login",
    });
  }
}

export async function requireSuperuser() {
  const user = await UsersService.readUserMe();
  if (!canAccessAdmin(user)) {
    throw redirect({
      to: "/",
    });
  }
}
