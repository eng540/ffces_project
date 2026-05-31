import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("ar-SA", {
    style: "currency",
    currency: "SAR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "—";
  return new Intl.DateTimeFormat("ar-SA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(date));
}

export function formatDateTime(date: string | null | undefined): string {
  if (!date) return "—";
  return new Intl.DateTimeFormat("ar-SA", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(date));
}

export function getStatusColor(status: string): {
  bg: string;
  text: string;
  label: string;
} {
  const colors: Record<string, { bg: string; text: string; label: string }> = {
    open: { bg: "bg-blue-100", text: "text-blue-800", label: "مفتوح" },
    closed: { bg: "bg-green-100", text: "text-green-800", label: "مقفل" },
    overdue: { bg: "bg-red-100", text: "text-red-800", label: "متأخر" },
    partially_settled: {
      bg: "bg-amber-100",
      text: "text-amber-800",
      label: "مسدد جزئياً",
    },
    under_review: {
      bg: "bg-purple-100",
      text: "text-purple-800",
      label: "قيد المراجعة",
    },
    pending: { bg: "bg-amber-100", text: "text-amber-800", label: "معلق" },
    approved: { bg: "bg-green-100", text: "text-green-800", label: "معتمد" },
    rejected: { bg: "bg-red-100", text: "text-red-800", label: "مرفوض" },
    verified: { bg: "bg-green-100", text: "text-green-800", label: "متحقق" },
    calculated: { bg: "bg-blue-100", text: "text-blue-800", label: "محسوب" },
    paid: { bg: "bg-green-100", text: "text-green-800", label: "مدفوع" },
    cancelled: { bg: "bg-gray-100", text: "text-gray-800", label: "ملغي" },
  };
  return (
    colors[status] || {
      bg: "bg-gray-100",
      text: "text-gray-800",
      label: status,
    }
  );
}

export function getPartyTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    worker: "عامل",
    supplier: "مورد",
    contractor: "مقاول",
  };
  return labels[type] || type;
}

export function getPaymentTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    advance: "سلفة",
    salary: "راتب",
    invoice: "فاتورة",
    settlement: "تسوية",
    reimbursement: "استرداد",
  };
  return labels[type] || type;
}

export function getExpenseCategoryLabel(category: string): string {
  const labels: Record<string, string> = {
    transportation: "نقل",
    materials: "مواد",
    labor: "عمالة",
    equipment: "معدات",
    food: "طعام",
    accommodation: "سكن",
    misc: "أخرى",
  };
  return labels[category] || category;
}

export function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
