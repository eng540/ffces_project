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
import { formatCurrency, formatDate, formatDateTime } from "@/lib/utils";
import type { Settlement, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Eye, Scale, CheckCircle, XCircle } from "lucide-react";

export default function SettlementsPage() {
  const [settlements, setSettlements] = useState<Settlement[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [custodyFilter, setCustodyFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [custodies, setCustodies] = useState<SelectOption[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedSettlement, setSelectedSettlement] = useState<Settlement | null>(null);
  const [formData, setFormData] = useState({ custody_id: "", total_refund: "", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (statusFilter) params.status = statusFilter;
      if (custodyFilter) params.custody_id = custodyFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getSettlements(params) as PaginatedResponse<Settlement>;
      setSettlements(res.items || []);
      setTotal(res.total || 0);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل التسويات", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, custodyFilter, searchQuery, addToast]);

  useEffect(() => {
    // FIX: properly extract items from paginated response
    api.getCustodies({ status: "open", page_size: "200" }).then((res: any) => {
      const items = Array.isArray(res) ? res : (res?.items || []);
      setCustodies(items.map((c: any) => ({ value: c.id, label: c.description || c.holder_name || c.id })));
    }).catch(() => {});
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createSettlement({
        custody_id: formData.custody_id,
        total_refund: parseFloat(formData.total_refund),
        notes: formData.notes || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم إنشاء التسوية بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ custody_id: "", total_refund: "", notes: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل إنشاء التسوية", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveSettlement(id);
      addToast({ title: "تم بنجاح", description: "تم اعتماد التسوية", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل", variant: "destructive" });
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectSettlement(id);
      addToast({ title: "تم بنجاح", description: "تم رفض التسوية", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل", variant: "destructive" });
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة التسويات</h1>
          <p className="page-description">تسوية العهد المالية المقفلة</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" /> تسوية جديدة</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إنشاء تسوية جديدة</DialogTitle>
              <DialogDescription>اختر العهدة وأدخل تفاصيل التسوية</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="space-y-2">
                <Label>العهدة</Label>
                <Select value={formData.custody_id} onValueChange={(v) => setFormData({ ...formData, custody_id: v })}>
                  <SelectTrigger><SelectValue placeholder="اختر العهدة" /></SelectTrigger>
                  <SelectContent>
                    {custodies.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>مبلغ الاسترداد</Label>
                <Input type="number" step="0.01" value={formData.total_refund} onChange={(e) => setFormData({ ...formData, total_refund: e.target.value })} required placeholder="0.00" />
              </div>
              <div className="space-y-2">
                <Label>ملاحظات</Label>
                <Textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="ملاحظات إضافية" />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>إلغاء</Button>
                <Button type="submit" disabled={submitting}>{submitting ? "جاري الإنشاء..." : "إنشاء"}</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

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

      {loading ? <PageLoader /> : settlements.length === 0 ? (
        <EmptyState icon={<Scale className="h-12 w-12" />} title="لا توجد تسويات" description="لم يتم العثور على تسويات." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>العهدة</TableHead>
                <TableHead>إجمالي المصروفات</TableHead>
                <TableHead>مبلغ الاسترداد</TableHead>
                <TableHead>صافي المبلغ</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>تاريخ التسوية</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {settlements.map((s) => (
                <TableRow key={s.id}>
                  <TableCell className="font-medium max-w-[200px] truncate">{s.custody_description}</TableCell>
                  <TableCell>{formatCurrency(s.total_expenses)}</TableCell>
                  <TableCell>{formatCurrency(s.total_refund)}</TableCell>
                  <TableCell className={s.net_amount < 0 ? "text-red-600 font-semibold" : "font-semibold"}>
                    {formatCurrency(s.net_amount)}
                  </TableCell>
                  <TableCell><StatusBadge status={s.status} /></TableCell>
                  <TableCell>{formatDate(s.settlement_date)}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => { setSelectedSettlement(s); setViewOpen(true); }}><Eye className="h-4 w-4" /></Button>
                      {s.status === "pending" && (
                        <>
                          <Button size="sm" variant="ghost" className="text-green-600" onClick={() => handleApprove(s.id)}><CheckCircle className="h-4 w-4" /></Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleReject(s.id)}><XCircle className="h-4 w-4" /></Button>
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
              <span className="text-sm text-muted-foreground">إجمالي {total} تسوية</span>
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
          <DialogHeader><DialogTitle>تفاصيل التسوية</DialogTitle></DialogHeader>
          {selectedSettlement && (
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-muted-foreground">العهدة</p><p className="font-medium">{selectedSettlement.custody_description}</p></div>
              <div><p className="text-xs text-muted-foreground">الحالة</p><StatusBadge status={selectedSettlement.status} /></div>
              <div><p className="text-xs text-muted-foreground">إجمالي المصروفات</p><p className="font-bold">{formatCurrency(selectedSettlement.total_expenses)}</p></div>
              <div><p className="text-xs text-muted-foreground">مبلغ الاسترداد</p><p className="font-bold">{formatCurrency(selectedSettlement.total_refund)}</p></div>
              <div><p className="text-xs text-muted-foreground">صافي المبلغ</p><p className={`font-bold text-lg ${selectedSettlement.net_amount < 0 ? "text-red-600" : "text-green-600"}`}>{formatCurrency(selectedSettlement.net_amount)}</p></div>
              <div><p className="text-xs text-muted-foreground">تاريخ التسوية</p><p>{formatDate(selectedSettlement.settlement_date)}</p></div>
              <div><p className="text-xs text-muted-foreground">بواسطة</p><p>{selectedSettlement.created_by_name}</p></div>
              {selectedSettlement.notes && <div className="col-span-2"><p className="text-xs text-muted-foreground">ملاحظات</p><p>{selectedSettlement.notes}</p></div>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
