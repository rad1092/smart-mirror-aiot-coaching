import type { ModeType } from "../pages/ModePage";
import type { ResultData } from "../types/result";

export const mockResultByMode: Record<ModeType, ResultData> = {
  grooming: {
    session_id: "session_mock_001",
    mode: "grooming",
    summary: "오늘은 얼굴 정돈과 깔끔한 코디가 잘 어울립니다.",
    cards: [
      { type: "hair", title: "헤어 추천", content: "윗볼륨을 살리고 옆라인을 정리한 스타일을 추천합니다." },
      { type: "grooming", title: "그루밍 추천", content: "눈썹 아래 잔털 정리로 인상을 또렷하게 만들 수 있습니다." },
    ],
    checklist: ["머리 윗볼륨 살리기", "눈썹 아래 잔털 정리"],
  },
  outfit: {
    session_id: "session_mock_002",
    mode: "outfit",
    summary: "네이비 상의와 중립 톤 하의 조합이 안정적입니다.",
    cards: [
      { type: "outfit", title: "코디 추천", content: "네이비 상의에는 베이지 또는 그레이 하의가 잘 어울립니다." },
    ],
    checklist: ["상의/하의 명도 균형 맞추기"],
  },
  outing: {
    session_id: "session_mock_003",
    mode: "outing",
    summary: "외출 전 전체 인상은 깔끔한 편입니다.",
    cards: [
      { type: "outing", title: "외출 점검", content: "얼굴톤과 착장 색상이 무난하게 조화됩니다." },
    ],
    checklist: ["옷 주름 최종 확인", "헤어 라인 정리"],
  },
  exercise: {
    session_id: "session_mock_004",
    mode: "exercise",
    summary: "운동 자세 분석은 시퀀스 기준으로 진행되었습니다.",
    cards: [
      { type: "posture", title: "자세 피드백", content: "어깨가 살짝 말려 보여 가슴 펴기 스트레칭을 추천합니다." },
    ],
    checklist: ["어깨 후인 유지", "호흡 리듬 유지"],
  },
};

export const mockFallbackByMode: Record<ModeType, ResultData> = {
  grooming: {
    session_id: "session_mock_fb_001",
    mode: "grooming",
    summary: "분석 서버 일부 기능이 제한되어 기본 가이드를 제공합니다.",
    cards: [
      { type: "grooming", title: "기본 가이드", content: "얼굴/헤어 정돈 기본 체크리스트를 확인해주세요." },
    ],
    checklist: ["세안 후 보습 확인", "헤어 라인 정리"],
    fallback: true,
  },
  outfit: {
    session_id: "session_mock_fb_002",
    mode: "outfit",
    summary: "분석 서버 일부 기능이 제한되어 기본 가이드를 제공합니다.",
    cards: [
      { type: "outfit", title: "기본 가이드", content: "상의/하의 색상 대비를 확인해주세요." },
    ],
    checklist: ["상의/하의 색상 확인"],
    fallback: true,
  },
  outing: {
    session_id: "session_mock_fb_003",
    mode: "outing",
    summary: "분석 서버 일부 기능이 제한되어 기본 가이드를 제공합니다.",
    cards: [
      { type: "outing", title: "기본 가이드", content: "외출 전 기본 점검 항목을 확인해주세요." },
    ],
    checklist: ["옷 주름 확인", "헤어 라인 정리"],
    fallback: true,
  },
  exercise: {
    session_id: "session_mock_fb_004",
    mode: "exercise",
    summary: "분석 서버 일부 기능이 제한되어 기본 가이드를 제공합니다.",
    cards: [
      { type: "posture", title: "기본 가이드", content: "기본 스트레칭 루틴을 확인해주세요." },
    ],
    checklist: ["가벼운 스트레칭 1분"],
    fallback: true,
  },
};

export function delay(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const timer = window.setTimeout(() => resolve(), ms);
    if (signal) {
      signal.addEventListener(
        "abort",
        () => {
          window.clearTimeout(timer);
          reject(new DOMException("Aborted", "AbortError"));
        },
        { once: true },
      );
    }
  });
}
