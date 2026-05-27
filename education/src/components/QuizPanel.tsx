import { useState } from 'react';
import { HelpCircle } from 'lucide-react';

type QuizQuestion = {
  prompt: string;
  answers: string[];
  correctIndex: number;
};

export function QuizPanel({ quiz }: { quiz: QuizQuestion[] }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [showAll, setShowAll] = useState(false);
  const correctCount = quiz.filter((question, index) => answers[index] === question.correctIndex).length;
  const answeredCount = Object.keys(answers).length;
  const visibleQuestions = showAll
    ? quiz.map((question, questionIndex) => ({ question, questionIndex }))
    : [{ question: quiz[activeIndex], questionIndex: activeIndex }];

  const chooseAnswer = (questionIndex: number, answerIndex: number) => {
    setAnswers((current) => ({ ...current, [questionIndex]: answerIndex }));
  };

  return (
    <section className="wide-panel" data-testid="quiz-panel">
      <div className="panel-heading">
        <HelpCircle size={20} />
        <h3>Final checkpoint</h3>
      </div>
      <div className="quiz-progress">
        <div>
          <span>{showAll ? 'Review mode' : `Question ${activeIndex + 1} of ${quiz.length}`}</span>
          <strong>Answered {answeredCount}/{quiz.length}</strong>
        </div>
        <div className="quiz-controls">
          <button
            className="secondary-action"
            disabled={showAll || activeIndex === 0}
            onClick={() => setActiveIndex((index) => Math.max(0, index - 1))}
            type="button"
          >
            Previous question
          </button>
          <button
            className="secondary-action"
            disabled={showAll || activeIndex === quiz.length - 1}
            onClick={() => setActiveIndex((index) => Math.min(quiz.length - 1, index + 1))}
            type="button"
          >
            Next question
          </button>
          <button className="secondary-action" onClick={() => setShowAll((value) => !value)} type="button">
            {showAll ? 'Focus one question' : 'Review all questions'}
          </button>
        </div>
      </div>
      <div className="quiz-list">
        {visibleQuestions.map(({ question, questionIndex }) => (
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
                  onClick={() => chooseAnswer(questionIndex, answerIndex)}
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
