import "server-only";
import { readFile } from "node:fs/promises";
import path from "node:path";
import type { AiNotReady, AiPerformance, AiPrediction } from "./contracts";

const publishedRoot = path.join(process.cwd(), "ai", "published");
const missingModel: AiNotReady = { status: "NOT_READY", reason: "NO_APPROVED_MODEL", message: "承認済みの実データモデルがまだ公開されていません。AI予想準備中です。" };
const safeRaceId = (raceId: string) => /^[a-zA-Z0-9_-]+$/.test(raceId);
async function jsonFile<T>(file: string): Promise<T | null> { try { return JSON.parse(await readFile(file, "utf8")) as T; } catch { return null; } }
async function modelReady(): Promise<boolean> {
  const manifest = await jsonFile<{ active_model?: { contains_synthetic?: boolean; version?: string } }>(path.join(publishedRoot, "active-model.json"));
  return Boolean(manifest?.active_model?.version && manifest.active_model.contains_synthetic === false);
}
export async function getAiStatus(): Promise<{ status: "READY" } | AiNotReady> {
  return (await modelReady()) ? { status: "READY" } : missingModel;
}
export async function getAiPrediction(raceId: string): Promise<AiPrediction | AiNotReady> {
  if (!(await modelReady())) return missingModel;
  if (!safeRaceId(raceId)) return { status: "NOT_READY", reason: "INVALID_PUBLISHED_DATA", message: "予測データを安全に読み込めませんでした。" };
  const prediction = await jsonFile<AiPrediction>(path.join(publishedRoot, "predictions", `${raceId}.json`));
  if (!prediction || prediction.race_id !== raceId || !Array.isArray(prediction.predictions)) return { status: "NOT_READY", reason: "MISSING_PREDICTION", message: "このレースの承認済みAI予想はまだ公開されていません。" };
  return { ...prediction, status: "READY" };
}
export async function getAiPerformance(): Promise<AiPerformance> {
  if (!(await modelReady())) return missingModel;
  const performance = await jsonFile<Omit<Extract<AiPerformance, { status: "READY" }>, "status">>(path.join(publishedRoot, "performance.json"));
  if (!performance || !Number.isInteger(performance.races_evaluated)) return { status: "NOT_READY", reason: "UNAVAILABLE", message: "保存済みの実予測と確定結果がそろうと、予想成績を表示します。" };
  return { ...performance, status: "READY" };
}
