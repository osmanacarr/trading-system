"use client";

import { useEffect, useState } from "react";
import { computeScheduledJobs, type ScheduledJob } from "@/lib/schedule";
import { Panel } from "./ui/Panel";
import { Badge } from "./ui/Badge";
import { PulseDot } from "./ui/PulseDot";

// "Ne zaman ne haber gelecek" paneli (bkz. ilgili konusma - kullanicinin
// somut sikayeti: "herhangi bir zamanlama bilgisi goremiyorum"). Veri
// dosyasina bagli DEGIL - lib/schedule.ts'teki sabit cron tanimlarindan
// istemci tarafinda hesaplanir, bu yuzden kendi 60sn'lik zamanlayicisi var
// (dashboard'un genel 10sn'lik poll'una ihtiyaci yok).
export function ScanScheduleCard() {
  const [jobs, setJobs] = useState<ScheduledJob[]>(() => computeScheduledJobs());

  useEffect(() => {
    const id = setInterval(() => setJobs(computeScheduledJobs()), 60_000);
    return () => clearInterval(id);
  }, []);

  return (
    <Panel title="tarama takvimi — ne zaman ne haber gelecek">
      <div className="divide-y divide-term-border-soft">
        {jobs.map((job) => (
          <div key={job.id} className="flex items-center gap-2 px-3 py-1.5">
            <PulseDot tone={job.status === "otomatik" ? "green" : "neutral"} live={job.status === "otomatik"} />
            <span className="w-44 shrink-0 text-[11px] text-term-text">{job.label}</span>
            <span className="flex-1 text-[10px] text-term-text-dim">{job.detail}</span>
            {job.status === "deneysel-manuel" && <Badge tone="neutral">🧪 DENEYSEL</Badge>}
          </div>
        ))}
      </div>
    </Panel>
  );
}
