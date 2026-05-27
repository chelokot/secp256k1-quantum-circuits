import { useState } from 'react';
import { HelpCircle } from 'lucide-react';

type QuizQuestion = {
  prompt: string;
  answers: string[];
  correctIndex: number;
};

export function QuizPanel({ quiz }: { quiz: QuizQuestion[] }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const correctCount = quiz.filter((question, index) => answers[index] === question.correctIndex).length;

  return (
    <section className="wide-panel" data-testid="quiz-panel">
      <div className="panel-heading">
        <HelpCircle size={20} />
        <h3>Checkpoint questions</h3>
      </div>
      <div className="quiz-list">
        {quiz.map((question, questionIndex) => (
          <fieldset key={question.prompt}>
            <legend>{question.prompt}</legend>
            {question.answers.map((answer, answerIndex) => {
              const selected = answers[questionIndex] === answerIndex;
              const correct = question.correctIndex === answerIndex;
              return (
                <button
                  className={selected ? (correct ? 'answer correct' : 'answer wrong') : 'answer'}
                  key={answer}
                  type="button"
                  onClick={() => setAnswers((current) => ({ ...current, [questionIndex]: answerIndex }))}
                >
                  {answer}
                </button>
              );
            })}
          </fieldset>
        ))}
      </div>
      <p className="score-line">Score: {correctCount}/{quiz.length}</p>
    </section>
  );
}
