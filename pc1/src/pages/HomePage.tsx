import type { NavigateFunction } from "react-router-dom";

import Header from "../components/Header";

type HomePageProps = {
  navigate: NavigateFunction;
};

function HomePage({ navigate }: HomePageProps) {
  return (
    <main className="page">
      <Header
        title="Smart Mirror AI Coach"
        subtitle="거울 앞에서 지금 상태를 점검해보세요."
      />
      <div className="row">
        <button
          type="button"
          className="btn btn--primary"
          onClick={() => navigate("/mode")}
        >
          시작하기
        </button>
      </div>
    </main>
  );
}

export default HomePage;
