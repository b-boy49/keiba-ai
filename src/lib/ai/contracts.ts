export type AiReadinessReason = "NO_APPROVED_MODEL" | "INVALID_PUBLISHED_DATA" | "MISSING_PREDICTION" | "UNAVAILABLE";

export type AiNotReady = { status: "NOT_READY"; reason: AiReadinessReason; message: string };
export type AiPrediction = {
  status: "READY"; race_id: string; published_at: string; data_source: string; model_version: string;
  trained_at?: string; approved_at?: string; feature_snapshot_at?: string; probability_policy?: string;
  predictions: Array<{ horse_id: string; horse_name: string; predicted_rank: number; reference_win_score: number; analysis_basis?: string }>;
};
export type AiPerformance = { status: "READY"; published_at: string; data_source: string; races_evaluated: number; top1_winner_hits: number; top1_winner_rate: number | null } | AiNotReady;
