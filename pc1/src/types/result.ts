import type { ModeType } from "../pages/ModePage";

export type ResultCardType = "hair" | "grooming" | "outfit" | "outing" | "posture";

export type ResultCard = {
  type: ResultCardType;
  title: string;
  content: string;
};

export type ResultChecklistItem = string;

export type ResultData = {
  session_id: string;
  mode: ModeType | string;
  summary: string;
  cards: ResultCard[];
  checklist: ResultChecklistItem[];
  fallback?: boolean;
};
