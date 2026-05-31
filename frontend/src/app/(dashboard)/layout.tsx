"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { Sidebar } from "@/components/layout/sidebar";
import { ToastProvider } from "@/components/ui/toast";
import { PageLoader } from "@/components/shared/loading";

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return <PageLoader />;
  }

  if (!isAuthenticated) {
    router.replace("/login");
    return <PageLoader />;
  }

  return <>{children}</>;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ToastProvider>
      <AuthGuard>
        <div className="min-h-screen bg-background">
          <Sidebar />
          <main className="lg:me-64 transition-all duration-300 min-h-screen">
            <div className="p-4 lg:p-6 pt-16 lg:pt-6">
              {children}
            </div>
          </main>
        </div>
      </AuthGuard>
    </ToastProvider>
  );
}
