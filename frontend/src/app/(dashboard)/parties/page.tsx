"use client";

import React, { useEffect, useState, useCallback } from "react";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageLoader, EmptyState } from "@/components/shared/loading";
import { PartyTypeBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate } from "@/lib/utils";
import type { Party, PaginatedResponse, Payment, Entitlement } from "@/types";
import { Plus, Search, Eye, Users } from "lucide-react";

export default function PartiesPage() {
  const [parties, setParties] = useState<Party[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewOpen, setViewOpen] = useState(false);
  const [selectedParty, setSelectedParty] = useState<Party | null>(null);
  const [partyPayments, setPartyPayments] = useState<Payment[]>([]);
  const [partyEntitlements, setPartyEntitlements] = useState<Entitlement[]>([]);
  const [formData, setFormData] = useState({ name: "", type: "worker", phone: "", email: "", address: "", national_id: "", notes: "" });
  const [submitting, setSubmitting] = useState(false);
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const params: Record<string, string> = { page: String(page), page_size: String(pageSize) };
      if (typeFilter) params.type = typeFilter;
      if (searchQuery) params.search = searchQuery;
      const res = await api.getParties(params) as PaginatedResponse<Party>;
      setParties(res.items);
      setTotal(res.total);
    } catch {
      addToast({ title: "خطأ", description: "فشل تحميل الأطراف", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter, searchQuery, addToast]);

  useEffect(() => {
    if (searchParams.get("action") === "create") setCreateOpen(true);
  }, [searchParams]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createParty({
        name: formData.name,
        type: formData.type as "worker" | "supplier" | "contractor",
        phone: formData.phone || undefined,
        email: formData.email || undefined,
        address: formData.address || undefined,
        national_id: formData.national_id || undefined,
        notes: formData.notes || undefined,
      });
      addToast({ title: "تم بنجاح", description: "تم إضافة الطرف بنجاح", variant: "success" });
      setCreateOpen(false);
      setFormData({ name: "", type: "worker", phone: "", email: "", address: "", national_id: "", notes: "" });
      fetchData();
    } catch (err) {
      addToast({ title: "خطأ", description: err instanceof Error ? err.message : "فشل إضافة الطرف", variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleView = async (party: Party) => {
    setSelectedParty(party);
    setViewOpen(true);
    try {
      const [paymentsRes, entitlementsRes] = await Promise.all([
        api.getPayments({party_id: party.id, page_size: "100"}).catch(() => ({items: []})) as Promise<PaginatedResponse<Payment>>,
        api.getEntitlements({party_id: party.id, page_size: "100"}).catch(() => ({items: []})) as Promise<PaginatedResponse<Entitlement>>,
      ]);
      setPartyPayments(paymentsRes.items);
      setPartyEntitlements(entitlementsRes.items);
    } catch {
      // silently handle
    }
  };

  const pages = Math.ceil(total / pageSize);

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">إدارة الأطراف</h1>
          <p className="page-description">إدارة العمال والموردين والمقاولين</p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="h-4 w-4" /> طرف جديد</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>إضافة طرف جديد</DialogTitle>
              <DialogDescription>أدخل بيانات الطرف</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>الاسم</Label>
                  <Input value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} required placeholder="اسم الطرف" />
                </div>
                <div className="space-y-2">
                  <Label>النوع</Label>
                  <Select value={formData.type} onValueChange={(v) => setFormData({ ...formData, type: v })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="worker">عامل</SelectItem>
                      <SelectItem value="supplier">مورد</SelectItem>
                      <SelectItem value="contractor">مقاول</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>الهاتف</Label>
                  <Input value={formData.phone} onChange={(e) => setFormData({ ...formData, phone: e.target.value })} placeholder="رقم الهاتف" />
                </div>
                <div className="space-y-2">
                  <Label>البريد الإلكتروني</Label>
                  <Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} placeholder="البريد الإلكتروني" />
                </div>
              </div>
              <div className="space-y-2">
                <Label>العنوان</Label>
                <Input value={formData.address} onChange={(e) => setFormData({ ...formData, address: e.target.value })} placeholder="العنوان" />
              </div>
              <div className="space-y-2">
                <Label>ملاحظات</Label>
                <Textarea value={formData.notes} onChange={(e) => setFormData({ ...formData, notes: e.target.value })} placeholder="ملاحظات إضافية" />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>إلغاء</Button>
                <Button type="submit" disabled={submitting}>{submitting ? "جاري الإضافة..." : "إضافة"}</Button>
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
            <SelectItem value="worker">عامل</SelectItem>
            <SelectItem value="supplier">مورد</SelectItem>
            <SelectItem value="contractor">مقاول</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {loading ? <PageLoader /> : parties.length === 0 ? (
        <EmptyState icon={<Users className="h-12 w-12" />} title="لا توجد أطراف" description="لم يتم العثور على أطراف. قم بإضافة طرف جديد." />
      ) : (
        <div className="data-table-wrapper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>الاسم</TableHead>
                <TableHead>النوع</TableHead>
                <TableHead>الهاتف</TableHead>
                <TableHead>إجمالي المدفوع</TableHead>
                <TableHead>إجمالي المستحقات</TableHead>
                <TableHead>الرصيد</TableHead>
                <TableHead>الحالة</TableHead>
                <TableHead>الإجراءات</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {parties.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-medium">{p.name}</TableCell>
                  <TableCell><PartyTypeBadge type={p.type} /></TableCell>
                  <TableCell>{p.phone || "—"}</TableCell>
                  <TableCell>{formatCurrency(p.total_paid)}</TableCell>
                  <TableCell>{formatCurrency(p.total_entitlement)}</TableCell>
                  <TableCell className={p.balance < 0 ? "text-red-600 font-semibold" : "text-green-600 font-semibold"}>
                    {formatCurrency(p.balance)}
                  </TableCell>
                  <TableCell>
                    <span className={`status-badge ${p.is_active ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}>
                      {p.is_active ? "نشط" : "غير نشط"}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button size="sm" variant="ghost" onClick={() => handleView(p)}><Eye className="h-4 w-4" /></Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {pages > 1 && (
            <div className="flex items-center justify-between p-4 border-t">
              <span className="text-sm text-muted-foreground">إجمالي {total} طرف</span>
              <div className="flex gap-1">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage(page - 1)}>السابق</Button>
                <span className="flex items-center px-3 text-sm">{page} / {pages}</span>
                <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => setPage(page + 1)}>التالي</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* View Dialog with Tabs */}
      <Dialog open={viewOpen} onOpenChange={setViewOpen}>
        <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
          <DialogHeader><DialogTitle>كشف الطرف</DialogTitle></DialogHeader>
          {selectedParty && (
            <Tabs defaultValue="info">
              <TabsList>
                <TabsTrigger value="info">البيانات</TabsTrigger>
                <TabsTrigger value="payments">الدفعات</TabsTrigger>
                <TabsTrigger value="entitlements">المستحقات</TabsTrigger>
              </TabsList>
              <TabsContent value="info">
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div><p className="text-xs text-muted-foreground">الاسم</p><p className="font-medium">{selectedParty.name}</p></div>
                  <div><p className="text-xs text-muted-foreground">النوع</p><PartyTypeBadge type={selectedParty.type} /></div>
                  <div><p className="text-xs text-muted-foreground">الهاتف</p><p>{selectedParty.phone || "—"}</p></div>
                  <div><p className="text-xs text-muted-foreground">البريد</p><p>{selectedParty.email || "—"}</p></div>
                  <div><p className="text-xs text-muted-foreground">إجمالي المدفوع</p><p className="font-bold">{formatCurrency(selectedParty.total_paid)}</p></div>
                  <div><p className="text-xs text-muted-foreground">إجمالي المستحقات</p><p className="font-bold">{formatCurrency(selectedParty.total_entitlement)}</p></div>
                  <div><p className="text-xs text-muted-foreground">الرصيد</p><p className={`font-bold text-lg ${selectedParty.balance < 0 ? "text-red-600" : "text-green-600"}`}>{formatCurrency(selectedParty.balance)}</p></div>
                </div>
              </TabsContent>
              <TabsContent value="payments">
                <div className="mt-4">
                  {partyPayments.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">لا توجد دفعات</p>
                  ) : (
                    <Table>
                      <TableHeader><TableRow><TableHead>الوصف</TableHead><TableHead>المبلغ</TableHead><TableHead>التاريخ</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {partyPayments.map((p) => (
                          <TableRow key={p.id}><TableCell>{p.description}</TableCell><TableCell>{formatCurrency(p.amount)}</TableCell><TableCell>{formatDate(p.payment_date)}</TableCell></TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </TabsContent>
              <TabsContent value="entitlements">
                <div className="mt-4">
                  {partyEntitlements.length === 0 ? (
                    <p className="text-center text-muted-foreground py-8">لا توجد مستحقات</p>
                  ) : (
                    <Table>
                      <TableHeader><TableRow><TableHead>الفترة</TableHead><TableHead>صافي المبلغ</TableHead><TableHead>الحالة</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {partyEntitlements.map((ent) => (
                          <TableRow key={ent.id}>
                            <TableCell>{formatDate(ent.period_start)} - {formatDate(ent.period_end)}</TableCell>
                            <TableCell>{formatCurrency(ent.net_amount)}</TableCell>
                            <TableCell><span className={`status-badge ${ent.status === "paid" ? "bg-green-100 text-green-800" : ent.status === "calculated" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800"}`}>{ent.status === "paid" ? "مدفوع" : ent.status === "calculated" ? "محسوب" : "معلق"}</span></TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
