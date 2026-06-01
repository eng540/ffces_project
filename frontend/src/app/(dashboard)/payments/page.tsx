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
import { PaymentTypeBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Payment, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Eye, CreditCard } from "lucide-react";

function PaymentsPageContent() {
  const [payments, setPayments] = useState<Payment[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [partyFilter, setPartyFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [parties, setParties] = useState<SelectOption[]>([]);
  const [projects, setProjects] = useState<SelectOption[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedPayment, setSelectedPayment] = useState<Payment | null>(null);
  const [formData, setFormData] = useState({ amount: "", payment_type: "advance", description: "", reference_number: "", payment_date: "", party_id: "", project_id: "", custody_id: "" });
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (typeFilter) params.payment_type = typeFilter;
      if (projectFilter) params.project_id = projectFilter;
      if (partyFilter) params.party_id = partyFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getPayments(params) as PaginatedResponse<Payment>;
      setPayments(res.items || []);
      setTotal(res.total || 0);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل الدفعات", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter, projectFilter, partyFilter, searchQuery, addToast]);

  useEffect(() => {
    if (searchParams.get("action") === "create") setCreateOpen(true);
  }, [searchParams]);

  useEffect(() => {
    // FIX: properly extract items from paginated responses
    Promise.all([
      api.getParties({ page_size: "200" }).then((res: any) => {
        const items = Array.isArray(res) ? res : (res?.items || []);
        setParties(items.map((p: any) => ({ value: p.id, label: p.name || p.id })));
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
      await api.createPayment({
        amount: parseFloat(formData.amount),
        payment_type: formData.payment_type,
        description: formData.description,
        reference_number: formData.reference_number || undefined,
        payment_date: formData.payment_date,
        party_id: formData.party_id,
        project_id: formData.project_id,
        custody_id: formData.custody_id || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم إنشاء الدفعة بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ amount: "", payment_type: "advance", description: "", reference_number: "", payment_date: "", party_id: "", project_id: "", custody_id: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل إنشاء الدفعة", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة الدفعات</h1>
          <p className="page-description">عرض وإدارة جميع الدفعات المالية</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" /> دفعة جديدة</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إنشاء دفعة جديدة</DialogTitle>
              <DialogDescription>أدخل بيانات الدفعة</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>المبلغ</Label>
                  <Input type="number" step="0.01" value={formData.amount} onChange={(e) => setFormData({ ...formData, amount: e.target.value })} required placeholder="0.00" />
                </div>
                <div className="space-y-2">
                  <Label>نوع الدفعة</Label>
                  <Select value={formData.payment_type} onValueChange={(v) => setFormData({ ...formData, payment_type: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="advance">سلفة</SelectItem>
                      <SelectItem value="salary">راتب</SelectItem>
                      <SelectItem value="invoice">فاتورة</SelectItem>
                      <SelectItem value="settlement">تسوية</SelectItem>
                      <SelectItem value="reimbursement">استرداد</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>الوصف</Label>
                <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} required placeholder="وصف الدفعة" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>التاريخ</Label>
                  <Input type="date" value={formData.payment_date} onChange={(e) => setFormData({ ...formData, payment_date: e.target.value })} required />
                </div>
                <div className="space-y-2">
                  <Label>رقم المرجع</Label>
                  <Input value={formData.reference_number} onChange={(e) => setFormData({ ...formData, reference_number: e.target.value })} placeholder="رقم المرجع (اختياري)" />
                </div>
              </div>
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
        <Select value={typeFilter} onValueChange={(v) => { setTypeFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="النوع" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">الكل</SelectItem>
            <SelectItem value="advance">سلفة</SelectItem>
            <SelectItem value="salary">راتب</SelectItem>
            <SelectItem value="invoice">فاتورة</SelectItem>
            <SelectItem value="settlement">تسوية</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? <PageLoader /> : payments.length === 0 ? (
        <EmptyState icon={<CreditCard className="h-12 w-12" />} title="لا توجد دفعات" description="لم يتم العثور على دفعات. قم بإنشاء دفعة جديدة." />
      ) : (
        <div className="data-table-wrapper overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الوصف</TableHead>
                <TableHead>النوع</TableHead>
                <TableHead>المبلغ</TableHead>
                <TableHead>الطرف</TableHead>
                <TableHead>المشروع</TableHead>
                <TableHead>التاريخ</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {payments.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium max-w-[200px] truncate">{p.description}</TableCell>
                  <TableCell><PaymentTypeBadge type={p.payment_type} /></TableCell>
                  <TableCell>{formatCurrency(p.amount)}</TableCell>
                  <TableCell>{p.party_name}</TableCell>
                  <TableCell>{p.project_name}</TableCell>
                  <TableCell>{formatDate(p.payment_date)}</TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" onClick={() => { setSelectedPayment(p); setViewOpen(true); }}><Eye className="h-4 w-4" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <span className="text-sm text-muted-foreground">إجمالي {total} دفعة</span>
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
          <DialogHeader><DialogTitle>تفاصيل الدفعة</DialogTitle></DialogHeader>
          {selectedPayment && (
            <div className="grid grid-cols-2 gap-4">
              <div><p className="text-xs text-muted-foreground">الوصف</p><p className="font-medium">{selectedPayment.description}</p></div>
              <div><p className="text-xs text-muted-foreground">النوع</p><PaymentTypeBadge type={selectedPayment.payment_type} /></div>
              <div><p className="text-xs text-muted-foreground">المبلغ</p><p className="font-bold text-lg">{formatCurrency(selectedPayment.amount)}</p></div>
              <div><p className="text-xs text-muted-foreground">الطرف</p><p>{selectedPayment.party_name}</p></div>
              <div><p className="text-xs text-muted-foreground">المشروع</p><p>{selectedPayment.project_name}</p></div>
              <div><p className="text-xs text-muted-foreground">التاريخ</p><p>{formatDate(selectedPayment.payment_date)}</p></div>
              <div><p className="text-xs text-muted-foreground">رقم المرجع</p><p>{selectedPayment.reference_number || "—"}</p></div>
              <div><p className="text-xs text-muted-foreground">بواسطة</p><p>{selectedPayment.created_by_name}</p></div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function PaymentsPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <PaymentsPageContent />
    </Suspense>
  );
}
