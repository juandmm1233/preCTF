type TheoryAccordionProps = {
  explanation: string;
  goal: string;
  prevention: string;
  tutorialUrl: string;
};

function preventionItems(text: string): string[] {
  return text
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^\d+[.)]\s+/, ""));
}

export function TheoryAccordion({ explanation, goal, prevention, tutorialUrl }: TheoryAccordionProps) {
  const theory = explanation.trim();
  const objective = goal.trim();
  const fixes = preventionItems(prevention);
  const url = tutorialUrl.trim();
  if (!theory && !objective && fixes.length === 0) return null;

  return (
    <details className="panel theory-accordion" open>
      <summary>Teoría y Tutorial</summary>
      <div className="theory-body">
        {theory && (
          <section>
            <h3>Qué es este vector</h3>
            <p>{theory}</p>
          </section>
        )}
        {objective && (
          <section>
            <h3>Qué hacer en el laboratorio</h3>
            <p>{objective}</p>
          </section>
        )}
        {fixes.length > 0 && (
          <section>
            <h3>Cómo se corrige</h3>
            {fixes.length === 1 ? (
              <p>{fixes[0]}</p>
            ) : (
              <ol className="theory-list">
                {fixes.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            )}
          </section>
        )}
        {url && (
          <a className="button-link" href={url} target="_blank" rel="noopener noreferrer">
            Ver Tutorial de Apoyo
          </a>
        )}
      </div>
    </details>
  );
}
