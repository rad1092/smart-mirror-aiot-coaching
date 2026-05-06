import type { ChangeEvent } from "react";
import { useEffect, useRef, useState } from "react";
import type { NavigateFunction } from "react-router-dom";

import CameraPreview from "../components/CameraPreview";
import Header from "../components/Header";
import {
  AnalyzeError,
  analyzeExerciseFrame,
  normalizeResultData,
  startSession,
  stopSession,
  type ExerciseRealtimeMessage,
} from "../services/api";
import { useLiveCamera } from "../state/useLiveCamera";
import type { ResultData } from "../types/result";
import type { ModeType } from "./ModePage";

const MODE_LABEL: Record<ModeType, string> = {
  exercise: "운동 코칭",
  outing: "외출 전 점검",
  grooming: "얼굴/그루밍 체크",
  outfit: "옷 색상 조합",
};

type CameraPageProps = {
  navigate: NavigateFunction;
  selectedMode: ModeType;
  capturedImageFile: File | null;
  capturedImagePreviewUrl: string | null;
  lastError: string | null;
  setCapturedImageFile: (file: File | null) => void;
  setCapturedImagePreviewUrl: (url: string | null) => void;
  setAnalysisStatus: (status: "idle" | "capturing" | "analyzing" | "success" | "error") => void;
  setResultData: (data: ResultData | null) => void;
  setLastError: (error: string | null) => void;
  startAnalysis: () => void;
};

