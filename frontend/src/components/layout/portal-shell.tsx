"use client";

import { LogOut, Menu, User as UserIcon, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { logout } from "@/features/authentication/api";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { Logo } from "./logo";
import { adminNav, type NavItem, studentNav } from "./nav";

function isActive(pathname: string, href: string, root: string) {
  return href === root ? pathname === root : pathname === href || pathname.startsWith(`${href}/`);
}

function Sidebar({
  items,
  root,
  portal,
  onNavigate,
}: {
  items: NavItem[];
  root: string;
  portal: "student" | "admin";
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <div className="bg-navy text-navy-foreground flex h-full flex-col">
      <div className="flex h-16 items-center px-5">
        <Logo href={root} tone="light" suffix={portal === "admin" ? "Admin" : undefined} />
      </div>
      <nav
        className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2"
        aria-label={portal === "admin" ? "Admin" : "Student"}
      >
        {items.map(({ href, label, icon: Icon, planned }) => {
          const active = isActive(pathname, href, root);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                active ? "bg-white/10 font-medium text-white" : "hover:bg-white/5 hover:text-white",
              )}
            >
              <Icon className={cn("size-4 shrink-0", active ? "text-primary" : "opacity-70")} aria-hidden />
              <span className="flex-1 truncate">{label}</span>
              {planned && (
                <span className="text-navy-foreground/70 rounded bg-white/5 px-1.5 py-0.5 text-[10px] tracking-wide uppercase">
                  Soon
                </span>
              )}
              {active && <span className="bg-brand-gradient h-5 w-1 rounded-full" aria-hidden />}
            </Link>
          );
        })}
      </nav>
      <div className="text-navy-foreground/60 border-t border-white/5 p-4 text-xs">
        {portal === "admin" ? "Super Admin Portal" : "Student Portal"} · Phase 0
      </div>
    </div>
  );
}

function UserMenu({ portal }: { portal: "student" | "admin" }) {
  const user = useAuthStore((s) => s.user);
  const router = useRouter();
  const name = user?.display_name || user?.email || "";
  const initials = name
    .split(/[\s@.]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");

  async function signOut() {
    await logout().catch(() => undefined);
    router.replace(portal === "admin" ? "/admin/login" : "/login");
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className="hover:bg-muted flex items-center gap-2.5 rounded-lg p-1 pr-2"
        aria-label="Account menu"
      >
        <span className="bg-brand-gradient flex size-8 items-center justify-center rounded-full text-xs font-semibold text-white">
          {initials || "?"}
        </span>
        <span className="hidden max-w-40 truncate text-sm font-medium sm:block">{name}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>{user?.email}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {portal === "student" && (
          <DropdownMenuItem onSelect={() => router.push("/profile")}>
            <UserIcon /> Profile & settings
          </DropdownMenuItem>
        )}
        <DropdownMenuItem onSelect={signOut}>
          <LogOut /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function PortalShell({ portal, children }: { portal: "student" | "admin"; children: React.ReactNode }) {
  const items = portal === "admin" ? adminNav : studentNav;
  const root = portal === "admin" ? "/admin" : "/dashboard";
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const current = items.find((i) => isActive(pathname, i.href, root));

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[16.5rem_1fr]">
      <aside className="sticky top-0 hidden h-screen lg:block">
        <Sidebar items={items} root={root} portal={portal} />
      </aside>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <button className="bg-navy/50 absolute inset-0" onClick={() => setOpen(false)} aria-label="Close menu" />
          <div className="relative h-full w-72 shadow-2xl">
            <Sidebar items={items} root={root} portal={portal} onNavigate={() => setOpen(false)} />
            <button
              onClick={() => setOpen(false)}
              className="absolute top-4 right-3 rounded-md p-1.5 text-white hover:bg-white/10"
              aria-label="Close menu"
            >
              <X className="size-5" />
            </button>
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-col">
        <header className="bg-card/80 sticky top-0 z-30 flex h-16 items-center gap-3 border-b px-4 backdrop-blur sm:px-6">
          <button
            className="hover:bg-muted rounded-md p-2 lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="size-5" />
          </button>
          <p className="font-medium">{current?.label}</p>
          <div className="ml-auto">
            <UserMenu portal={portal} />
          </div>
        </header>
        <main className="mx-auto w-full max-w-6xl flex-1 p-4 sm:p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-muted-foreground mt-1 text-sm">{description}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}
