"use client";

import React, { useState } from "react";
import { api } from "@/lib/api";
import { useToast } from "@/components/ui/toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { PageLoader, EmptyState } from "@/components/shared/loading";
import { StatusBadge } from "@/components/shared/status-badge";
import { formatCurrency, formatDate, downloadJSON } from "@/lib/utils";
import type { CustodyStatement, PartyLedger, ProjectSummary, Custody, SelectOption } from "@/types";
import {
  FileText,
  Download,
  Shield,
  Users,
  FolderOpen,
  AlertTriangle,
} from "lucide-react";

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState("custody-statement");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Custody Statement
  const [custodyStatement, setCustodyStatement] = useState<CustodyStatement | null>(null);
  const [selectedCustodyId, setSelectedCustodyId] = useState("");
  const [custodies, setCustodies] = useState<SelectOption[]>([]);

  // Party Ledger
  const [partyLedger, setPartyLedger] = useState<PartyLedger | null>(null);
  const [selectedPartyId, setSelectedPartyId] = useState("");
  const [parties, setParties] = useState<SelectOption[]>([]);

  // Project Summary
  const [projectSummary, setProjectSummary] = useState<ProjectSummary | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [projects, setProjects] = useState<SelectOption[]>([]);

  // Open Custodies
  const [openCustodies, setOpenCustodies] = useState<Custody[]>([]);
  const [openCustodiesLoaded, setOpenCustodiesLoaded] = useState(false);

  const { addToast } = useToast();

  // Load dropdowns
  React.useEffect(() => {
    Promise.all([
      api.getCustodies().then((data: unknown) => setCustodies(data as SelectOption[])).catch(() => {}),
      api.getParties().then((data: unknown) => setParties(data as SelectOption[])).catch(() => {}),
      api.getProjects().then((data: unknown) => setProjects(data as SelectOption[])).catch(() => {}),
    ]);
  }, []);

  const handleCustodyStatement = async () => {
    if (!selectedCustodyId) return;
    try {
      setLoading(true);
      setError("");
      const data = await api.get<CustodyStatement>(`/api/v1/reports/custody-statement/${selectedCustodyId}`);
      setCustodyStatement(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل تحميل التقرير");
    } finally {
      setLoading(false);
    }
  };

  const handlePartyLedger = async () => {
    if (!selectedPartyId) return;
    try {
      setLoading(true);
      setError("");
      const data = await api.get<PartyLedger>(`/api/v1/reports/party-ledger/${selectedPartyId}`);
      setPartyLedger(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل تحميل التقرير");
    } finally {
      setLoading(false);
    }
  };

  const handleProjectSummary = async () => {
    if (!selectedProjectId) return;
    try {
      setLoading(true);
      setError("");
      const data = await api.get<ProjectSummary>(`/api/v1/reports/project-summary/${selectedProjectId}`);
      setProjectSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل تحميل التقرير");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenCustodies = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await api.get<Custody[]>("/api/v1/reports/open-custodies");
      setOpenCustodies(data);
      setOpenCustodiesLoaded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل تحميل التقرير");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="page-header">
        <div>
          <h1 className="page-title">التقارير</h1>
          <p className="page-description">عرض وتصدير التقارير المالية</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-sm">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="custody-statement">
            <Shield className="h-4 w-4 ms-2" />
            كشف العهدة
          </TabsTrigger>
          <TabsTrigger value="party-ledger">
            <Users className="h-4 w-4 ms-2" />
            دفتر الطرف
          </TabsTrigger>
          <TabsTrigger value="project-summary">
            <FolderOpen className="h-4 w-4 ms-2" />
            ملخص المشروع
          </TabsTrigger>
          <TabsTrigger value="open-custodies">
            <AlertTriangle className="h-4 w-4 ms-2" />
            العهد المفتوحة
          </TabsTrigger>
        </TabsList>

        {/* Custody Statement */}
        <TabsContent value="custody-statement">
          <Card>
            <CardHeader>
              <CardTitle>كشف العهدة</CardTitle>
              <CardDescription>عرض تفصيلي لحركة عهدة محددة</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 items-end flex-wrap">
                <div className="flex-1 min-w-[250px] space-y-2">
                  <Label>اختر العهدة</Label>
                  <Select value={selectedCustodyId} onValueChange={setSelectedCustodyId}>
                    <SelectTrigger><SelectValue placeholder="اختر عهدة" /></SelectTrigger>
                    <SelectContent>
                      {custodies.map((c) => <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleCustodyStatement} disabled={!selectedCustodyId || loading}>
                  عرض التقرير
                </Button>
                {custodyStatement && (
                  <Button variant="outline" onClick={() => downloadJSON(custodyStatement, `custody-statement-${selectedCustodyId}`)}>
                    <Download className="h-4 w-4" />
                    تصدير
                  </Button>
                )}
              </div>

              {loading && <PageLoader />}

              {custodyStatement && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div><p className="text-xs text-muted-foreground">المبلغ</p><p className="font-bold">{formatCurrency(custodyStatement.custody.amount)}</p></div>
                    <div><p className="text-xs text-muted-foreground">المتبقي</p><p className="font-bold text-amber-600">{formatCurrency(custodyStatement.custody.remaining_amount)}</p></div>
                    <div><p className="text-xs text-muted-foreground">الحالة</p><StatusBadge status={custodyStatement.custody.status} /></div>
                    <div><p className="text-xs text-muted-foreground">الحامل</p><p>{custodyStatement.custody.holder_name}</p></div>
                  </div>

                  <h3 className="font-semibold mt-4">المصروفات</h3>
                  {custodyStatement.expenses.length === 0 ? (
                    <p className="text-muted-foreground text-sm">لا توجد مصروفات</p>
                  ) : (
                    <Table>
                      <TableHeader><TableRow><TableHead>الوصف</TableHead><TableHead>المبلغ</TableHead><TableHead>الحالة</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {custodyStatement.expenses.map((e) => (
                          <TableRow key={e.id}><TableCell>{e.description}</TableCell><TableCell>{formatCurrency(e.amount)}</TableCell><TableCell><StatusBadge status={e.status} /></TableCell></TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Party Ledger */}
        <TabsContent value="party-ledger">
          <Card>
            <CardHeader>
              <CardTitle>دفتر الطرف</CardTitle>
              <CardDescription>عرض كامل لجميع الحركات المالية لطرف محدد</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 items-end flex-wrap">
                <div className="flex-1 min-w-[250px] space-y-2">
                  <Label>اختر الطرف</Label>
                  <Select value={selectedPartyId} onValueChange={setSelectedPartyId}>
                    <SelectTrigger><SelectValue placeholder="اختر طرف" /></SelectTrigger>
                    <SelectContent>
                      {parties.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handlePartyLedger} disabled={!selectedPartyId || loading}>
                  عرض التقرير
                </Button>
                {partyLedger && (
                  <Button variant="outline" onClick={() => downloadJSON(partyLedger, `party-ledger-${selectedPartyId}`)}>
                    <Download className="h-4 w-4" />
                    تصدير
                  </Button>
                )}
              </div>

              {loading && <PageLoader />}

              {partyLedger && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div><p className="text-xs text-muted-foreground">إجمالي المدفوع</p><p className="font-bold text-green-600">{formatCurrency(partyLedger.party.total_paid)}</p></div>
                    <div><p className="text-xs text-muted-foreground">إجمالي المستحقات</p><p className="font-bold">{formatCurrency(partyLedger.party.total_entitlement)}</p></div>
                    <div><p className="text-xs text-muted-foreground">الرصيد</p><p className={`font-bold text-lg ${partyLedger.party.balance < 0 ? "text-red-600" : "text-green-600"}`}>{formatCurrency(partyLedger.party.balance)}</p></div>
                  </div>

                  <h3 className="font-semibold">الدفعات</h3>
                  {partyLedger.payments.length === 0 ? (
                    <p className="text-muted-foreground text-sm">لا توجد دفعات</p>
                  ) : (
                    <Table>
                      <TableHeader><TableRow><TableHead>الوصف</TableHead><TableHead>المبلغ</TableHead><TableHead>التاريخ</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {partyLedger.payments.map((p) => (
                          <TableRow key={p.id}><TableCell>{p.description}</TableCell><TableCell>{formatCurrency(p.amount)}</TableCell><TableCell>{formatDate(p.payment_date)}</TableCell></TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Project Summary */}
        <TabsContent value="project-summary">
          <Card>
            <CardHeader>
              <CardTitle>ملخص المشروع</CardTitle>
              <CardDescription>عرض ملخص شامل لمشروع محدد</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3 items-end flex-wrap">
                <div className="flex-1 min-w-[250px] space-y-2">
                  <Label>اختر المشروع</Label>
                  <Select value={selectedProjectId} onValueChange={setSelectedProjectId}>
                    <SelectTrigger><SelectValue placeholder="اختر مشروع" /></SelectTrigger>
                    <SelectContent>
                      {projects.map((p) => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <Button onClick={handleProjectSummary} disabled={!selectedProjectId || loading}>
                  عرض التقرير
                </Button>
                {projectSummary && (
                  <Button variant="outline" onClick={() => downloadJSON(projectSummary, `project-summary-${selectedProjectId}`)}>
                    <Download className="h-4 w-4" />
                    تصدير
                  </Button>
                )}
              </div>

              {loading && <PageLoader />}

              {projectSummary && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div><p className="text-xs text-muted-foreground">إجمالي العهد</p><p className="font-bold">{formatCurrency(projectSummary.total_custody_amount)}</p></div>
                    <div><p className="text-xs text-muted-foreground">إجمالي المصروفات</p><p className="font-bold text-red-600">{formatCurrency(projectSummary.total_expenses)}</p></div>
                    <div><p className="text-xs text-muted-foreground">إجمالي الدفعات</p><p className="font-bold text-green-600">{formatCurrency(projectSummary.total_payments)}</p></div>
                  </div>

                  <h3 className="font-semibold">العهد في المشروع</h3>
                  {projectSummary.custodies.length === 0 ? (
                    <p className="text-muted-foreground text-sm">لا توجد عهد</p>
                  ) : (
                    <Table>
                      <TableHeader><TableRow><TableHead>الوصف</TableHead><TableHead>المبلغ</TableHead><TableHead>المتبقي</TableHead><TableHead>الحالة</TableHead></TableRow></TableHeader>
                      <TableBody>
                        {projectSummary.custodies.map((c) => (
                          <TableRow key={c.id}><TableCell>{c.description}</TableCell><TableCell>{formatCurrency(c.amount)}</TableCell><TableCell>{formatCurrency(c.remaining_amount)}</TableCell><TableCell><StatusBadge status={c.status} /></TableCell></TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Open Custodies */}
        <TabsContent value="open-custodies">
          <Card>
            <CardHeader>
              <CardTitle>تقرير العهد المفتوحة</CardTitle>
              <CardDescription>عرض جميع العهد المفتوحة والمتأخرة</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-3">
                <Button onClick={handleOpenCustodies} disabled={loading}>
                  تحميل التقرير
                </Button>
                {openCustodiesLoaded && (
                  <Button variant="outline" onClick={() => downloadJSON(openCustodies, "open-custodies-report")}>
                    <Download className="h-4 w-4" />
                    تصدير
                  </Button>
                )}
              </div>

              {loading && <PageLoader />}

              {openCustodiesLoaded && openCustodies.length === 0 ? (
                <EmptyState icon={<Shield className="h-12 w-12" />} title="لا توجد عهد مفتوحة" />
              ) : openCustodiesLoaded && (
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
                        <TableHead>تاريخ الاستحقاق</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {openCustodies.map((c) => (
                        <TableRow key={c.id}>
                          <TableCell className="font-medium">{c.description}</TableCell>
                          <TableCell>{c.holder_name}</TableCell>
                          <TableCell>{c.project_name}</TableCell>
                          <TableCell>{formatCurrency(c.amount)}</TableCell>
                          <TableCell>{formatCurrency(c.remaining_amount)}</TableCell>
                          <TableCell><StatusBadge status={c.status} /></TableCell>
                          <TableCell>{formatDate(c.due_date)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
