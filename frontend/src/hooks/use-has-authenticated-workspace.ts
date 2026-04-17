"use client";

import { useEffect, useState } from "react";

import {
  getStoredAuthToken,
  getStoredWorkspaceId,
  SESSION_STORAGE_EVENT,
} from "@/lib/api";


function readAuthenticatedWorkspaceState(): boolean {
  return Boolean(getStoredAuthToken() && getStoredWorkspaceId());
}


export function useHasAuthenticatedWorkspace() {
  const [hasAuthenticatedWorkspace, setHasAuthenticatedWorkspace] = useState<boolean | null>(null);

  useEffect(() => {
    const syncState = () => {
      setHasAuthenticatedWorkspace(readAuthenticatedWorkspaceState());
    };

    syncState();
    window.addEventListener(SESSION_STORAGE_EVENT, syncState);
    return () => window.removeEventListener(SESSION_STORAGE_EVENT, syncState);
  }, []);

  return hasAuthenticatedWorkspace;
}
