"use client";

import React, { Suspense, useEffect, useState, useCallback } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PageLoader, EmptyState, LoadingSpinner } from "@/components/shared/loading";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Custody, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Filter, Eye, CheckCircle, Shield } from "lucide-react";

function CustodiesPageContent() {
  const [custodies, setCustodies] = useState<Custody[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [projects, setProjects] = useState<SelectOption[]>([]);
  const [projectFilter, setProjectFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedCustody, setSelectedCustody] = useState<Custody | null>(null);
  const [formData, setFormData] = useState({ amount: "", holder_id: "", project_id: "", description: "", due_date: "" });
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (statusFilter) params.status = statusFilter;
      if (projectFilter) params.project_id = projectFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getCustodies(params) as PaginatedResponse<Custody>;
      setCustodies(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      addToast({ title: "خطأ", description: "فشل تحميل العهد", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, projectFilter, searchQuery, addToast]);

  useEffect(() => {
    if (searchParams.get("action") === "create") setCreateOpen(true);
  }, [searchParams]);

  useEffect(() => {
    api.getProjects({ page_size: "200" }).then((res: any) => {
      const items = Array.isArray(res) ? res : (res?.items || []);
      setProjects(items.map((p: any) => ({ value: p.id, label: p.name || p.description || p.id })));
    }).catch(() => {});
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createCustody({
        amount: parseFloat(formData.amount),
        holder_id: formData.holder_id,
        project_id: formData.project_id,
        description: formData.description,
        due_date: formData.due_date || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم إنشاء العهدة بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ amount: "", holder_id: "", project_id: "", description: "", due_date: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل إنشاء العهدة", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleSettle = async (custodyId: string) => {
    try {
      await api.settleCustody(custodyId, { total_refund: 0, notes: "تسوية نهائية" });
      addToast({ title: "تم بنجاح", description: "تم تسوية العهدة", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل تسوية العهدة", variant: "destructive" });
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة العهد</h1>
          <p className="page-description">عرض وإدارة جميع العهد المالية</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" /> عهدة جديدة</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إنشاء عهدة جديدة</DialogTitle>
              <DialogDescription>أدخل بيانات العهدة المالية</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>المبلغ</Label>
                <Input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} required placeholder="0.00" />
              </div>
              <div className="space-y-2">
                <Label>معرف الحامل</Label>
                <Input value={formData.holder_id} onChange={(e) => setFormData({ ...formData, holder_id: e.target.value })} required placeholder="أدخل معرف الحامل" />
              </div>
              <div className="space-y-2">
                <Label>المشروع</Label>
                <Select value={formData.project_id} onValueChange={(v) => setFormData({ ...formData, project_id: v })}>
                  <SelectTrigger><SelectValue placeholder="اختر المشروع" /></SelectTrigger>
                  <SelectContent>
                    {projects.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>الوصف</Label>
                <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="وصف العهدة" />
              </div>
              <div className="space-y-2">
                <Label>تاريخ الاستحقاق</Label>
                <Input type="date" value={formData.due_date} onChange={(e) => setFormData({ ...formData, due_date: e.target.value })} />
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
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">جميع الحالات</SelectItem>
            <SelectItem value="open">مفتوح</SelectItem>
            <SelectItem value="closed">مقفل</SelectItem>
            <SelectItem value="overdue">متأخر</SelectItem>
            <SelectItem value="partially_settled">مسدد جزئياً</SelectItem>
          </SelectContent>
        </Select>
        <Select value={projectFilter} onValueChange={(v) => { setProjectFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[160px]"><SelectValue placeholder="المشروع" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">جميع المشاريع</SelectItem>
            {projects.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      {loading ? (
        <PageLoader />
      ) : custodies.length === 0 ? (
        <EmptyState icon={<Shield className="h-12 w-12" />} title="لا توجد عهد" description="لم يتم العثور على عهد. قم بإنشاء عهدة جديدة." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الوصف</TableHead>
                <TableHead>الحامل</TableHead>
                <TableHead>المشروع</TableHead>
                <TableHead>المبلغ</TableHead>
                <TableHead>المتبقي</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>تاريخ الإصدار</TableHead>
                <TableHead>تاريخ الاستحقاق</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {custodies.map((c) => (
                <TableRow key={c.id}>
                  <TableCell className="font-medium max-w-[200px] truncate">{c.description}</TableCell>
                  <TableCell>{c.holder_name}</TableCell>
                  <TableCell>{c.project_name}</TableCell>
                  <TableCell>{formatCurrency(c.amount)}</TableCell>
                  <TableCell>{formatCurrency(c.remaining_amount)}</TableCell>
                  <TableCell><StatusBadge status={c.status} /></TableCell>
                  <TableCell>{formatDate(c.issued_date)}</TableCell>
                  <TableCell>{formatDate(c.due_date)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => { setSelectedCustody(c); setViewOpen(true); }}>
                        <Eye className="h-4 w-4" />
                      </Button>
                      {c.status === "open" && (
                        <Button size="sm" variant="ghost" className="text-green-600 hover:text-green-700" onClick={() => handleSettle(c.id)}>
                          <CheckCircle className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <span className="text-sm text-muted-foreground">إجمالي {total} عهدة</span>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>السابق</Button>
                <span className="flex items-center px-3 text-sm">{page} / {pages}</span>
                <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>التالي</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* View Dialog */}
      <Dialog open={viewOpen} onOpenChange={setViewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>تفاصيل العهدة</DialogTitle>
          </DialogHeader>
          {selectedCustody && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div><p className="text-xs text-muted-foreground">الوصف</p><p className="font-medium">{selectedCustody.description}</p></div>
                <div><p className="text-xs text-muted-foreground">الحامل</p><p className="font-medium">{selectedCustody.holder_name}</p></div>
                <div><p className="text-xs text-muted-foreground">المشروع</p><p className="font-medium">{selectedCustody.project_name}</p></div>
                <div><p className="text-xs text-muted-foreground">الحالة</p><StatusBadge status={selectedCustody.status} /></div>
                <div><p className="text-xs text-muted-foreground">المبلغ</p><p className="font-bold text-lg">{formatCurrency(selectedCustody.amount)}</p></div>
                <div><p className="text-xs text-muted-foreground">المبلغ المتبقي</p><p className="font-bold text-lg text-amber-600">{formatCurrency(selectedCustody.remaining_amount)}</p></div>
                <div><p className="text-xs text-muted-foreground">تاريخ الإصدار</p><p>{formatDate(selectedCustody.issued_date)}</p></div>
                <div><p className="text-xs text-muted-foreground">تاريخ الاستحقاق</p><p>{formatDate(selectedCustody.due_date)}</p></div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function CustodiesPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <CustodiesPageContent />
    </Suspense>
  );
}
