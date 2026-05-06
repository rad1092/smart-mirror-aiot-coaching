import type { ModeType } from "../pages/ModePage";
import { delay, mockFallbackByMode, mockResultByMode } from "../mocks/results";
import type { ResultCard, ResultCardType, ResultData } from "../types/result";

export type { ResultData } from "../types/result";

export function normalizeResultData(raw: unknown): ResultData {
  const wrapper = (raw ?? {}) as Record<string, unknown>;
  const session =
    typeof wrapper.session === "object" && wrapper.session !== null
      ? (wrapper.session as Record<string, unknown>)
      : null;
  const analyze =
    typeof wrapper.analyze === "object" && wrapper.analyze !== null
      ? (wrapper.analyze as Record<string, unknown>)
      : null;
  const finalData =
    typeof wrapper.final === "object" && wrapper.final !== null
      ? (wrapper.final as Record<string, unknown>)
      : null;

  const payload = finalData ?? analyze ?? wrapper;
  const sessionId = String(payload.session_id ?? session?.session_id ?? "");
  const modeRaw = String(payload.mode ?? wrapper.mode ?? "");
  const mode = (modeRaw || "grooming") as ModeType | string;

  const coaching =
    typeof payload.coaching === "object" && payload.coaching !== null
      ? (payload.coaching as Record<string, unknown>)
      : null;
  const coachingSummary = coaching ? String(coaching.summary ?? "") : "";

  if (analyze?.type === "exercise_update") {
    const exercise =
      typeof analyze.exercise === "object" && analyze.exercise !== null
        ? (analyze.exercise as Record<string, unknown>)
        : null;
    const count = exercise ? Number(exercise.count ?? 0) : 0;
    const state = exercise ? String(exercise.state ?? "") : "";
    const feedback = String(analyze.feedback ?? coachingSummary ?? "운동 프레임 분석이 완료되었습니다.");

    const checklist: string[] = [`스쿼트 카운트: ${count}`, `현재 상태: ${state || "unknown"}`];
    if (coaching && Array.isArray(coaching.warnings)) {
      for (const warning of coaching.warnings) {
        checklist.push(`주의: ${String(warning)}`);
      }
    }

    return {
      session_id: sessionId,
      mode: "exercise",
      summary: coachingSummary || feedback,
      cards: [
        {
          type: "posture",
          title: "운동 피드백",
          content: feedback,
        },
        ...(coachingSummary
          ? [
              {
                type: "posture" as ResultCardType,
                title: "최종 코칭 요약",
                content: coachingSummary,
              },
            ]
          : []),
      ],
      checklist,
      fallback: false,
    };
  }

  const cards: ResultCard[] = [];
  if (coachingSummary) {
    const cardType: ResultCardType = mode === "outfit" ? "outfit" : mode === "outing" ? "outing" : "grooming";
    cards.push({
      type: cardType,
      title: "AI 코칭 요약",
      content: coachingSummary,
    });
  }

  const features =
    typeof payload.features === "object" && payload.features !== null
      ? (payload.features as Record<string, unknown>)
      : null;
  const face = features && typeof features.face === "object" ? (features.face as Record<string, unknown>) : null;
  const outfit = features && typeof features.outfit === "object" ? (features.outfit as Record<string, unknown>) : null;

  if (face) {
    cards.push({
      type: "grooming",
      title: "얼굴 피처",
      content: `brightness ${Number(face.brightness ?? 0).toFixed(2)}, redness ${Number(face.redness ?? 0).toFixed(
        2,
      )}, beard_shadow ${Number(face.beard_shadow ?? 0).toFixed(2)}`,
    });
  }

  if (outfit) {
    const top =
      typeof outfit.top_color === "object" && outfit.top_color !== null
        ? (outfit.top_color as Record<string, unknown>)
        : null;
    const bottom =
      typeof outfit.bottom_color === "object" && outfit.bottom_color !== null
        ? (outfit.bottom_color as Record<string, unknown>)
        : null;
    cards.push({
      type: mode === "outing" ? "outing" : "outfit",
      title: "착장 피처",
      content: `top ${String(top?.name ?? "unknown")}, bottom ${String(bottom?.name ?? "unknown")}`,
    });
  }

  const checklist: string[] = [];
  if (coaching && Array.isArray(coaching.routine)) {
    for (const routine of coaching.routine) {
      if (typeof routine === "object" && routine !== null) {
        const item = routine as Record<string, unknown>;
        checklist.push(`${String(item.title ?? "루틴")}: ${String(item.description ?? "")}`);
      }
    }
  }
  if (coaching && Array.isArray(coaching.actions)) {
    for (const action of coaching.actions) {
      checklist.push(String(action));
    }
  }
  if (coaching && Array.isArray(coaching.warnings)) {
    for (const warning of coaching.warnings) {
      checklist.push(`주의: ${String(warning)}`);
    }
  }
  if (coaching && coaching.priority) {
    checklist.push(`우선순위: ${String(coaching.priority)}`);
  }
  if (coaching && coaching.mirror_message) {
    checklist.push(`미러 메시지: ${String(coaching.mirror_message)}`);
  }

  if (checklist.length === 0) {
    checklist.push("세부 권장 항목이 없어서 요약 결과를 확인해주세요.");
  }

  return {
    session_id: sessionId,
    mode,
    summary: coachingSummary || "분석이 완료되었습니다.",
    cards,
    checklist,
    fallback: false,
  };
}

