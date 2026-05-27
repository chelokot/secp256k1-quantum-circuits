import katex from 'katex';

type MathTexProps = {
  displayMode?: boolean;
  tex: string;
};

export function MathTex({ displayMode = false, tex }: MathTexProps) {
  const html = katex.renderToString(tex, {
    displayMode,
    output: 'htmlAndMathml',
    strict: 'ignore',
    throwOnError: false,
    trust: false,
  });

  return (
    <span
      aria-label={tex}
      className={displayMode ? 'math-tex math-tex-display' : 'math-tex'}
      data-tex={tex}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

type MathTextProps = {
  text: string;
};

export function MathText({ text }: MathTextProps) {
  const parts = text.split(/(\$[^$]+\$)/g);

  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith('$') && part.endsWith('$')) {
          return <MathTex key={`${part}-${index}`} tex={part.slice(1, -1)} />;
        }

        return part;
      })}
    </>
  );
}