function CameraPage({
  navigate,
  selectedMode,
  capturedImageFile,
  capturedImagePreviewUrl,
  lastError,
  setCapturedImageFile,
  setCapturedImagePreviewUrl,
  setAnalysisStatus,
  setResultData,
  setLastError,
  startAnalysis,
}: CameraPageProps) {
  const camera = useLiveCamera();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [inputSource, setInputSource] = useState<"camera" | "file">("camera");
  const [exerciseRunning, setExerciseRunning] = useState(false);
  const [exerciseCount, setExerciseCount] = useState(0);
  const [exerciseState, setExerciseState] = useState("idle");
  const [exerciseFeedback, setExerciseFeedback] = useState<string | null>(null);

  const sessionIdRef = useRef<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const loopRef = useRef<number | null>(null);
  const wsKeepAliveRef = useRef<number | null>(null);
  const lastFrameResponseRef = useRef<unknown>(null);

  const stopExerciseLoop = () => {
    if (loopRef.current !== null) {
      window.clearInterval(loopRef.current);
      loopRef.current = null;
    }
  };

  const closeExerciseSocket = () => {
    if (wsKeepAliveRef.current !== null) {
      window.clearInterval(wsKeepAliveRef.current);
      wsKeepAliveRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  };

  useEffect(() => {
    setLastError(null);
    void camera.start();

    return () => {
      stopExerciseLoop();
      closeExerciseSocket();
      camera.stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const acceptFile = (nextFile: File | null) => {
    setCapturedImageFile(nextFile);

    if (capturedImagePreviewUrl) {
      URL.revokeObjectURL(capturedImagePreviewUrl);
    }

    if (nextFile) {
      setInputSource("file");
      setAnalysisStatus("capturing");
      setCapturedImagePreviewUrl(URL.createObjectURL(nextFile));
      setLastError(null);
    } else {
      setAnalysisStatus("idle");
      setCapturedImagePreviewUrl(null);
    }
  };

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    acceptFile(event.target.files?.[0] ?? null);
  };

  const onCaptureClick = async () => {
    try {
      const file = await camera.capture();
      if (!file) {
        setLastError("이미지를 캡처하지 못했습니다. 다시 시도해주세요.");
        return;
      }
      acceptFile(file);
    } catch {
      setLastError("이미지 캡처 중 오류가 발생했습니다.");
    }
  };

  const onStartCameraClick = async () => {
    setInputSource("camera");
    setLastError(null);
    await camera.start();
  };

  const onSelectFileClick = () => {
    setInputSource("file");
    fileInputRef.current?.click();
  };

  const startAnalyze = () => {
    if (selectedMode === "exercise") {
      void startExerciseRealtime();
      return;
    }

    if (!capturedImageFile) {
      setLastError("촬영 파일이 없습니다. 카메라로 캡처하거나 파일을 선택해주세요.");
      return;
    }
    startAnalysis();
  };

  const startExerciseRealtime = async () => {
    if (exerciseRunning) {
      return;
    }

    if (camera.status !== "ready") {
      setLastError("운동 모드는 라이브 카메라가 필요합니다. 먼저 카메라를 시작해주세요.");
      return;
    }

    setLastError(null);
    setAnalysisStatus("analyzing");

    try {
      const session = await startSession("exercise", "squat");
      sessionIdRef.current = session.session_id;

      const ws = new WebSocket(session.ws_url);
      wsRef.current = ws;
      ws.onopen = () => {
        // eslint-disable-next-line no-console
        console.info("[exercise-ws] connected", session.ws_url);
      };
      ws.onerror = () => {
        // eslint-disable-next-line no-console
        console.error("[exercise-ws] error", session.ws_url);
      };
      ws.onclose = (event) => {
        // eslint-disable-next-line no-console
        console.info("[exercise-ws] closed", event.code, event.reason || "no-reason");
      };
      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ExerciseRealtimeMessage;
          if (message.type === "exercise_update") {
            setExerciseCount(Number(message.count ?? 0));
            setExerciseState(String(message.state ?? "idle"));
            setExerciseFeedback(String(message.feedback ?? ""));
          }
        } catch {
          // Ignore malformed WebSocket payloads from transient network noise.
        }
      };

      wsKeepAliveRef.current = window.setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send("ping");
        }
      }, 10000);

      setExerciseRunning(true);
      loopRef.current = window.setInterval(() => {
        void (async () => {
          if (!sessionIdRef.current) {
            return;
          }
          const frame = await camera.capture();
          if (!frame) {
            return;
          }
          lastFrameResponseRef.current = await analyzeExerciseFrame(sessionIdRef.current, frame);
        })().catch((error) => {
          stopExerciseLoop();
          setExerciseRunning(false);
          const message = error instanceof Error ? error.message : "운동 프레임 전송 중 오류가 발생했습니다.";
          setLastError(message);
          setAnalysisStatus("error");
        });
      }, 1500);
    } catch (error) {
      setExerciseRunning(false);
      setAnalysisStatus("error");
      if (error instanceof AnalyzeError) {
        setLastError(error.message);
      } else {
        setLastError("운동 세션 시작에 실패했습니다.");
      }
    }
  };

  const stopExerciseRealtime = async () => {
    const sessionId = sessionIdRef.current;
    stopExerciseLoop();
    closeExerciseSocket();
    setExerciseRunning(false);

    if (!sessionId) {
      setAnalysisStatus("error");
      setLastError("종료할 운동 세션이 없습니다.");
      return;
    }

    try {
      const finalResponse = await stopSession(sessionId);
      const wrapped = {
        mode: "exercise",
        session: { session_id: sessionId },
        analyze: lastFrameResponseRef.current,
        final: finalResponse,
      };

      setResultData(normalizeResultData(wrapped));
      setAnalysisStatus("success");
      setLastError(null);
      navigate("/result", { replace: true });
    } catch (error) {
      setAnalysisStatus("error");
      if (error instanceof AnalyzeError) {
        setLastError(error.message);
      } else {
        setLastError("운동 세션 종료에 실패했습니다.");
      }
    } finally {
      sessionIdRef.current = null;
      lastFrameResponseRef.current = null;
    }
  };

  const cameraInactive = camera.status !== "ready" && camera.status !== "requesting";

  return (
    <main className="page">
      <Header
        title="카메라"
        subtitle={`선택 모드: ${MODE_LABEL[selectedMode]}`}
      />

      {lastError ? (
        <p className="error" role="alert">
          {lastError}
        </p>
      ) : null}

      {camera.errorMessage ? (
        <p className="error" role="alert">
          {camera.errorMessage}
        </p>
      ) : null}

      <section className="stack" aria-label="라이브 카메라">
        <div className="camera-stage">
          <div className="camera-preview">
            <video
              ref={camera.videoRef}
              className="camera-preview__image"
              playsInline
              muted
              style={{ display: camera.status === "ready" ? "block" : "none" }}
            />
            {camera.status !== "ready" ? (
              <div className="camera-preview__empty" role="status">
                {camera.status === "requesting"
                  ? "카메라 권한 요청 중..."
                  : camera.status === "denied"
                    ? "카메라 권한이 필요합니다. 시스템/브라우저 권한을 허용해주세요."
                    : camera.status === "unavailable"
                      ? "사용 가능한 카메라가 없습니다. 파일 선택으로 진행해주세요."
                      : "카메라를 준비 중입니다..."}
              </div>
            ) : null}
          </div>

          <aside className="camera-source-panel" aria-label="입력 방식 선택">
            <h3 className="camera-source-panel__title">입력 선택</h3>
            <button
              type="button"
              className={inputSource === "camera" ? "btn btn--primary" : "btn"}
              onClick={onStartCameraClick}
              disabled={camera.status === "denied" || camera.status === "unavailable"}
            >
              라이브 웹캠
            </button>
            <button
              type="button"
              className={inputSource === "file" ? "btn btn--primary" : "btn"}
              onClick={onSelectFileClick}
            >
              파일 선택
            </button>
            <input
              ref={fileInputRef}
              id="camera-file-input"
              type="file"
              accept="image/*"
              onChange={onFileChange}
              style={{ display: "none" }}
            />
          </aside>
        </div>

        <div className="row">
          {cameraInactive ? (
            <button
              type="button"
              onClick={onStartCameraClick}
              disabled={camera.status === "denied" || camera.status === "unavailable"}
            >
              카메라 시작
            </button>
          ) : (
            <button type="button" onClick={camera.stop}>
              카메라 정지
            </button>
          )}
          <button
            type="button"
            className="btn btn--primary"
            onClick={onCaptureClick}
            disabled={camera.status !== "ready"}
          >
            캡처
          </button>
        </div>
      </section>

      <section className="stack" aria-label="파일에서 선택">
        <label htmlFor="camera-file-input-inline">
          <span>또는 이미지 파일을 직접 선택해주세요.</span>
        </label>
        <input
          id="camera-file-input-inline"
          type="file"
          accept="image/*"
          onChange={onFileChange}
        />
      </section>

      <section aria-label="선택된 이미지">
        <h3>선택된 이미지</h3>
        <CameraPreview previewUrl={capturedImagePreviewUrl} />
      </section>

      <div className="row">
        <button type="button" onClick={() => navigate("/mode")}>
          모드 다시 선택
        </button>
        {selectedMode === "exercise" ? (
          <>
            <button
              type="button"
              className="btn btn--primary"
              onClick={startAnalyze}
              disabled={exerciseRunning || camera.status !== "ready"}
            >
              운동 시작
            </button>
            <button type="button" onClick={stopExerciseRealtime} disabled={!exerciseRunning}>
              운동 종료
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn btn--primary"
            onClick={startAnalyze}
            disabled={!capturedImageFile}
          >
            분석 시작
          </button>
        )}
      </div>

      {selectedMode === "exercise" ? (
        <section className="checklist" aria-label="운동 실시간 상태">
          <h3 className="checklist__title">운동 실시간 상태</h3>
          <ul className="checklist__list">
            <li className="checklist__item">카운트: {exerciseCount}</li>
            <li className="checklist__item">상태: {exerciseState}</li>
            <li className="checklist__item">피드백: {exerciseFeedback ?? "-"}</li>
          </ul>
        </section>
      ) : null}
    </main>
  );
}

export default CameraPage;
