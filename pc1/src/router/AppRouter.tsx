import { useEffect } from "react";
import { Navigate, Route, Routes, useNavigate } from "react-router-dom";

import CameraPage from "../pages/CameraPage";
import HomePage from "../pages/HomePage";
import LoadingPage from "../pages/LoadingPage";
import ModePage from "../pages/ModePage";
import ResultPage from "../pages/ResultPage";
import { useAppFlow, type AnalysisStatus } from "../state/useAppFlow";

type RedirectWithErrorProps = {
  to: string;
  message: string;
  setLastError: (message: string | null) => void;
  setAnalysisStatus?: (status: AnalysisStatus) => void;
};

function RedirectWithError({ to, message, setLastError, setAnalysisStatus }: RedirectWithErrorProps) {
  useEffect(() => {
    setLastError(message);
    if (setAnalysisStatus) {
      setAnalysisStatus("error");
    }
  }, [message, setAnalysisStatus, setLastError]);

  return <Navigate to={to} replace />;
}

function AppRouter() {
  const navigate = useNavigate();
  const flow = useAppFlow();

  return (
    <Routes>
      <Route path="/" element={<HomePage navigate={navigate} />} />

      <Route
        path="/mode"
        element={
          <ModePage
            navigate={navigate}
            lastError={flow.lastError}
            onSelectMode={(mode) => {
              flow.resetFlowState();
              flow.setSelectedMode(mode);
            }}
          />
        }
      />

      <Route
        path="/camera"
        element={
          flow.selectedMode ? (
            <CameraPage
              navigate={navigate}
              selectedMode={flow.selectedMode}
              capturedImageFile={flow.capturedImageFile}
              capturedImagePreviewUrl={flow.capturedImagePreviewUrl}
              lastError={flow.lastError}
              setCapturedImageFile={flow.setCapturedImageFile}
              setCapturedImagePreviewUrl={flow.setCapturedImagePreviewUrl}
              setAnalysisStatus={flow.setAnalysisStatus}
              setResultData={flow.setResultData}
              setLastError={flow.setLastError}
              startAnalysis={flow.startAnalysis}
            />
          ) : (
            <RedirectWithError
              to="/mode"
              message="모드�?먼�? ?�택?�주?�요."
              setLastError={flow.setLastError}
            />
          )
        }
      />

      <Route
        path="/loading"
        element={
          !flow.selectedMode ? (
            <RedirectWithError
              to="/mode"
              message="모드�?먼�? ?�택?�주?�요."
              setLastError={flow.setLastError}
              setAnalysisStatus={flow.setAnalysisStatus}
            />
          ) : !flow.capturedImageFile ? (
            <RedirectWithError
              to="/camera"
              message="?��?지 ?�일???�습?�다. 카메???�면?�서 ?��?지�??�택?�주?�요."
              setLastError={flow.setLastError}
              setAnalysisStatus={flow.setAnalysisStatus}
            />
          ) : flow.analysisStatus !== "analyzing" ? (
            <RedirectWithError
              to="/camera"
              message="분석 ?�태가 ?�바르�? ?�습?�다. ?�시 분석???�작?�주?�요."
              setLastError={flow.setLastError}
              setAnalysisStatus={flow.setAnalysisStatus}
            />
          ) : (
            <LoadingPage />
          )
        }
      />

      <Route
        path="/result"
        element={
          flow.resultData && flow.selectedMode ? (
            <ResultPage
              navigate={navigate}
              selectedMode={flow.selectedMode}
              resultData={flow.resultData}
              onResetFlowState={flow.resetFlowState}
              setSelectedMode={flow.setSelectedMode}
            />
          ) : (
            <Navigate to="/mode" replace />
          )
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default AppRouter;
