"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Shield,
  Receipt,
  DollarSign,
  CreditCard,
  Scale,
  ClipboardList,
  Users,
  FileText,
  LogOut,
  Menu,
  X,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/lib/auth-store";

interface NavItem {
  href: string;
  label: string;
  icon: React.ReactNode;
}

const navItems: NavItem[] = [
  { href: "/", label: "لوحة التحكم", icon: <LayoutDashboard className="h-5 w-5" /> },
  { href: "/custodies", label: "العهد", icon: <Shield className="h-5 w-5" /> },
  { href: "/expenses", label: "المصروفات", icon: <Receipt className="h-5 w-5" /> },
  { href: "/entitlements", label: "المستحقات", icon: <DollarSign className="h-5 w-5" /> },
  { href: "/payments", label: "الدفعات", icon: <CreditCard className="h-5 w-5" /> },
  { href: "/settlements", label: "التسويات", icon: <Scale className="h-5 w-5" /> },
  { href: "/work-records", label: "سجلات العمل", icon: <ClipboardList className="h-5 w-5" /> },
  { href: "/parties", label: "الأطراف", icon: <Users className="h-5 w-5" /> },
  { href: "/reports", label: "التقارير", icon: <FileText className="h-5 w-5" /> },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, user } = useAuthStore();
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/";
    return pathname.startsWith(href);
  };

  // FIX: Use router.push for navigation instead of window.location.href
  const handleLogout = () => {
    logout();
    // AuthGuard in layout will detect isAuthenticated=false and redirect
    // But we also explicitly navigate to be safe
    router.push("/login");
  };

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-border">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-lg shrink-0">
          F
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <h1 className="font-bold text-sm truncate">FFCES</h1>
            <p className="text-xs text-muted-foreground truncate">نظام إدارة العهد المالية</p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMobileOpen(false)}
            className={cn(
              "sidebar-item",
              isActive(item.href) && "active"
            )}
            title={collapsed ? item.label : undefined}
          >
            {item.icon}
            {!collapsed && <span>{item.label}</span>}
          </Link>
        ))}
      </nav>

      {/* User Section */}
      {!collapsed && (
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-muted/50">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-primary-foreground text-sm font-semibold shrink-0">
              {user?.full_name?.charAt(0) || "م"}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium truncate">{user?.full_name || "مستخدم"}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="sidebar-item w-full mt-1 text-destructive hover:bg-red-50 hover:text-red-700 cursor-pointer"
          >
            <LogOut className="h-5 w-5" />
            <span>تسجيل الخروج</span>
          </button>
        </div>
      )}

      {collapsed && (
        <div className="border-t border-border p-3">
          <button
            onClick={handleLogout}
            className="sidebar-item w-full text-destructive hover:bg-red-50 hover:text-red-700 justify-center cursor-pointer"
            title="تسجيل الخروج"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      )}
    </div>
  );

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 end-4 z-40 lg:hidden flex h-10 w-10 items-center justify-center rounded-lg bg-card border border-border shadow-sm cursor-pointer"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed top-0 end-0 z-50 h-full w-72 bg-card border-s border-border shadow-xl transition-transform duration-300 lg:hidden",
          mobileOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute top-4 start-4 flex h-8 w-8 items-center justify-center rounded-lg hover:bg-muted cursor-pointer"
        >
          <X className="h-5 w-5" />
        </button>
        <div className="pt-14">{sidebarContent}</div>
      </aside>

      {/* Desktop sidebar */}
      <aside
        className={cn(
          "hidden lg:fixed lg:top-0 lg:end-0 lg:z-30 lg:h-full bg-card border-s border-border shadow-sm transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {sidebarContent}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -start-3 top-20 flex h-6 w-6 items-center justify-center rounded-full bg-card border border-border shadow-sm hover:bg-muted cursor-pointer"
        >
          <ChevronLeft
            className={cn(
              "h-3.5 w-3.5 transition-transform",
              collapsed && "rotate-180"
            )}
          />
        </button>
      </aside>
    </>
  );
}
