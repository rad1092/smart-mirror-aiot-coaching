import type { ResultCard as ResultCardModel } from "../types/result";

const TYPE_LABEL: Record<string, string> = {
  hair: "헤어",
  grooming: "그루밍",
  outfit: "코디",
  outing: "외출 점검",
  posture: "자세",
};

type ResultCardProps = {
  card: ResultCardModel;
};

function ResultCard({ card }: ResultCardProps) {
  const tag = TYPE_LABEL[card.type] ?? card.type;
  return (
    <article className="result-card" aria-label={`${card.title} 결과 카드`}>
      <header className="result-card__head">
        <span className="result-card__tag">{tag}</span>
        <h3 className="result-card__title">{card.title}</h3>
      </header>
      <p className="result-card__content">{card.content}</p>
    </article>
  );
}

export default ResultCard;
