import type { NavigateFunction } from "react-router-dom";

import Header from "../components/Header";
import ModeButton from "../components/ModeButton";

export type ModeType = "exercise" | "outing" | "grooming" | "outfit";

type ModePageProps = {
  navigate: NavigateFunction;
  lastError: string | null;
  onSelectMode: (mode: ModeType) => void;
};

const MODES: Array<{ key: ModeType; label: string; description: string }> = [
  { key: "exercise", label: "운동 코칭", description: "자세 시퀀스를 분석합니다." },
  { key: "outing", label: "외출 전 점검", description: "전체 인상을 점검합니다." },
  { key: "grooming", label: "얼굴/그루밍 체크", description: "얼굴/헤어 정돈 가이드를 제공합니다." },
  { key: "outfit", label: "옷 색상 조합", description: "상의/하의 조합을 제안합니다." },
];

function ModePage({ navigate, lastError, onSelectMode }: ModePageProps) {
  return (
    <main className="page">
      <Header title="모드 선택" subtitle="원하는 분석 모드를 선택해주세요." />
      {lastError ? (
        <p className="error" role="alert">
          {lastError}
        </p>
      ) : null}
      <div className="stack">
        {MODES.map((mode) => (
          <ModeButton
            key={mode.key}
            mode={mode.key}
            label={mode.label}
            description={mode.description}
            onClick={(selected) => {
              onSelectMode(selected);
              navigate("/camera");
            }}
          />
        ))}
      </div>
    </main>
  );
}

export default ModePage;
