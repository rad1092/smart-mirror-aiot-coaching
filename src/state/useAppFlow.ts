import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import type { ModeType } from "../pages/ModePage";
import { analyze, AnalyzeError, type ResultData } from "../services/analyze";

export type AnalysisStatus = "idle" | "capturing" | "analyzing" | "success" | "error";

export type AppFlowState = {
  selectedMode: ModeType | null;
  capturedImageFile: File | null;
  capturedImagePreviewUrl: string | null;
  analysisStatus: AnalysisStatus;
  resultData: ResultData | null;
  lastError: string | null;
};

export type AppFlowApi = AppFlowState & {
  setSelectedMode: (mode: ModeType | null) => void;
  setCapturedImageFile: (file: File | null) => void;
  setCapturedImagePreviewUrl: (url: string | null) => void;
  setAnalysisStatus: (status: AnalysisStatus) => void;
  setResultData: (data: ResultData | null) => void;
  setLastError: (message: string | null) => void;
  resetFlowState: () => void;
  startAnalysis: () => void;
};

export function useAppFlow(): AppFlowApi {
  const navigate = useNavigate();
  const location = useLocation();

  const [selectedMode, setSelectedMode] = useState<ModeType | null>(null);
  const [capturedImageFile, setCapturedImageFile] = useState<File | null>(null);
  const [capturedImagePreviewUrl, setCapturedImagePreviewUrl] = useState<string | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState<AnalysisStatus>("idle");
  const [resultData, setResultData] = useState<ResultData | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);

  const inFlightRef = useRef(false);
  const requestKeyRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  const selectedModeRef = useRef<ModeType | null>(null);
  const capturedImageFileRef = useRef<File | null>(null);

  // Refs are kept in sync so startAnalysis sees latest state without re-creating callbacks.
  selectedModeRef.current = selectedMode;
  capturedImageFileRef.current = capturedImageFile;

  // Abort any in-flight request when the hook owner unmounts.
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
    };
  }, []);

  const resetFlowState = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    requestKeyRef.current += 1;
    inFlightRef.current = false;

    if (capturedImagePreviewUrl) {
      URL.revokeObjectURL(capturedImagePreviewUrl);
    }

    setCapturedImageFile(null);
    setCapturedImagePreviewUrl(null);
    setResultData(null);
    setLastError(null);
    setAnalysisStatus("idle");
  };

  // Cancel analyzing when the user navigates away from /loading.
  useEffect(() => {
    if (analysisStatus !== "analyzing") {
      return;
    }

    if (location.pathname !== "/loading") {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }

      requestKeyRef.current += 1;
      inFlightRef.current = false;
      setAnalysisStatus("error");
      setLastError("분석이 취소되었습니다. 다시 시도해주세요.");
    }
  }, [analysisStatus, location.pathname]);

  // When entering Home, reset everything if any flow state is dirty.
  useEffect(() => {
    if (location.pathname !== "/") {
      return;
    }

    if (
      selectedMode ||
      capturedImageFile ||
      capturedImagePreviewUrl ||
      resultData ||
      lastError ||
      analysisStatus !== "idle"
    ) {
      resetFlowState();
      setSelectedMode(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    analysisStatus,
    capturedImageFile,
    capturedImagePreviewUrl,
    lastError,
    location.pathname,
    resultData,
    selectedMode,
  ]);

  const startAnalysis = () => {
    const mode = selectedModeRef.current;
    const file = capturedImageFileRef.current;

    if (!mode || !file) {
      setLastError("분석을 시작할 이미지 파일이 없습니다. 파일을 다시 선택해주세요.");
      setAnalysisStatus("error");
      return;
    }

    if (inFlightRef.current || analysisStatus === "analyzing") {
      return;
    }

    setLastError(null);
    setAnalysisStatus("analyzing");
    navigate("/loading");

    inFlightRef.current = true;
    const requestKey = requestKeyRef.current + 1;
    requestKeyRef.current = requestKey;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const { signal } = abortControllerRef.current;

    analyze({ mode, file, signal })
      .then((data) => {
        if (requestKey !== requestKeyRef.current) {
          return;
        }
        setResultData(data);
        setAnalysisStatus("success");
        setLastError(null);
        navigate("/result", { replace: true });
      })
      .catch((error) => {
        if (requestKey !== requestKeyRef.current) {
          return;
        }
        if (error instanceof DOMException && error.name === "AbortError") {
          return;
        }
        let message = "분석 중 오류가 발생했습니다.";
        if (error instanceof AnalyzeError) {
          message = error.message;
        } else if (error instanceof Error) {
          message = error.message;
        }
        setLastError(message);
        setAnalysisStatus("error");
        navigate("/camera", { replace: true });
      })
      .finally(() => {
        if (requestKey === requestKeyRef.current) {
          abortControllerRef.current = null;
        }
        inFlightRef.current = false;
      });
  };

  return {
    selectedMode,
    capturedImageFile,
    capturedImagePreviewUrl,
    analysisStatus,
    resultData,
    lastError,
    setSelectedMode,
    setCapturedImageFile,
    setCapturedImagePreviewUrl,
    setAnalysisStatus,
    setResultData,
    setLastError,
    resetFlowState,
    startAnalysis,
  };
}
