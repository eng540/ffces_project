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
import { StatusBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { WorkRecord, PaginatedResponse, SelectOption } from "@/types";
import { Plus, Search, Eye, CheckCircle, XCircle, ClipboardList, Users } from "lucide-react";

function WorkRecordsPageContent() {
  const [records, setRecords] = useState<WorkRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [projectFilter, setProjectFilter] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [parties, setParties] = useState<SelectOption[]>([]);
  const [projects, setProjects] = useState<SelectOption[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [formData, setFormData] = useState({ party_id: "", project_id: "", work_date: "", hours_worked: "", rate_per_hour: "", description: "" });
  const [bulkRecords, setBulkRecords] = useState([{ party_id: "", work_date: "", hours_worked: "", rate_per_hour: "" }]);
  const [bulkProject, setBulkProject] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (statusFilter) params.status = statusFilter;
      if (projectFilter) params.project_id = projectFilter;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getWorkRecords(params) as PaginatedResponse<WorkRecord>;
      setRecords(res.items || []);
      setTotal(res.total || 0);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل سجلات العمل", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter, projectFilter, dateFrom, dateTo, searchQuery, addToast]);

  useEffect(() => {
    if (searchParams.get("action") === "create") setCreateOpen(true);
  }, [searchParams]);

  useEffect(() => {
    // FIX: properly extract items from paginated responses
    Promise.all([
      api.getParties({ type: "worker", page_size: "200" }).then((res: any) => {
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
      await api.createWorkRecord({
        party_id: formData.party_id,
        project_id: formData.project_id,
        work_date: formData.work_date,
        hours_worked: parseFloat(formData.hours_worked),
        rate_per_hour: parseFloat(formData.rate_per_hour),
        description: formData.description || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم تسجيل العمل بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ party_id: "", project_id: "", work_date: "", hours_worked: "", rate_per_hour: "", description: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل تسجيل العمل", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleBulkCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createBulkWorkRecords({
        project_id: bulkProject,
        records: bulkRecords.filter(r => r.party_id && r.work_date && r.hours_worked).map(r => ({
          party_id: r.party_id,
          work_date: r.work_date,
          hours_worked: parseFloat(r.hours_worked),
          rate_per_hour: parseFloat(r.rate_per_hour || "0"),
        })),
      });
      addToast({ title: "تم بنجاح", description: "تم تسجيل سجلات العمل بنجاح", variant: "success" });
      setBulkOpen(false);
      setBulkRecords([{ party_id: "", work_date: "", hours_worked: "", rate_per_hour: "" }]);
      setBulkProject("");
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (id: string) => {
    try {
      await api.verifyWorkRecord(id);
      addToast({ title: "تم بنجاح", description: "تم التحقق من السجل", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل", variant: "destructive" });
    }
  };

  const handleRejectRecord = async (id: string) => {
    try {
      await api.rejectWorkRecord(id);
      addToast({ title: "تم بنجاح", description: "تم رفض السجل", variant: "success" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل", variant: "destructive" });
    }
  };

  const addBulkRow = () => {
    setBulkRecords([...bulkRecords, { party_id: "", work_date: "", hours_worked: "", rate_per_hour: "" }]);
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">سجلات العمل</h1>
          <p className="page-description">تسجيل ومتابعة سجلات العمل اليومية</p>
        </div>
        <div className="flex gap-2">
          <Dialog open={bulkOpen} onOpenChange={setBulkOpen}>
            <DialogTrigger asChild>
              <Button variant="outline"><Users className="h-4 w-4" /> تسجيل جماعي</Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>تسجيل جماعي لسجلات العمل</DialogTitle>
                <DialogDescription>أضف سجلات عمل متعددة دفعة واحدة</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleBulkCreate} className="space-y-4">
                <div className="space-y-2">
                  <Label>المشروع</Label>
                  <Select value={bulkProject} onValueChange={setBulkProject}>
                    <SelectTrigger><SelectValue placeholder="اختر المشروع" /></SelectTrigger>
                    <SelectContent>
                      {projects.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {bulkRecords.map((row, idx) => (
                    <div key={idx} className="grid grid-cols-4 gap-2 items-end">
                      <Select value={row.party_id} onValueChange={(v) => { const newRec = [...bulkRecords]; newRec[idx].party_id = v; setBulkRecords(newRec); }}>
                        <SelectTrigger><SelectValue placeholder="العامل" /></SelectTrigger>
                        <SelectContent>
                          {parties.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                      <Input type="date" value={row.work_date} onChange={(e) => { const newRec = [...bulkRecords]; newRec[idx].work_date = e.target.value; setBulkRecords(newRec); }} />
                      <Input type="number" placeholder="الساعات" value={row.hours_worked} onChange={(e) => { const newRec = [...bulkRecords]; newRec[idx].hours_worked = e.target.value; setBulkRecords(newRec); }} />
                      <Input type="number" placeholder="معدل/ساعة" value={row.rate_per_hour} onChange={(e) => { const newRec = [...bulkRecords]; newRec[idx].rate_per_hour = e.target.value; setBulkRecords(newRec); }} />
                    </div>
                  ))}
                </div>
                <Button type="button" variant="outline" onClick={addBulkRow}>+ إضافة سطر</Button>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setBulkOpen(false)}>إلغاء</Button>
                  <Button type="submit" disabled={submitting || !bulkProject}>{submitting ? "جاري التسجيل..." : "تسجيل الكل"}</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button><Plus className="h-4 w-4" /> سجل جديد</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>تسجيل عمل جديد</DialogTitle>
                <DialogDescription>أدخل بيانات سجل العمل</DialogDescription>
              </DialogHeader>
              <form onSubmit={handleCreate} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>العامل</Label>
                    <Select value={formData.party_id} onValueChange={(v) => setFormData({ ...formData, party_id: v })}>
                      <SelectTrigger><SelectValue placeholder="اختر العامل" /></SelectTrigger>
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
                <div className="space-y-2">
                  <Label>تاريخ العمل</Label>
                  <Input type="date" value={formData.work_date} onChange={(e) => setFormData({ ...formData, work_date: e.target.value })} required />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>ساعات العمل</Label>
                    <Input type="number" step="0.5" value={formData.hours_worked} onChange={(e) => setFormData({ ...formData, hours_worked: e.target.value })} required placeholder="0" />
                  </div>
                  <div className="space-y-2">
                    <Label>معدل الساعة</Label>
                    <Input type="number" step="0.01" value={formData.rate_per_hour} onChange={(e) => setFormData({ ...formData, rate_per_hour: e.target.value })} required placeholder="0.00" />
                  </div>
                </div>
                <div className="space-y-2">
                  <Label>وصف</Label>
                  <Textarea value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} placeholder="وصف العمل المنجز" />
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>إلغاء</Button>
                  <Button type="submit" disabled={submitting}>{submitting ? "جاري التسجيل..." : "تسجيل"}</Button>
                </DialogFooter>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input className="ps-10" placeholder="بحث..." value={searchQuery} onChange={(e) => { setSearchQuery(e.target.value); setPage(1); }} />
        </div>
        <Select value={statusFilter} onValueChange={(v) => { setStatusFilter(v === "all" ? "" : v); setPage(1); }}>
          <SelectTrigger className="w-[130px]"><SelectValue placeholder="الحالة" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">الكل</SelectItem>
            <SelectItem value="pending">معلق</SelectItem>
            <SelectItem value="verified">متحقق</SelectItem>
            <SelectItem value="rejected">مرفوض</SelectItem>
          </SelectContent>
        </Select>
        <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1); }} className="w-auto" placeholder="من تاريخ" />
        <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1); }} className="w-auto" placeholder="إلى تاريخ" />
      </div>

      {loading ? <PageLoader /> : records.length === 0 ? (
        <EmptyState icon={<ClipboardList className="h-12 w-12" />} title="لا توجد سجلات" description="لم يتم العثور على سجلات عمل." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>العامل</TableHead>
                <TableHead>المشروع</TableHead>
                <TableHead>تاريخ العمل</TableHead>
                <TableHead>الساعات</TableHead>
                <TableHead>المعدل/ساعة</TableHead>
                <TableHead>إجمالي المبلغ</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-medium">{r.party_name}</TableCell>
                  <TableCell>{r.project_name}</TableCell>
                  <TableCell>{formatDate(r.work_date)}</TableCell>
                  <TableCell>{r.hours_worked}</TableCell>
                  <TableCell>{formatCurrency(r.rate_per_hour)}</TableCell>
                  <TableCell className="font-semibold">{formatCurrency(r.total_amount)}</TableCell>
                  <TableCell><StatusBadge status={r.status} /></TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {r.status === "pending" && (
                        <>
                          <Button size="sm" variant="ghost" className="text-green-600" onClick={() => handleVerify(r.id)}><CheckCircle className="h-4 w-4" /></Button>
                          <Button size="sm" variant="ghost" className="text-red-600" onClick={() => handleRejectRecord(r.id)}><XCircle className="h-4 w-4" /></Button>
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
              <span className="text-sm text-muted-foreground">إجمالي {total} سجل</span>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>السابق</Button>
                <span className="flex items-center px-3 text-sm">{page} / {pages}</span>
                <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>التالي</Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function WorkRecordsPage() {
  return (
    <Suspense fallback={<LoadingSpinner />}>
      <WorkRecordsPageContent />
    </Suspense>
  );
}
