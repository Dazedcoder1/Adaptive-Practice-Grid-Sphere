"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, Gauge, ThumbsUp, Wallet } from "lucide-react";
import { useState } from "react";
import { StatCard } from "@/components/dashboard/stat-card";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { ApiError } from "@/services/api";
import { aiApi } from "../ai-api";
import { AiHeader } from "./ai-tabs";

const errMsg = (e: unknown) => (e instanceof ApiError ? e.message : "Something went wrong.");
const n = (x: number) => x.toLocaleString("en-IN");
const usd = (x: number) => `$${x.toFixed(x && x < 0.01 ? 4 : 2)}`;
const FEATURE: Record<string, string> = { tutor: "Tutor replies", embedding: "Embeddings", test: "Admin tests" };
const SOURCE: Record<string, string> = { ai: "AI", notes: "Study notes", safety: "Wellbeing reply" };
const FLAG: Record<string, string> = {
  answer_withheld: "Answer held back",
  citation_removed: "Invalid citation removed",
  instructions_withheld: "Rules echo blocked",
  possible_injection: "Possible prompt injection",
  wellbeing: "Wellbeing reply",
  daily_limit: "Student daily limit hit",
  budget: "Platform budget hit",
  ai_unavailable: "Provider unavailable",
  not_configured: "No provider (notes mode)",
  disabled: "AI turned off",
  counts_as_hint: "Counted as a hint",
  hint_revealed: "Authored hint shown",
  truncated: "Reply truncated",
};

export function AiUsagePage() {
  const [days, setDays] = useState(14);
  const r = useQuery({ queryKey: ["admin", "ai", "usage", days], queryFn: () => aiApi.usage(days) });

  return (
    <>
      <AiHeader
        actions={
          <Select value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </Select>
        }
      />
      {r.isLoading ? (
        <LoadingState />
      ) : r.isError || !r.data ? (
        <ErrorState message={errMsg(r.error)} onRetry={() => void r.refetch()} />
      ) : (
        (() => {
          const d = r.data;
          const calls = d.by_feature.reduce((a, f) => a + f.calls, 0);
          const errors = d.by_feature.reduce((a, f) => a + f.errors, 0);
          const cost = d.by_day.reduce((a, x) => a + x.cost_usd, 0);
          const rated = d.helpful.yes + d.helpful.no;
          const tutorRow = d.by_feature.find((f) => f.feature === "tutor");
          return (
            <div className="space-y-6">
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="Provider calls"
                  value={n(calls)}
                  icon={Activity}
                  hint={`${errors} failed`}
                  tone={errors ? "warning" : "default"}
                />
                <StatCard
                  label="Estimated cost"
                  value={usd(cost)}
                  icon={Wallet}
                  hint={
                    d.prices_set
                      ? `Today ${usd(d.today_cost_usd)} of ${usd(d.daily_cost_limit_usd)}`
                      : "Set prices in Overview to estimate cost"
                  }
                />
                <StatCard
                  label="Tutor latency (p95)"
                  value={tutorRow ? `${(tutorRow.p95_ms / 1000).toFixed(1)} s` : "—"}
                  icon={Gauge}
                  hint={tutorRow ? `median ${(tutorRow.p50_ms / 1000).toFixed(1)} s` : "No AI replies yet"}
                />
                <StatCard
                  label="Rated helpful"
                  value={rated ? `${Math.round((d.helpful.yes / rated) * 100)}%` : "—"}
                  icon={ThumbsUp}
                  hint={`${rated} ratings`}
                />
              </div>

              {!calls && !d.replies.length ? (
                <Card>
                  <EmptyState
                    title="No AI activity in this period"
                    description="Usage appears here once students use the tutor."
                  />
                </Card>
              ) : (
                <div className="grid gap-6 xl:grid-cols-2">
                  <Card>
                    <CardHeader>
                      <CardTitle>By day</CardTitle>
                    </CardHeader>
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent">
                          <TableHead>Day</TableHead>
                          <TableHead className="text-right">Calls</TableHead>
                          <TableHead className="text-right">Tokens in / out</TableHead>
                          <TableHead className="text-right">Cost</TableHead>
                          <TableHead className="text-right">Errors</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {[...d.by_day].reverse().map((x) => (
                          <TableRow key={x.day}>
                            <TableCell>
                              {new Date(x.day).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{n(x.calls)}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {n(x.input_tokens)} / {n(x.output_tokens)}
                            </TableCell>
                            <TableCell className="text-right tabular-nums">{usd(x.cost_usd)}</TableCell>
                            <TableCell className="text-right tabular-nums">
                              {x.errors}
                              {x.fallbacks ? ` · ${x.fallbacks} fallback` : ""}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Card>

                  <div className="space-y-6">
                    <Card>
                      <CardHeader>
                        <CardTitle>By feature</CardTitle>
                      </CardHeader>
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent">
                            <TableHead>Feature</TableHead>
                            <TableHead className="text-right">Calls</TableHead>
                            <TableHead className="text-right">Tokens</TableHead>
                            <TableHead className="text-right">p50 / p95</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {d.by_feature.map((f) => (
                            <TableRow key={f.feature}>
                              <TableCell>{FEATURE[f.feature] ?? f.feature}</TableCell>
                              <TableCell className="text-right tabular-nums">{n(f.calls)}</TableCell>
                              <TableCell className="text-right tabular-nums">{n(f.tokens)}</TableCell>
                              <TableCell className="text-right tabular-nums">
                                {f.p50_ms} / {f.p95_ms} ms
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </Card>
                    <Card>
                      <CardHeader>
                        <CardTitle>Tutor replies and safeguards</CardTitle>
                      </CardHeader>
                      <CardContent className="grid gap-6 sm:grid-cols-2">
                        <div>
                          <p className="text-muted-foreground mb-2 text-xs font-medium">How replies were produced</p>
                          <ul className="space-y-1 text-sm">
                            {Object.entries(
                              d.replies.reduce<Record<string, number>>(
                                (a, x) => ({ ...a, [x.source]: (a[x.source] ?? 0) + x.count }),
                                {},
                              ),
                            ).map(([s, c]) => (
                              <li key={s} className="flex justify-between">
                                <span>{SOURCE[s] ?? s}</span>
                                <span className="tabular-nums">{n(c)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                        <div>
                          <p className="text-muted-foreground mb-2 text-xs font-medium">Guardrails triggered</p>
                          {Object.keys(d.flags).length ? (
                            <ul className="space-y-1 text-sm">
                              {Object.entries(d.flags)
                                .sort((a, b) => b[1] - a[1])
                                .map(([f, c]) => (
                                  <li key={f} className="flex justify-between gap-3">
                                    <span>{FLAG[f] ?? f}</span>
                                    <span className="tabular-nums">{n(c)}</span>
                                  </li>
                                ))}
                            </ul>
                          ) : (
                            <p className="text-muted-foreground text-sm">None</p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                    {d.errors.length > 0 && (
                      <Card>
                        <CardHeader>
                          <CardTitle>Provider errors</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-1 text-sm">
                            {d.errors.map((e) => (
                              <li key={e.code} className="flex justify-between">
                                <code className="text-xs">{e.code}</code>
                                <span className="tabular-nums">{e.count}</span>
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })()
      )}
    </>
  );
}
