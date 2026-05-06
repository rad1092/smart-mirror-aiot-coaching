function LoadingPage() {
  return (
    <main className="page loading-page" aria-busy="true" aria-live="polite">
      <div className="loading-page__spinner" aria-hidden="true" />
      <h1>분석 중</h1>
      <p>잠시만 기다려주세요. 데이터를 분석하고 있습니다.</p>
    </main>
  );
}

export default LoadingPage;
