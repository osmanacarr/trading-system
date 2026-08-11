// research/publish_summary.py::assemble_summary() ciktisiyla BIREBIR ayni
// sema (research/data/research_summary.json). Python tarafi "tek dogru
// kaynak" - bu dosya sadece TIP olarak yansitir, mantik ICERMEZ.

export interface FactorIcRow {
  factor_name: string;
  mean_ic: number | null;
  n_dates: number;
  decayed: boolean;
  first_half_mean_ic: number | null;
  second_half_mean_ic: number | null;
}

export type RegimeLabel = "low" | "normal" | "high";

export interface RegimeSummary {
  counts: Record<RegimeLabel, number>;
  majority_label: RegimeLabel | null;
  n_symbols: number;
}

export interface EnsembleWeightRow {
  factor_name: string;
  weight: number | null;
}

export interface RedundantFactorPair {
  factor_a: string;
  factor_b: string;
  correlation: number | null;
}

export interface EnsembleSummary {
  weights: EnsembleWeightRow[];
  redundant_pairs: RedundantFactorPair[];
}

export interface AttributionSummary {
  total_common_return: number;
  total_specific_return: number;
  pct_specific: number;
  n_trades: number;
}

export interface RuleBurdenSummary {
  n_filters: number;
  max_filters: number;
  overfitting_risk: boolean;
}

export interface ResearchSummary {
  generated_at: string;
  factor_ic: FactorIcRow[];
  regime: RegimeSummary;
  ensemble: EnsembleSummary;
  attribution: AttributionSummary;
  rule_burden: RuleBurdenSummary;
}
