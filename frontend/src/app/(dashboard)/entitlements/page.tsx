"use client";

import React, { useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { PageLoader, EmptyState } from "@/components/shared/loading";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Entitlement, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Eye, DollarSign, Calculator } from "lucide-react";

export default function EntitlementsPage() {
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [partyFilter, setPartyFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [parties, setParties] = useState<SelectOption[]>([]);
  const [projects, setProjects] = useState<SelectOption[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedEntitlement, setSelectedEntitlement] = useState<Entitlement | null>(null);
  const [formData, setFormData] = useState({ party_id: "", project_id: "", period_start: "", period_end: "", deductions: "", additions: "", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (statusFilter) params.status = statusFilter;
      if (partyFilter) params.party_id = partyFilter;
      if (projectFilter) params.project_id = projectFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getEntitlements(params) as PaginatedResponse<Entitlement>;
      setEntitlements(res.items);
      setTotal(res.total);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل المستحقات", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, partyFilter, projectFilter, searchQuery, addToast]);

  useEffect(() => {
    Promise.all([
      api.getParties().then((data: unknown) => setParties(data as SelectOption[])).catch(() => {}),
      api.getProjects().then((data: unknown) => setProjects(data as SelectOption[])).catch(() => {}),
    ]);
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createEntitlement({
        party_id: formData.party_id,
        project_id: formData.project_id,
        period_start: formData.period_start,
        period_end: formData.period_end,
        deductions: formData.deductions ? parseFloat(formData.deductions) : undefined,
        additions: formData.additions ? parseFloat(formData.additions) : undefined,
        notes: formData.notes || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم حساب المستحقات بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ party_id: "", project_id: "", period_start: "", period_end: "", deductions: "", additions: "", notes: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل حساب المستحقات", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة المستحقات</h1>
          <p className="page-description">حساب ومتابعة مستحقات الأطراف</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Calculator className="h-4 w-4" /> حساب مستحقات</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>حساب مستحقات جديدة</DialogTitle>
              <DialogDescription>أدخل الفترة والبيانات لحساب المستحقات</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>الطرف</Label>
                  <Select value={formData.party_id} onValueChange={(v) => setFormData({ ...formData, party_id: v })}>
                    <SelectTrigger><SelectValue placeholder="اختر الطرف" /></SelectTrigger>
                    <SelectContent>
                      {parties.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
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
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>بداية الفترة</Label>
                  <Input type="date" value={formData.period_start} onChange={(e) => setFormData({ ...formData, period_start: e.target.value })} required />
                </div>
                <div className="space-y-2">
                  <Label>نهاية الفترة</Label>
                  <Input type="date" value={formData.period_end} onChange={(e) => setFormData({ ...formData, period_end: e.target.value })} required />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>الخصومات</Label>
                  <Input type="number" step="0.01" value={formData.deductions} onChange={(e) => setFormData({ ...formData, deductions: e.target.value })} placeholder="0.00" />
                </div>
                <div className="space-y-2">
                  <Label>الإضافات</Label>
                  <Input type="number" step="0.01" value={formData.additions} onChange={(e) => setFormData({ ...formData, additions: e.target.value })} placeholder="0.00" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>ملاحظات</Label>
                <Textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="ملاحظات إضافية" />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>إلغاء</Button>
                <Button type="submit" disabled={submitting}>{submitting ? "جاري الحساب..." : "حساب"}</Button>
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
            <SelectItem value="calculated">محسوب</SelectItem>
            <SelectItem value="paid">مدفوع</SelectItem>
            <SelectItem value="cancelled">ملغي</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? <PageLoader /> : entitlements.length === 0 ? (
        <EmptyState icon={<DollarSign className="h-12 w-12" />} title="لا توجد مستحقات" description="لم يتم العثور على مستحقات. قم بحساب مستحقات جديدة." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الطرف</TableHead>
                <TableHead>المشروع</TableHead>
                <TableHead>الفترة</TableHead>
                <TableHead>إجمالي الساعات</TableHead>
                <TableHead>الخصومات</TableHead>
                <TableHead>الإضافات</TableHead>
                <TableHead>صافي المبلغ</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entitlements.map((ent) => (
                <TableRow key={ent.id}>
                  <TableCell className="font-medium">{ent.party_name}</TableCell>
                  <TableCell>{ent.project_name}</TableCell>
                  <TableCell>{formatDate(ent.period_start)} - {formatDate(ent.period_end)}</TableCell>
                  <TableCell>{ent.total_work_hours}</TableCell>
                  <TableCell className="text-red-600">{formatCurrency(ent.total_deductions)}</TableCell>
                  <TableCell className="text-green-600">{formatCurrency(ent.total_additions)}</TableCell>
                  <TableCell className="font-bold">{formatCurrency(ent.net_amount)}</TableCell>
                  <TableCell><StatusBadge status={ent.status} /></TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" onClick={() => { setSelectedEntitlement(ent); setViewOpen(true); }}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <span className="text-sm text-muted-foreground">إجمالي {total} مستحق</span>
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
          <DialogHeader><DialogTitle>تفاصيل المستحقات</DialogTitle></DialogHeader>
          {selectedEntitlement && (
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-muted-foreground">الطرف</p><p className="font-medium">{selectedEntitlement.party_name}</p></div>
              <div><p className="text-xs text-muted-foreground">المشروع</p><p>{selectedEntitlement.project_name}</p></div>
              <div><p className="text-xs text-muted-foreground">الفترة</p><p>{formatDate(selectedEntitlement.period_start)} - {formatDate(selectedEntitlement.period_end)}</p></div>
              <div><p className="text-xs text-muted-foreground">الحالة</p><StatusBadge status={selectedEntitlement.status} /></div>
              <div><p className="text-xs text-muted-foreground">إجمالي ساعات العمل</p><p className="font-semibold">{selectedEntitlement.total_work_hours} ساعة</p></div>
              <div><p className="text-xs text-muted-foreground">الخصومات</p><p className="text-red-600 font-semibold">{formatCurrency(selectedEntitlement.total_deductions)}</p></div>
              <div><p className="text-xs text-muted-foreground">الإضافات</p><p className="text-green-600 font-semibold">{formatCurrency(selectedEntitlement.total_additions)}</p></div>
              <div><p className="text-xs text-muted-foreground">صافي المبلغ</p><p className="font-bold text-xl">{formatCurrency(selectedEntitlement.net_amount)}</p></div>
              {selectedEntitlement.notes && <div className="col-span-2"><p className="text-xs text-muted-foreground">ملاحظات</p><p>{selectedEntitlement.notes}</p></div>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
