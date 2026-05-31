"use client";

import React, { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PageLoader, EmptyState, LoadingSpinner } from "@/components/shared/loading";
import { StatusBadge, CategoryBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Expense, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Eye, CheckCircle, XCircle, Receipt } from "lucide-react";

function ExpensesPageContent() {
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [custodyFilter, setCustodyFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [custodies, setCustodies] = useState<SelectOption[]>([]);
  const [projects, setProjects] = useState<SelectOption[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedExpense, setSelectedExpense] = useState<Expense | null>(null);
  const [formData, setFormData] = useState({ amount: "", description: "", category: "misc", receipt_number: "", expense_date: "", custody_id: "" });
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (statusFilter) params.status = statusFilter;
      if (projectFilter) params.project_id = projectFilter;
      if (custodyFilter) params.custody_id = custodyFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getExpenses(params) as PaginatedResponse<Expense>;
      setExpenses(res.items || []);
      setTotal(res.total || 0);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل المصروفات", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, projectFilter, custodyFilter, searchQuery, addToast]);

  useEffect(() => {
    if (searchParams.get("action") === "create") setCreateOpen(true);
  }, [searchParams]);

  useEffect(() => {
    Promise.all([
      // FIX: Use api.getCustodies (not api.getExpenses) for the custody dropdown
      api.getCustodies({ status: "open", page_size: "200" }).then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.items || []);
        setCustodies(items.map((c: any) => ({ value: c.id, label: c.description || c.holder_name || c.id })));
      }).catch(() => {}),
      api.getProjects({ page_size: "200" }).then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.items || []);
        setProjects(items.map((p: any) => ({ value: p.id, label: p.name || p.description || p.id })));
      }).catch(() => {}),
    ]);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createExpense({
        amount: parseFloat(formData.amount),
        description: formData.description,
        category: formData.category,
        receipt_number: formData.receipt_number || undefined,
        expense_date: formData.expense_date,
        custody_id: formData.custody_id,
      });
      addToast({ title: "تم بنجاح", description: "تم إنشاء المصروف بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ amount: "", description: "", category: "misc", receipt_number: "", expense_date: "", custody_id: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل إنشاء المصروف", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveExpense(id);
      addToast({ title: "تم بنجاح", description: "تم اعتماد المصروف", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل اعتماد المصروف", variant: "destructive" });
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectExpense(id);
      addToast({ title: "تم بنجاح", description: "تم رفض المصروف", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل رفض المصروف", variant: "destructive" });
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة المصروفات</h1>
          <p className="page-description">عرض وإدارة جميع المصروفات</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" /> مصروف جديد</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إنشاء مصروف جديد</DialogTitle>
              <DialogDescription>أدخل بيانات المصروف</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>المبلغ</Label>
                  <Input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} required placeholder="0.00" />
                </div>
                <div className="space-y-2">
                  <Label>التاريخ</Label>
                  <Input type="date" value={formData.expense_date} onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })} required />
                </div>
              </div>
              <div className="space-y-2">
                <Label>الوصف</Label>
                <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required placeholder="وصف المصروف" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>التصنيف</Label>
                  <Select value={formData.category} onValueChange={(v) => setFormData({ ...formData, category: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="transportation">نقل</SelectItem>
                      <SelectItem value="materials">مواد</SelectItem>
                      <SelectItem value="labor">عمالة</SelectItem>
                      <SelectItem value="equipment">معدات</SelectItem>
                      <SelectItem value="food">طعام</SelectItem>
                      <SelectItem value="accommodation">سكن</SelectItem>
                      <SelectItem value="misc">أخرى</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>رقم الإيصال</Label>
                  <Input value={formData.receipt_number} onChange={(e) => setFormData({ ...formData, receipt_number: e.target.value })} placeholder="رقم الإيصال (اختياري)" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>العهدة</Label>
                <Select value={formData.custody_id} onValueChange={(v) => setFormData({ ...formData, custody_id: v })}>
                  <SelectTrigger><SelectValue placeholder="اختر العهدة" /></SelectTrigger>
                  <SelectContent>
                    {custodies.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>إلغاء</Button>
                <Button type="submit" disabled={submitting}>{submitting ? "جاري الإنشاء..." : "إنشاء"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="ps-10" placeholder="بحث..." value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }} />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">الكل</SelectItem>
            <SelectItem value="pending">معلق</SelectItem>
            <SelectItem value="approved">معتمد</SelectItem>
            <SelectItem value="rejected">مرفوض</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? <PageLoader /> : expenses.length === 0 ? (
        <EmptyState icon={<Receipt className="h-12 w-12" />} title="لا توجد مصروفات" description="لم يتم العثور على مصروفات. قم بإنشاء مصروف جديد." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الوصف</TableHead>
                <TableHead>التصنيف</TableHead>
                <TableHead>المبلغ</TableHead>
                <TableHead>العهدة</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>التاريخ</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {expenses.map((e) => (
                <TableRow key={e.id}>
                  <TableCell className="font-medium max-w-[200px] truncate">{e.description}</TableCell>
                  <TableCell><CategoryBadge category={e.category} /></TableCell>
                  <TableCell>{formatCurrency(e.amount)}</TableCell>
                  <TableCell className="max-w-[150px] truncate">{e.custody_description}</TableCell>
                  <TableCell><StatusBadge status={e.status} /></TableCell>
                  <TableCell>{formatDate(e.expense_date)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => { setSelectedExpense(e); setViewOpen(true); }}><Eye className="h-4 w-4" /></Button>
                      {e.status === "pending" && (
                        <>
                          <Button size="sm" variant="ghost" className="text-green-600" onClick={() => handleApprove(e.id)}><CheckCircle className="h-4 w-4" /></Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleReject(e.id)}><XCircle className="h-4 w-4" /></Button>
                        </>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <span className="text-sm text-muted-foreground">إجمالي {total} مصروف</span>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>السابق</Button>
                <span className="flex items-center px-3 text-sm">{page} / {pages}</span>
                <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>التالي</Button>
              </div>
            </div>
          )}
        </div>
      )}

      <Dialog open={viewOpen} onOpenChange={setViewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>تفاصيل المصروف</DialogTitle></DialogHeader>
          {selectedExpense && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><p className="text-xs text-muted-foreground">الوصف</p><p className="font-medium">{selectedExpense.description}</p></div>
                <div><p className="text-xs text-muted-foreground">التصنيف</p><CategoryBadge category={selectedExpense.category} /></div>
                <div><p className="text-xs text-muted-foreground">المبلغ</p><p className="font-bold text-lg">{formatCurrency(selectedExpense.amount)}</p></div>
                <div><p className="text-xs text-muted-foreground">الحالة</p><StatusBadge status={selectedExpense.status} /></div>
                <div><p className="text-xs text-muted-foreground">العهدة</p><p>{selectedExpense.custody_description}</p></div>
                <div><p className="text-xs text-muted-foreground">المشروع</p><p>{selectedExpense.project_name}</p></div>
                <div><p className="text-xs text-muted-foreground">التاريخ</p><p>{formatDate(selectedExpense.expense_date)}</p></div>
                <div><p className="text-xs text-muted-foreground">بواسطة</p><p>{selectedExpense.created_by_name}</p></div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ExpensesPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <ExpensesPageContent />
    </Suspense>
  );
}