export class AnalyzeError extends Error {
  status: number;
  code: string;
  fallback: boolean;

  constructor(message: string, status: number, code: string, fallback = false) {
    super(message);
    this.name = "AnalyzeError";
    this.status = status;
    this.code = code;
    this.fallback = fallback;
  }
}

export type AnalyzeRequest = {
  mode: ModeType;
  file: File;
  signal: AbortSignal;
};

export type SessionStartResponse = {
  session_id: string;
  ws_url: string;
  mode: string;
  status: string;
};

export type ExerciseRealtimeMessage = {
  type: "exercise_update";
  session_id: string;
  count: number;
  state: string;
  feedback: string;
};

export type MockScenario = "success" | "fallback" | "error_500" | "error_503" | "error_504" | "error_413";

const API_MODE = (import.meta.env.VITE_API_MODE ?? "mock") as "mock" | "real";
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:9000") as string;
const MOCK_SCENARIO = (import.meta.env.VITE_MOCK_SCENARIO ?? "success") as MockScenario;
const MOCK_DELAY_MS = Number(import.meta.env.VITE_MOCK_DELAY_MS ?? 1200);

async function analyzeWithMock(req: AnalyzeRequest): Promise<ResultData> {
  const { mode, signal } = req;
  await delay(MOCK_DELAY_MS, signal);

  switch (MOCK_SCENARIO) {
    case "fallback":
      return mockFallbackByMode[mode];
    case "error_500":
      throw new AnalyzeError("서버 내부 오류로 분석에 실패했습니다.", 500, "SERVER_ERROR");
    case "error_503":
      throw new AnalyzeError("분석 서버를 일시적으로 사용할 수 없습니다.", 503, "SERVICE_UNAVAILABLE");
    case "error_504":
      throw new AnalyzeError("분석 요청이 시간 내에 완료되지 않았습니다.", 504, "TIMEOUT");
    case "error_413":
      throw new AnalyzeError("이미지 용량이 너무 큽니다. 더 작은 파일을 사용해주세요.", 413, "PAYLOAD_TOO_LARGE");
    case "success":
    default:
      return mockResultByMode[mode];
  }
}

async function analyzeWithFetch(req: AnalyzeRequest): Promise<ResultData> {
  const { mode, file, signal } = req;

  // Lazy import to avoid loading Tauri runtime in browser-only dev/test scenarios.
  const { invoke } = await import("@tauri-apps/api/core");

  const purpose = mode === "outfit" || mode === "outing" ? "daily" : null;
  const metadata = {
    mode,
    purpose,
  };

  const arrayBuffer = await file.arrayBuffer();
  const imageBytes = Array.from(new Uint8Array(arrayBuffer));

  // External abort propagation: Tauri 2 invoke does not natively accept AbortSignal,
  // so we reject early when aborted before/after the call.
  if (signal.aborted) {
    throw new DOMException("Aborted", "AbortError");
  }

  let aborted = false;
  const onAbort = () => {
    aborted = true;
  };
  signal.addEventListener("abort", onAbort, { once: true });

  try {
    const raw = await invoke<unknown>("submit_analysis", {
      baseUrl: API_BASE_URL,
      imageBytes,
      fileName: file.name || "capture.jpg",
      metadata,
    });

    if (aborted) {
      throw new DOMException("Aborted", "AbortError");
    }

    return normalizeResultData(raw);
  } catch (error) {
    if (aborted || (error instanceof DOMException && error.name === "AbortError")) {
      throw new DOMException("Aborted", "AbortError");
    }

    // Tauri command Err(AnalyzeError) is serialized to a plain object on the JS side.
    if (typeof error === "object" && error !== null && "code" in error && "message" in error) {
      const e = error as { status?: number; code?: string; message?: string };
      throw new AnalyzeError(
        e.message ?? "분석 중 오류가 발생했습니다.",
        typeof e.status === "number" ? e.status : 0,
        typeof e.code === "string" ? e.code : "UNKNOWN",
      );
    }

    if (error instanceof AnalyzeError) {
      throw error;
    }

    const message = error instanceof Error ? error.message : "분석 중 오류가 발생했습니다.";
    throw new AnalyzeError(message, 0, "INVOKE_ERROR");
  } finally {
    signal.removeEventListener("abort", onAbort);
  }
}

export async function analyze(req: AnalyzeRequest): Promise<ResultData> {
  if (API_MODE === "mock") {
    return analyzeWithMock(req);
  }
  return analyzeWithFetch(req);
}

export async function startSession(mode: ModeType, goal?: string): Promise<SessionStartResponse> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_id: "default",
      mode,
      goal: goal ?? (mode === "exercise" ? "squat" : undefined),
    }),
  });

  if (!response.ok) {
    throw new AnalyzeError("세션 시작에 실패했습니다.", response.status, "SESSION_START_FAILED");
  }

  const data = (await response.json()) as SessionStartResponse;
  return data;
}

export async function analyzeExerciseFrame(sessionId: string, file: File): Promise<unknown> {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("file", file, file.name || "capture.jpg");

  const response = await fetch(`${API_BASE_URL}/api/analyze/exercise`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw new AnalyzeError("운동 프레임 분석에 실패했습니다.", response.status, "EXERCISE_ANALYZE_FAILED");
  }

  return response.json();
}

export async function stopSession(sessionId: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/stop`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new AnalyzeError("세션 종료에 실패했습니다.", response.status, "SESSION_STOP_FAILED");
  }

  return response.json();
}
