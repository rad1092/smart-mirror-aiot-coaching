import type { NavigateFunction } from "react-router-dom";

import Checklist from "../components/Checklist";
import Header from "../components/Header";
import ResultCard from "../components/ResultCard";
import type { ResultData } from "../types/result";
import type { ModeType } from "./ModePage";

type ResultPageProps = {
  navigate: NavigateFunction;
  selectedMode: ModeType;
  resultData: ResultData;
  onResetFlowState: () => void;
  setSelectedMode: (mode: ModeType | null) => void;
};

function ResultPage({
  navigate,
  selectedMode,
  resultData,
  onResetFlowState,
  setSelectedMode,
}: ResultPageProps) {
  return (
    <main className="page">
      <Header
        title="결과 카드"
        subtitle={resultData.fallback ? "분석 완료 (일부 기능 제한)" : "분석이 완료되었습니다."}
      />

      <p>{resultData.summary}</p>

      <section className="stack" aria-label="결과 카드 목록">
        {resultData.cards.map((card) => (
          <ResultCard key={`${card.type}-${card.title}`} card={card} />
        ))}
      </section>

      <Checklist items={resultData.checklist} />

      <div className="row">
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => {
            onResetFlowState();
            setSelectedMode(selectedMode);
            navigate("/camera");
          }}
        >
          같은 모드 다시 분석
        </button>
        <button
          type="button"
          onClick={() => {
            onResetFlowState();
            setSelectedMode(null);
            navigate("/mode");
          }}
        >
          다른 모드 선택
        </button>
        <button
          type="button"
          onClick={() => {
            onResetFlowState();
            setSelectedMode(null);
            navigate("/");
          }}
        >
          처음으로
        </button>
      </div>
    </main>
  );
}

export default ResultPage;
