"use client";

import { ReactNode } from "react";
import BusinessShell from "@/components/BusinessShell";
import { useRequireRole } from "@/lib/auth";
import { Spinner } from "@/components/ui";

export default function BusinessLayout({ children }: { children: ReactNode }) {
  const { user, loading } = useRequireRole("business");
  if (loading || !user) return <Spinner />;
  return <BusinessShell>{children}</BusinessShell>;
}
