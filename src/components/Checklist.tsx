type ChecklistProps = {
  items: string[];
  title?: string;
};

function Checklist({ items, title = "체크리스트" }: ChecklistProps) {
  if (!items || items.length === 0) {
    return null;
  }

  return (
    <section className="checklist" aria-label={title}>
      <h3 className="checklist__title">{title}</h3>
      <ul className="checklist__list">
        {items.map((item, index) => (
          <li key={`${index}-${item}`} className="checklist__item">
            <span className="checklist__bullet" aria-hidden="true">
              ✓
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default Checklist;
