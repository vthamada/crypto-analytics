"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BookOpen,
  History,
  LayoutDashboard,
  Settings,
  Zap,
} from "lucide-react";
import { ThemeToggle } from "./theme-toggle";
import { cn } from "@/lib/utils";
import {
  getAdminSession,
  getStoredAuthToken,
  getStoredWorkspaceId,
  SESSION_STORAGE_EVENT,
  setStoredWorkspaceId,
} from "@/lib/api";
import type { WorkspaceSummary } from "@/lib/types";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/history", label: "Histórico", icon: History },
  { href: "/settings", label: "Configurações", icon: Settings },
  { href: "/help", label: "Ajuda", icon: BookOpen },
];

export function Header() {
  const pathname = usePathname();
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState("");
  const [organizationName, setOrganizationName] = useState("");

  useEffect(() => {
    const syncSession = () => {
      const token = getStoredAuthToken();
      if (!token) {
        setWorkspaces([]);
        setActiveWorkspaceId("");
        setOrganizationName("");
        return;
      }

      void getAdminSession(token)
        .then((session) => {
          setWorkspaces(session.workspaces);
          setActiveWorkspaceId(getStoredWorkspaceId() || session.workspaces[0]?.id || "");
          setOrganizationName(session.organization?.name || "");
        })
        .catch(() => {
          setWorkspaces([]);
          setActiveWorkspaceId("");
          setOrganizationName("");
        });
    };

    syncSession();
    window.addEventListener(SESSION_STORAGE_EVENT, syncSession);
    return () => window.removeEventListener(SESSION_STORAGE_EVENT, syncSession);
  }, []);

  function handleWorkspaceChange(workspaceId: string) {
    setStoredWorkspaceId(workspaceId);
    setActiveWorkspaceId(workspaceId);
    window.location.reload();
  }

  return (
    <header className="sticky top-0 z-50 border-b border-border/70 bg-background/90 backdrop-blur-xl">
      <div className="mx-auto max-w-7xl px-3 py-3 sm:px-4 sm:py-0">
        <div className="flex flex-col gap-3 sm:h-16 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary shadow-sm shadow-primary/20">
                  <Zap className="h-5 w-5 text-primary-foreground" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-base font-bold leading-none tracking-tight sm:text-lg">
                    Crypto Analytics
                  </p>
                  {organizationName ? (
                    <p className="truncate pt-1 text-xs text-muted-foreground">
                      {organizationName}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>
            <div className="sm:hidden">
              <ThemeToggle />
            </div>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            {workspaces.length > 0 ? (
              <select
                data-testid="header-workspace-select"
                value={activeWorkspaceId}
                onChange={(event) => handleWorkspaceChange(event.target.value)}
                className="h-10 min-w-0 rounded-xl border bg-background px-3 text-sm shadow-sm sm:h-9 sm:min-w-[220px]"
              >
                {workspaces.map((workspace) => (
                  <option key={workspace.id} value={workspace.id}>
                    {workspace.name}
                  </option>
                ))}
              </select>
            ) : null}

            <nav className="grid grid-cols-4 gap-1 rounded-2xl border border-border/70 bg-muted/30 p-1 sm:flex sm:items-center sm:gap-1 sm:border-0 sm:bg-transparent sm:p-0">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex min-w-0 items-center justify-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                      isActive
                        ? "bg-primary/12 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground",
                    )}
                    aria-label={item.label}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="hidden lg:inline">{item.label}</span>
                  </Link>
                );
              })}
              <div className="hidden sm:flex sm:items-center sm:pl-1">
                <ThemeToggle />
              </div>
            </nav>
          </div>
        </div>
      </div>
    </header>
  );
}
