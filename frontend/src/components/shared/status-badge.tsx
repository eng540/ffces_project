"use client";

import { cn } from "@/lib/utils";
import { getStatusColor, getPartyTypeLabel, getPaymentTypeLabel, getExpenseCategoryLabel } from "@/lib/utils";

interface StatusBadgeProps {
  status: string;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const { bg, text, label } = getStatusColor(status);
  return (
    <span className={cn("status-badge", bg, text, className)}>
      {label}
    </span>
  );
}

interface PartyTypeBadgeProps {
  type: string;
  className?: string;
}

export function PartyTypeBadge({ type, className }: PartyTypeBadgeProps) {
  const colors: Record<string, string> = {
    worker: "bg-blue-100 text-blue-800",
    supplier: "bg-purple-100 text-purple-800",
    contractor: "bg-orange-100 text-orange-800",
  };
  return (
    <span className={cn("status-badge", colors[type] || "bg-gray-100 text-gray-800", className)}>
      {getPartyTypeLabel(type)}
    </span>
  );
}

interface PaymentTypeBadgeProps {
  type: string;
  className?: string;
}

export function PaymentTypeBadge({ type, className }: PaymentTypeBadgeProps) {
  const colors: Record<string, string> = {
    advance: "bg-cyan-100 text-cyan-800",
    salary: "bg-green-100 text-green-800",
    invoice: "bg-purple-100 text-purple-800",
    settlement: "bg-amber-100 text-amber-800",
    reimbursement: "bg-blue-100 text-blue-800",
  };
  return (
    <span className={cn("status-badge", colors[type] || "bg-gray-100 text-gray-800", className)}>
      {getPaymentTypeLabel(type)}
    </span>
  );
}

interface CategoryBadgeProps {
  category: string;
  className?: string;
}

export function CategoryBadge({ category, className }: CategoryBadgeProps) {
  return (
    <span className={cn("status-badge bg-slate-100 text-slate-700", className)}>
      {getExpenseCategoryLabel(category)}
    </span>
  );
}
