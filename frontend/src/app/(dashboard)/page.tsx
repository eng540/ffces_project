"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/shared/loading";
import { formatCurrency } from "@/lib/utils";
import type { DashboardStats, OverdueCustodyAlert } from "@/types";
import {
  Shield,
  ShieldAlert,
  Receipt,
  CreditCard,
  Clock,
  Users,
  FolderOpen,
  AlertTriangle,
  Plus,
  TrendingUp,
  ArrowLeft,
} from "lucide-react";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [alerts, setAlerts] = useState<OverdueCustodyAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { addToast } = useToast();

  const fetchDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const [statsData, alertsData] = await Promise.all([
        api.get<DashboardStats>("/api/v1/dashboard/stats"),
        api.get<OverdueCustodyAlert[]>("/api/v1/dashboard/overdue-alerts").catch(() => []),
      ]);
      setStats(statsData);
      // Handle both paginated and direct array responses
      if (Array.isArray(alertsData)) {
        setAlerts(alertsData);
      } else if (alertsData && typeof alertsData === "object" && "items" in alertsData) {
        setAlerts((alertsData as any).items || []);
      } else {
        setAlerts([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل تحميل البيانات");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  if (loading) return <PageLoader />;

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <AlertTriangle className="h-12 w-12 text-destructive" />
        <p className="text-destructive font-medium">{error}</p>
        <Button onClick={fetchDashboard}>إعادة المحاولة</Button>
      </div>
    );
  }

  const statCards = stats
    ? [
        {
          label: "إجمالي العهد",
          value: stats.total_custodies,
          icon: <Shield className="h-5 w-5" />,
          color: "text-blue-600",
          bg: "bg-blue-50",
        },
        {
          label: "العهد المفتوحة",
          value: stats.open_custodies,
          icon: <ShieldAlert className="h-5 w-5" />,
          color: "text-amber-600",
          bg: "bg-amber-50",
        },
        {
          label: "العهد المتأخرة",
          value: stats.overdue_custodies,
          icon: <AlertTriangle className="h-5 w-5" />,
          color: "text-red-600",
          bg: "bg-red-50",
        },
        {
          label: "مصروفات اليوم",
          value: stats.todays_expenses,
          icon: <Receipt className="h-5 w-5" />,
          color: "text-green-600",
          bg: "bg-green-50",
          isCurrency: true,
        },
        {
          label: "دفعات اليوم",
          value: stats.todays_payments,
          icon: <CreditCard className="h-5 w-5" />,
          color: "text-purple-600",
          bg: "bg-purple-50",
          isCurrency: true,
        },
        {
          label: "بانتظار الموافقة",
          value: stats.pending_approvals,
          icon: <Clock className="h-5 w-5" />,
          color: "text-orange-600",
          bg: "bg-orange-50",
        },
        {
          label: "إجمالي الأطراف",
          value: stats.total_parties,
          icon: <Users className="h-5 w-5" />,
          color: "text-teal-600",
          bg: "bg-teal-50",
        },
        {
          label: "المشاريع النشطة",
          value: stats.active_projects,
          icon: <FolderOpen className="h-5 w-5" />,
          color: "text-indigo-600",
          bg: "bg-indigo-50",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">لوحة التحكم</h1>
          <p className="page-description">نظرة عامة على العمليات المالية الميدانية</p>
        </div>
        <div className="flex gap-2">
          <Link href="/custodies?action=create">
            <Button size="sm">
              <Plus className="h-4 w-4" />
              عهدة جديدة
            </Button>
          </Link>
          <Link href="/expenses?action=create">
            <Button size="sm" variant="outline">
              <Plus className="h-4 w-4" />
              مصروف جديد
            </Button>
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card) => (
          <Card key={card.label} className="stat-card">
            <div className="flex items-center justify-between">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${card.bg} ${card.color}`}>
                {card.icon}
              </div>
              {card.isCurrency ? (
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              ) : null}
            </div>
            <div className="mt-3">
              <p className="text-2xl font-bold text-foreground">
                {card.isCurrency ? formatCurrency(card.value) : card.value.toLocaleString("ar-SA")}
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">{card.label}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Alerts Section */}
      {alerts.length > 0 && (
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <h2 className="text-lg font-semibold text-red-800">
                تنبيهات العهد المتأخرة ({alerts.length})
              </h2>
            </div>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {alerts.map((alert) => (
                <div
                  key={alert.custody_id}
                  className="flex items-center justify-between p-3 rounded-lg bg-white border border-red-100"
                >
                  <div className="space-y-1">
                    <p className="font-medium text-sm">{alert.description}</p>
                    <p className="text-xs text-muted-foreground">
                      الحامل: {alert.holder_name} • المبلغ: {formatCurrency(alert.remaining_amount)}
                    </p>
                  </div>
                  <div className="text-start shrink-0">
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-600 bg-red-100 px-2 py-1 rounded-full">
                      {alert.days_overdue} يوم متأخر
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4">
              <Link href="/custodies?status=overdue">
                <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50">
                  <ArrowLeft className="h-4 w-4" />
                  عرض جميع العهد المتأخرة
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Actions */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {[
          { href: "/parties?action=create", label: "إضافة طرف جديد", icon: <Users className="h-5 w-5" /> },
          { href: "/payments?action=create", label: "إنشاء دفعة", icon: <CreditCard className="h-5 w-5" /> },
          { href: "/work-records?action=create", label: "تسجيل عمل جديد", icon: <Receipt className="h-5 w-5" /> },
          { href: "/reports", label: "عرض التقارير", icon: <TrendingUp className="h-5 w-5" /> },
        ].map((action) => (
          <Link key={action.href} href={action.href}>
            <Card className="hover:shadow-md transition-shadow cursor-pointer group">
              <CardContent className="p-4 flex flex-col items-center gap-2 text-center">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                  {action.icon}
                </div>
                <span className="text-sm font-medium">{action.label}</span>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
