"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
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
    <header className="sticky top-0 z-50 border-b bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
            <Zap className="h-5 w-5 text-primary-foreground" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight">Crypto Analytics</span>
            {organizationName ? (
              <p className="hidden text-xs text-muted-foreground sm:block">{organizationName}</p>
            ) : null}
          </div>
        </div>

        <nav className="flex items-center gap-1">
          {workspaces.length > 0 ? (
            <select
              data-testid="header-workspace-select"
              value={activeWorkspaceId}
              onChange={(event) => handleWorkspaceChange(event.target.value)}
              className="mr-2 h-9 rounded-lg border bg-background px-3 text-sm"
            >
              {workspaces.map((workspace) => (
                <option key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </option>
              ))}
            </select>
          ) : null}
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )}
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{item.label}</span>
              </Link>
            );
          })}
          <div className="ml-2">
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
}
