import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

const openLesson = async (page: Page, lessonId: string) => {
  await page.goto(`/#${lessonId}`);
};

const showAllLabs = async (page: Page) => {
  const toggle = page.getByRole('button', { name: 'Show all labs' });
  if (await toggle.count() > 0) {
    await toggle.click();
  }
};

const selectRouteLab = async (page: Page, labName: RegExp) => {
  await page.getByTestId('lab-route').getByRole('button', { name: labName }).click();
};

test('loads the personal quantum circuit course and generated repo status', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Quantum Circuit Lab' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Current repo contract' })).toHaveCount(0);
  await expect(page.getByLabel('Current repository resource status')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Core idea' }).locator('xpath=ancestor::article')).toContainText('given a public key Q');
  await expect(page.getByRole('heading', { name: 'Core idea' }).locator('xpath=ancestor::article')).toContainText('Classical memory stores one discrete bit string');
  await expect(page.getByRole('heading', { name: 'Core idea' }).locator('xpath=ancestor::article')).toContainText('Quantum memory stores amplitudes');
  await expect(page.getByTestId('lesson-pager')).toContainText('Lesson 1 of 23');
  await expect(page.getByTestId('lesson-pager').getByRole('button', { name: 'Previous' })).toBeDisabled();
  await expect(page.getByLabel('Course progress')).toHaveCount(0);
  await expect(page.getByTestId('lesson-brief')).toHaveCount(0);
  await expect(page.getByTestId('lesson-flow-bridge')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Try this page' })).toHaveCount(0);
  await expect(page.getByTestId('orientation-model-strip')).toContainText('Classical');
  await expect(page.getByTestId('orientation-model-strip')).toContainText('Quantum');
  await expect(page.getByTestId('orientation-model-strip')).toContainText('Readout');
  await expect(page.getByTestId('lesson-detail-steps')).toContainText('A normal CPU step updates a bit string');
  await expect(page.getByText('A normal CPU step updates a bit string')).toBeVisible();
  await expect(page.getByTestId('lesson-recall-check')).toContainText('Answer before reveal');
  await expect(page.getByTestId('lesson-recall-check')).toContainText('What chain must the repo connect');
  await expect(page.getByTestId('lesson-recall-check')).not.toContainText('mathematical attack, the quantum state-and-gate program, tests');
  await page.getByRole('button', { name: 'Reveal checkpoint answer' }).click();
  await expect(page.getByTestId('lesson-recall-check')).toContainText('mathematical attack, the quantum state-and-gate program, tests');
  await expect(page.getByTestId('page-vocab')).toHaveCount(0);
  await expect(page.getByTestId('computation-model-bridge')).toContainText('Ordinary computer');
  await expect(page.getByTestId('computation-model-bridge')).toContainText('Quantum circuit');
  await expect(page.getByTestId('computation-model-bridge')).toContainText('bit string');
  await expect(page.getByTestId('computation-model-bridge')).toContainText('amplitude vector');
  await expect(page.getByTestId('project-proof-map')).toContainText('What has to be proved');
  await expect(page.getByTestId('project-proof-map')).toContainText('public key');
  await expect(page.getByTestId('project-proof-map')).toContainText('Executable circuit');
  await expect(page.getByTestId('project-proof-map')).toContainText('counted peak');
  await expect(page.getByRole('heading', { name: 'Vocabulary spine' })).toHaveCount(0);
  await expect(page.getByLabel('Course navigation')).toContainText('Orientation');
  await expect(page.getByLabel('Course navigation')).toContainText('Quantum substrate');
  await expect(page.getByLabel('Course navigation')).not.toContainText('This repo now');
  await page.getByRole('button', { name: 'All lessons' }).click();
  await expect(page.getByLabel('Course navigation')).toContainText('This repo now');
  await page.getByRole('button', { name: 'Current section' }).click();
  await expect(page.getByLabel('Course navigation')).not.toContainText('This repo now');
  await expect(page.getByTestId('learning-path-map')).toContainText('Zero-to-contributor learning path');
  await expect(page.getByTestId('course-coverage-audit-lab')).toHaveCount(0);
});

test('lets the learner navigate concepts and complete progress', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: 'Mark understood and continue' }).click();
  await expect(page).toHaveURL(/#qubit$/);
  await page.reload();
  await expect(page).toHaveURL(/#qubit$/);

  await page.getByLabel('Course navigation').getByRole('button', { name: /Qubit basics/ }).click();
  await expect(page.getByRole('heading', { name: 'Qubit basics: amplitudes and measurement' })).toBeVisible();
  await expect(page).toHaveURL(/#qubit$/);
  await expect(page.getByTestId('lesson-pager')).toContainText('Lesson 2 of 23');
  await expect(page.getByRole('heading', { name: 'Core idea' }).locator('xpath=ancestor::article')).toContainText('Start with only one qubit');
  await expect(page.getByTestId('qubit-state-vector-visual')).toContainText('This is one qubit');
  await expect(page.locator('xpath=//*[@data-tex="|\\psi\\rangle=a|0\\rangle+b|1\\rangle"]')).toBeVisible();
  await expect(page.locator('.lesson-step-list li > span')).toHaveCount(0);
  await expect(page.getByRole('heading', { name: 'Notation' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Probability rule' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Relative angle' })).toBeVisible();
  await expect(page.getByTestId('lesson-detail-steps').getByRole('heading', { name: 'Measurement' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Core idea' }).locator('xpath=ancestor::article')).toContainText('complex number just means an arrow');
  await expect(page.locator('xpath=//*[@data-tex="P(0)=|a|^2"]')).toBeVisible();
  await page.getByTestId('lesson-pager').getByRole('button', { name: 'Previous' }).click();
  await expect(page).toHaveURL(/#zero$/);
  await page.getByTestId('lesson-pager').getByRole('button', { name: 'Next' }).click();
  await expect(page).toHaveURL(/#qubit$/);
  await page.getByRole('button', { name: 'Mark understood and continue' }).click();
  await expect(page).toHaveURL(/#one-qubit$/);
});

test('turns the lab collection into a zero-to-contributor learning path', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByTestId('learning-path-map')).toContainText('Zero-to-contributor learning path');
  await expect(page.getByTestId('learning-path-map')).toContainText('1. Quantum substrate');
  await expect(page.getByTestId('learning-path-map')).toContainText('2. Attack algorithm');
  await expect(page.getByTestId('learning-path-map')).toContainText('3. Circuit engine');
  await expect(page.getByTestId('learning-path-map')).toContainText('4. Audit and contribution');
  await expect(page.getByTestId('learning-path-map')).toContainText('Contributor readiness');
  await expect(page.getByTestId('learning-path-map')).toContainText('not ready');
  await expect(page.getByTestId('learning-path-map')).toContainText('Qubit basics: amplitudes and measurement');
  await expect(page.getByTestId('learning-path-map')).toContainText('One-qubit gates as reversible motion');
  await expect(page.getByTestId('learning-path-map')).toContainText('Two qubits: joint states and entanglement');
  await page.getByRole('button', { name: 'Jump to next missing contributor step' }).click();
  await expect(page.getByRole('heading', { name: 'Qubit basics: amplitudes and measurement' })).toBeVisible();
  await expect(page).toHaveURL(/#qubit$/);
  await page.getByRole('button', { name: 'Mark understood and continue' }).click();
  await page.getByLabel('Course navigation').getByRole('button', { name: /What the project/ }).click();
  await expect(page.getByTestId('learning-path-map')).toContainText('One-qubit gates as reversible motion');
});

test('runs the qubit and netlist interactives', async ({ page }) => {
  await openLesson(page, 'qubit');

  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Phase becomes probability');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('From state vector to gate');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('calibrated pulse or interaction');
  await expect(page.locator('xpath=//*[@data-tex="|\\psi\\rangle = a|0\\rangle + b|1\\rangle,\\quad |a|^2 + |b|^2 = 1"]')).toBeVisible();
  await expect(page.locator('xpath=//*[contains(@data-tex,"\\alpha a+\\beta b")]')).toBeVisible();
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Valid gates are unitary');
  await expect(page.locator('xpath=//*[@data-tex="U^\\dagger U = I"]')).toBeVisible();
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('three physical knobs');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('First example: Hadamard');
  await expect(page.locator('xpath=//*[contains(@data-tex,"\\frac{a+b}{\\sqrt{2}}")]')).toBeVisible();
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Before Hadamard');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('After Hadamard');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Measure now');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('0: 50% / 1: 50%');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Apply Hadamard, then measure');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('0: 100% / 1: 0%');
  await page.getByLabel('Relative amplitude angle').fill('180');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('Relative angle: 180 degrees');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('0: 0% / 1: 100%');
  await expect(page.getByTestId('qubit-amplitude-bridge-lab')).toContainText('opposite direction');

  await openLesson(page, 'one-qubit');
  await expect(page.getByRole('heading', { name: 'One-qubit gates as reversible motion' })).toBeVisible();
  await expect(page.getByTestId('one-qubit-story')).toContainText('What is allowed to move');
  await expect(page.getByTestId('one-qubit-story')).toContainText('Why a gate is a two-by-two rule');
  await expect(page.getByTestId('one-qubit-story')).toContainText('Why most formulas are not legal gates');
  await expect(page.getByTestId('one-qubit-story')).toContainText('Hadamard: create and recombine a split');
  await expect(page.getByTestId('one-qubit-story')).toContainText('No closed-gate attractor');
  await selectRouteLab(page, /Qubit steering/);
  await expect(page.getByTestId('bloch-playground')).toContainText('0-amplitude');
  await expect(page.getByTestId('bloch-playground')).toContainText('1-amplitude');
  await expect(page.getByTestId('bloch-playground')).toContainText('draws its two amplitudes separately');
  await expect(page.getByTestId('bloch-playground')).toContainText('mixes 0 and 1 amplitudes');
  await expect(page.getByTestId('bloch-playground')).toContainText('swaps the 0 and 1 amplitudes');
  await expect(page.getByTestId('bloch-playground')).toContainText('rotates only the 1-amplitude phase');
  await page.getByTestId('bloch-playground').getByRole('button', { name: 'Hadamard' }).click();
  await expect(page.getByTestId('bloch-playground')).toContainText('|0|²=0.50 |1|²=0.50');

  await selectRouteLab(page, /Gate pattern missions/);
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('closed quantum gates are reversible');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Prepare a split');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Store a hidden angle');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Cycles and groups');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('X² = I');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('No attractor under gates');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Long rotations');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Measurement is different');
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('Expose phase as outcome 1');
  await page.getByTestId('one-qubit-patterns-lab').getByRole('button', { name: /Hidden phase/ }).click();
  await expect(page.getByTestId('one-qubit-patterns-lab')).toContainText('sequence = H S');

  await openLesson(page, 'two-qubit');
  await expect(page.getByTestId('two-qubit-story')).toContainText('The new object is a joint table');
  await expect(page.getByTestId('two-qubit-story')).toContainText('Sometimes two wires are still independent');
  await expect(page.getByTestId('two-qubit-story')).toContainText('Controlled-X is not a measurement');
  await expect(page.getByTestId('two-qubit-story')).toContainText('How the Bell pair is born');
  await expect(page.getByTestId('two-qubit-story')).toContainText('No pair of private one-qubit states');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Run a two-qubit state vector');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Two qubits, four labels');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Product state');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Entangled state');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Measurement samples one full two-bit label');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Split q0, then use q0 as a control');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Mixing twice can cancel one branch');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Product split');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Bell correlation');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Cancel to |10>');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Controlled-X');
  await expect(page.getByTestId('state-vector-lab')).toContainText('control q0, bit-flip target q1 only when q0 is 1');
  await expect(page.getByTestId('state-vector-lab')).toContainText('Entangled');
  await expect(page.getByTestId('state-vector-lab')).toContainText('yes');
  await expect(page.getByTestId('state-vector-lab')).toContainText('|00>');
  await expect(page.getByTestId('state-vector-lab')).toContainText('50%');
  await page.getByTestId('state-vector-lab').getByRole('button', { name: 'Interference' }).click();
  await expect(page.getByTestId('state-vector-lab')).toContainText('|00>');
  await expect(page.getByTestId('state-vector-lab')).toContainText('0%');
  await expect(page.getByTestId('state-vector-lab')).toContainText('|10>');
  await expect(page.getByTestId('state-vector-lab')).toContainText('100%');

  await openLesson(page, 'clifford');
  await expect(page.getByTestId('clifford-story')).toContainText('Why there is a second cost axis');
  await expect(page.getByTestId('clifford-story')).toContainText('The stabilizer map is a restricted but useful world');
  await expect(page.getByTestId('clifford-story')).toContainText('A magic step leaves the cheap map');
  await expect(page.getByTestId('clifford-story')).toContainText('Peak qubits and non-Clifford count are separate headline axes');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('Stabilizer vs magic wheel');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('State class');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('stabilizer');
  await page.getByTestId('stabilizer-magic-lab').getByRole('button', { name: 'T', exact: true }).click();
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('magic');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('needs magic accounting');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('Non-Clifford steps');
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('1');
  await page.getByTestId('stabilizer-magic-lab').getByRole('button', { name: 'T', exact: true }).click();
  await expect(page.getByTestId('stabilizer-magic-lab')).toContainText('stabilizer-friendly');

  await openLesson(page, 'gates');
  await expect(page.getByTestId('gates-story')).toContainText('From formula to circuit row');
  await expect(page.getByTestId('gates-story')).toContainText('Wire');
  await expect(page.getByTestId('gates-story')).toContainText('Controlled gate');
  await expect(page.getByTestId('gates-story')).toContainText('Why cleanup is not optional');
  await expect(page.getByTestId('gates-story')).toContainText('scratch returned to |0>');
  await expect(page.getByTestId('circuit-builder')).toContainText('the row table is the countable object');
  await expect(page.getByTestId('circuit-builder')).toContainText('q0,q1 -> q2');
  await expect(page.getByTestId('circuit-builder')).toContainText('expensive controlled product');
  await page.getByTestId('circuit-builder').getByRole('button', { name: 'CCX' }).click();
  await expect(page.getByTestId('circuit-builder')).toContainText('Non-Clifford');
  await expect(page.getByTestId('circuit-builder')).toContainText('2');
});

test('shows phase estimation and toy curve arithmetic', async ({ page }) => {
  await openLesson(page, 'phase-estimation');

  await expect(page.getByTestId('phase-estimation-story')).toContainText('The problem is not “measure the answer directly”');
  await expect(page.getByTestId('phase-estimation-story')).toContainText('Controlled powers write a binary rhythm');
  await expect(page.getByTestId('phase-estimation-story')).toContainText('The inverse QFT is a rhythm matcher');
  await expect(page.getByTestId('phase-estimation-story')).toContainText('Cost lives before readout');
  await expect(page.getByTestId('lab-route')).toContainText('Phase estimation lens');
  await expect(page.getByTestId('phase-estimation-lab')).toContainText('Hidden phase');
  await expect(page.getByTestId('phase-estimation-lab')).toContainText('Current readout');
  await expect(page.getByTestId('phase-estimation-lab')).toContainText('largest measurement peak');
  await page.getByTestId('phase-estimation-lab').getByRole('slider').fill('5');
  await expect(page.getByTestId('phase-estimation-lab')).toContainText('5/16 maps to 0101');
  await expect(page.getByTestId('phase-estimation-lab')).toContainText('0101');

  await selectRouteLab(page, /Fourier lens/);
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('Fourier lens lab');
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('vector sum length 16/16');
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('peak: 0011 with 100%');
  await page.getByLabel('Fourier hidden frequency').fill('5');
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('peak: 0101 with 100%');
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('vector sum length 0/16');
  await page.getByLabel('Fourier candidate output').fill('5');
  await expect(page.getByTestId('fourier-lens-lab')).toContainText('vector sum length 16/16');

  await openLesson(page, 'ecdlp');
  await selectRouteLab(page, /Toy curve group/);
  await expect(page.getByTestId('toy-curve-lab')).toContainText('Toy elliptic curve group');
  await page.getByTestId('toy-curve-lab').getByRole('slider').fill('2');
  await expect(page.getByTestId('toy-curve-lab')).toContainText('nP');
  await expect(page.getByTestId('toy-curve-lab')).toContainText('(6, 3)');
});

test('shows the whole attack map and point-add formula microscope', async ({ page }) => {
  await openLesson(page, 'ecdlp');

  await expect(page.getByTestId('ecdlp-story')).toContainText('What is public, and what is hidden');
  await expect(page.getByTestId('ecdlp-story')).toContainText('“Logarithm” means undoing repeated group addition');
  await expect(page.getByTestId('ecdlp-story')).toContainText('The quantum oracle asks two-register questions');
  await expect(page.getByTestId('ecdlp-story')).toContainText('Why point-add dominates');
  await expect(page.getByTestId('lab-route')).toContainText('Lab 1 of 6');
  await expect(page.getByTestId('lab-route')).toContainText('Whole attack map');
  await expect(page.getByTestId('lab-route')).toContainText('Resource composer');
  await expect(page.getByTestId('lab-focus-controls')).toContainText('Next lab');
  await expect(page.getByTestId('attack-pipeline-lab')).toContainText('Whole attack map');
  await expect(page.getByTestId('attack-pipeline-lab')).toContainText('Controlled adds');
  await expect(page.getByTestId('attack-pipeline-lab')).toContainText('What is secret?');
  await expect(page.getByTestId('attack-pipeline-lab')).toContainText('controlled point-add');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toHaveCount(0);
  await selectRouteLab(page, /Resource composer/);
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Whole-oracle resource composer');

  await openLesson(page, 'netlists');
  await expect(page.getByTestId('lab-route')).toContainText('Circuit stack map');
  await expect(page.getByTestId('lab-route')).toContainText('Mini resource engine');
  await expect(page.getByTestId('circuit-stack-map')).toContainText('Phase estimation shell');
  await expect(page.getByTestId('circuit-stack-map')).toContainText('Old failure mode');
  await expect(page.getByTestId('circuit-stack-map')).toContainText('rows create live intervals');
  await page.getByTestId('circuit-stack-map').getByRole('button', { name: /Primitive netlist engine/ }).click();
  await expect(page.getByTestId('circuit-stack-map')).toContainText('operation stream, live intervals, owner-capacity proof');
  await expect(page.getByTestId('circuit-stack-map')).toContainText('3 physical-baseline blockers open');

  await openLesson(page, 'coordinates');
  await expect(page.getByRole('heading', { name: 'Coordinates, infinity, and field slots' })).toBeVisible();
  await expect(page.getByTestId('coordinate-story')).toContainText('The same curve point can have several names');
  await expect(page.getByTestId('coordinate-story')).toContainText('Why avoid division in the hot loop');
  await expect(page.getByTestId('coordinate-story')).toContainText('Infinity is not a footnote');
  await expect(page.getByTestId('coordinate-story')).toContainText('Overwrite audit');
  await showAllLabs(page);
  await expect(page.getByTestId('coordinate-model-lab')).toContainText('Affine and projective coordinates');
  await expect(page.getByTestId('coordinate-model-lab')).toContainText('(15, 3, 3)');
  await expect(page.getByTestId('coordinate-model-lab')).toContainText('= (5, 1)');
  await page.getByLabel('Projective scale').fill('5');
  await expect(page.getByTestId('coordinate-model-lab')).toContainText('(8, 5, 5)');
  await expect(page.getByTestId('coordinate-model-lab')).toContainText('3 field slots');
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Reversible overwrite lab');
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Y3 over C');
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Scalar map audit: permutation');
  await page.getByLabel('Enable zero-lift guard').uncheck();
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Scalar map audit: collision');
  await page.getByRole('button', { name: 'Singular matrix' }).click();
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Matrix audit: not reversible');
  await page.getByRole('button', { name: 'Invertible matrix' }).click();
  await expect(page.getByTestId('reversible-overwrite-lab')).toContainText('Matrix audit: reversible permutation');
  await expect(page.getByTestId('point-add-formula-lab')).toContainText('Point-add formula microscope');
  await page.getByTestId('point-add-formula-lab').getByRole('slider').fill('4');
  await expect(page.getByTestId('point-add-formula-lab')).toContainText('lookup infinity no-op');
});

test('connects the toy ECDLP oracle to phase kickback', async ({ page }) => {
  await openLesson(page, 'ecdlp');
  await showAllLabs(page);

  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('Discrete-log oracle toy');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('Choose registers');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('Find collisions');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('Q = 5G');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('4 + 2 * 5 = 1 mod 13');
  await expect(page.getByTestId('discrete-log-oracle-lab')).toContainText('hidden period (+5, -1)');

  await expect(page.getByTestId('phase-kickback-lab')).toContainText('Phase-kickback hidden-period lab');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('phase exponent = 3');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('Fourier gradient');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('(3, 2)');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('dot((d,-1), gradient) = 0 mod 13');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('d = 2 * inverse(3) = 5');
  await page.getByLabel('Kickback secret scalar').fill('7');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('a + b*d = 5 mod 13');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('(3, 8)');
  await expect(page.getByTestId('phase-kickback-lab')).toContainText('d = 8 * inverse(3) = 7');
});

test('teaches the windowed ECDLP scaffold that feeds point-add leaves', async ({ page }) => {
  await openLesson(page, 'ecdlp');
  await selectRouteLab(page, /Windowed scaffold/);

  await expect(page.getByTestId('window-scaffold-lab')).toContainText('Windowed attack scaffold');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('32');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('28');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('Classical tail elisions');
  await page.getByLabel('Selected scaffold window').fill('30');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('window 30: elided');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('raw-32 compiler path keeps it quantum');
  await page.getByLabel('Scaffold mode').selectOption('raw32');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('Point-add leaves');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('31');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('window 30: raw32');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('window size 16, retained additions 28');
  await expect(page.getByTestId('window-scaffold-lab')).toContainText('1,200q / 90,000,000');
});

test('teaches whole-oracle resource composition from strict artifacts', async ({ page }) => {
  await openLesson(page, 'ecdlp');
  await selectRouteLab(page, /Resource composer/);

  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Whole-oracle resource composer');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('31 point-add leaves');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('512 phase bits');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('36,973,222');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('7 * 256');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Composition audit: pass');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Qubit model audit: pass');

  await page.getByLabel('Include QROAM chunk streams').uncheck();
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Composition audit: fail');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('24,783,526');
  await page.getByLabel('Include QROAM chunk streams').check();

  await page.getByLabel('Mistakenly sum qubits per leaf').check();
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Wrong serial-sum qubits');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('61,008');
  await expect(page.getByTestId('oracle-resource-composer-lab')).toContainText('Qubit model audit: fail');
});

test('shows modular reduction and QROAMClean tradeoff pressure', async ({ page }) => {
  await openLesson(page, 'modular-lowering');
  await selectRouteLab(page, /Modular reduction/);

  await expect(page.getByTestId('modular-reduction-lab')).toContainText('Modular multiplication shape');
  await page.getByTestId('modular-reduction-lab').getByRole('slider').first().fill('4');
  await expect(page.getByTestId('modular-reduction-lab')).toContainText('reduce');

  await openLesson(page, 'lookup-qroam');
  await selectRouteLab(page, /QROAMClean tradeoff/);
  await expect(page.getByTestId('qroam-tradeoff-lab')).toContainText('QROAMClean tradeoff dial');
  await expect(page.getByTestId('qroam-tradeoff-lab')).toContainText('Target bits plus extra junk-register capacity');
  await expect(page.getByTestId('qroam-tradeoff-lab')).toContainText('target');
  await expect(page.getByTestId('qroam-tradeoff-lab')).toContainText('junk');
  await page.getByTestId('qroam-tradeoff-lab').getByRole('slider').fill('16');
  await expect(page.getByTestId('qroam-tradeoff-lab')).toContainText('Workspace');
});

test('separates external baselines, reference boundaries, and unaccepted candidates', async ({ page }) => {
  await openLesson(page, 'repo-baselines');

  await expect(page.getByTestId('baseline-explorer')).toContainText('Google low-qubit public line');
  await expect(page.getByTestId('baseline-explorer')).toContainText('Google low-gate public line');
  await expect(page.getByTestId('baseline-explorer')).toContainText('Repo older exact-family reference');
  await expect(page.getByTestId('baseline-explorer')).toContainText('Repo macro/ZKP wrapper reference');
  await expect(page.getByTestId('baseline-explorer')).toContainText('reference boundary not accepted');
  await expect(page.getByTestId('baseline-explorer')).toContainText('1044q');
});

test('teaches baseline tradeoff landscape and claim status', async ({ page }) => {
  await openLesson(page, 'repo-baselines');
  await selectRouteLab(page, /Tradeoff landscape/);

  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('Baseline tradeoff landscape');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('1,200q / 90M');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('1,450q / 70M');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('Google low-gate public line');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('70.0M');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('external public baseline');
  await page.getByLabel('Selected baseline row').selectOption('repo_macro_wrapper_reference');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('Repo macro/ZKP wrapper reference');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('1,199');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('do not call this accepted baseline');
  await page.getByLabel('Baseline status lens').selectOption('accepted');
  await expect(page.getByTestId('baseline-tradeoff-lab')).toContainText('No accepted physical baseline rows yet.');
});

test('bridges logical repo rows to a toy physical-qubit envelope', async ({ page }) => {
  await openLesson(page, 'logic-physical');

  await expect(page.getByTestId('logical-physical-story')).toContainText('The repo counts the algorithm layer');
  await expect(page.getByTestId('logical-physical-story')).toContainText('A logical qubit is protected information');
  await expect(page.getByTestId('logical-physical-story')).toContainText('Code distance');
  await expect(page.getByTestId('logical-physical-story')).toContainText('What the labs are allowed to claim');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('Logical to physical bridge');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('1,968');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('450');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('885.6k');
  await page.getByLabel('Logical resource row').selectOption('repo_guard_corrected');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('2,222');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('999.9k');
  await page.getByTestId('logical-physical-bridge-lab').getByLabel('Code distance').fill('17');
  await expect(page.getByTestId('logical-physical-bridge-lab')).toContainText('578');
});

test('teaches logical encoding with a repetition-code toy decoder', async ({ page }) => {
  await openLesson(page, 'logic-physical');

  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('Error-correction toy');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('majority vote');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('Manual decode: pass');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('11,110');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('0.000985%');
  await page.getByLabel('Physical carrier 1').click();
  await page.getByLabel('Physical carrier 3').click();
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('Manual decode: fail');
  await page.getByLabel('Repetition code distance').fill('7');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('Code distance: 7');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('Manual decode: pass');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('15,554');
  await expect(page.getByTestId('error-correction-toy-lab')).toContainText('tolerates 3');
});

test('teaches non-Clifford magic budget pressure separately from qubits', async ({ page }) => {
  await openLesson(page, 'clifford');

  await expect(page.getByTestId('magic-budget-lab')).toContainText('Non-Clifford magic budget');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('36,973,222');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('10,000,000');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('3.7 days');
  await page.getByLabel('Magic budget resource row').selectOption('google_low_qubit');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('90,000,000');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('9.0 days');
  await page.getByLabel('Parallel magic factories').fill('4');
  await expect(page.getByTestId('magic-budget-lab')).toContainText('4.5 days');
});

test('teaches QROAM selection and owner invariant failures', async ({ page }) => {
  await openLesson(page, 'lookup-qroam');

  await expect(page.getByTestId('lookup-story')).toContainText('A table lookup is still a circuit');
  await expect(page.getByTestId('lookup-story')).toContainText('What QROAMClean buys and what it spends');
  await expect(page.getByTestId('lookup-story')).toContainText('The consistency trap');
  await expect(page.getByTestId('lookup-story')).toContainText('not free output');
  await expect(page.getByTestId('lab-route')).toContainText('QROAM selection');
  await expect(page.getByTestId('lab-route')).toContainText('QROAMClean tradeoff');
  await expect(page.getByTestId('qroam-lab')).toContainText('QROAM table selection');
  await expect(page.getByTestId('qroam-lab')).toContainText('Target lane');
  await expect(page.getByTestId('qroam-lab')).toContainText('No-free-lane audit');
  await expect(page.getByTestId('qroam-lab')).toContainText('selected data must have an owner');
  await page.getByRole('button', { name: 'a0=1' }).click();
  await expect(page.getByTestId('qroam-lab')).toContainText('Selected');

  await openLesson(page, 'owner-capacity');
  await selectRouteLab(page, /Invariant lab/);
  await expect(page.getByTestId('engine-invariant-lab')).toContainText('Audit: pass');
  await page.getByLabel('Inject hidden scratch lane').check();
  await expect(page.getByTestId('engine-invariant-lab')).toContainText('Audit: fail');
});

test('lets the learner write and debug a tiny quantum netlist', async ({ page }) => {
  await openLesson(page, 'programming');
  await expect(page.getByTestId('programming-story')).toContainText('A circuit program is a contract over wires');
  await expect(page.getByTestId('programming-story')).toContainText('Rows are the smallest auditable unit');
  await expect(page.getByTestId('programming-story')).toContainText('A rejected row is a feature');
  await selectRouteLab(page, /Quantum DSL/);

  const editor = page.getByLabel('Quantum DSL editor');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('Non-Clifford');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('valid');
  await editor.fill('H q0\nBAD q0');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('unknown op BAD');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('error');
  await editor.fill('H q0\nCX q0 q1\nCCX q0 q1 q2');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('valid');
  await expect(page.getByTestId('quantum-dsl-lab')).toContainText('CCX');
});

test('teaches reversible cleanup as an executable puzzle', async ({ page }) => {
  await openLesson(page, 'cleanup');
  await expect(page.getByTestId('cleanup-story')).toContainText('Scratch becomes garbage when its story stops');
  await expect(page.getByTestId('cleanup-story')).toContainText('The safe pattern is compute, consume, reverse');
  await expect(page.getByTestId('cleanup-story')).toContainText('How this maps to the repo blocker');
  await selectRouteLab(page, /Cleanup puzzle/);

  await expect(page.getByTestId('cleanup-puzzle-lab')).toContainText('Audit: fail');
  await page.getByRole('button', { name: /uncompute A with same x,y/ }).click();
  await expect(page.getByTestId('cleanup-puzzle-lab')).toContainText('Audit: pass');
  await expect(page.getByTestId('cleanup-puzzle-lab')).toContainText('scratch returns to |0>');
});

test('shows partial-product lowering pressure', async ({ page }) => {
  await openLesson(page, 'modular-lowering');

  await expect(page.getByTestId('multiplier-grid-lab')).toContainText('Partial-product grid');
  await page.getByTestId('multiplier-grid-lab').getByRole('slider').first().fill('15');
  await page.getByTestId('multiplier-grid-lab').getByRole('slider').last().fill('15');
  await expect(page.getByTestId('multiplier-grid-lab')).toContainText('Active ANDs');
  await expect(page.getByTestId('multiplier-grid-lab')).toContainText('16');
});

test('requires owner assignment and numeric capacity to pass', async ({ page }) => {
  await openLesson(page, 'owner-capacity');
  await selectRouteLab(page, /Capacity game/);

  await expect(page.getByTestId('owner-capacity-game')).toContainText('Audit: fail');
  await page.getByLabel('Owner for guard ladder').selectOption('guard_workspace');
  await expect(page.getByTestId('owner-capacity-game')).toContainText('Audit: pass');
  await expect(page.getByTestId('owner-capacity-game')).toContainText('255/255');
});

test('keeps accepted-baseline promotion behind all blockers', async ({ page }) => {
  await openLesson(page, 'repo-baselines');
  await selectRouteLab(page, /Promotion audit/);

  await expect(page.getByTestId('baseline-promotion-lab')).toContainText('Promotion audit: blocked');
  await page.getByLabel('Close zero lift guard capacity not promoted').check();
  await page.getByLabel('Close modular accumulator source uncompute not promoted').check();
  await page.getByLabel('Close modular arithmetic clifford expansion not flattened').check();
  await expect(page.getByTestId('baseline-promotion-lab')).toContainText('Promotion audit: accepted-baseline ready');
  await page.getByLabel('Use guard-corrected qubit count').uncheck();
  await expect(page.getByTestId('baseline-promotion-lab')).toContainText('Promotion audit: blocked');
});

test('trains claim classification before publishing resource numbers', async ({ page }) => {
  await openLesson(page, 'contribution');

  await expect(page.getByTestId('claim-audit-drill')).toContainText('Claim audit drill');
  await expect(page.getByTestId('claim-audit-drill')).toContainText('Classification: wrong');
  await page.getByLabel('Claim classification').selectOption('rejected');
  await expect(page.getByTestId('claim-audit-drill')).toContainText('Classification: correct');
  await page.getByLabel('Require evidence same executable primitive stream').check();
  await page.getByLabel('Require evidence all physical blockers closed').check();
  await page.getByLabel('Require evidence proof input bound to selected contract').check();
  await expect(page.getByTestId('claim-audit-drill')).toContainText('Claim audit: pass');
  await page.getByLabel('Claim to review').selectOption('guard-consequence');
  await page.getByLabel('Claim classification').selectOption('consequence');
  await page.getByLabel('Require evidence derivation from strict candidate').check();
  await page.getByLabel('Require evidence clean-ladder guard capacity counted').check();
  await page.getByLabel('Require evidence not promoted into global primitive stream').check();
  await expect(page.getByTestId('claim-audit-drill')).toContainText('Claim audit: pass');
});

test('turns learning into contributor-ready mission packets', async ({ page }) => {
  await openLesson(page, 'contribution');

  await expect(page.getByTestId('contributor-mission-board')).toContainText('Contributor mission board');
  await expect(page.getByTestId('contributor-mission-board')).toContainText('Mission ready: no');
  await page.getByTestId('contributor-mission-board').getByRole('button', { name: /Promote a primitive lowering row/ }).click();
  await page.getByLabel('Complete mission item identify source controls').check();
  await page.getByLabel('Complete mission item name target wire').check();
  await page.getByLabel('Complete mission item assign counted owner').check();
  await page.getByLabel('Complete mission item prove cleanup or output ownership').check();
  await expect(page.getByTestId('contributor-mission-board')).toContainText('Mission ready: yes (4/4)');
  await expect(page.getByTestId('contributor-mission-board')).toContainText('modular accumulator source uncompute not promoted');
});

test('maps original education requirements to concrete course coverage', async ({ page }) => {
  await openLesson(page, 'contribution');

  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Course coverage audit');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Lessons');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('21');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Quiz questions');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('34');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Requirements mapped');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('12/12');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Start from zero quantum computing');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Teach the whole circuit stack');
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('Become useful enough to help improve the repo');
  await page.getByLabel('Show only boundary-aware coverage rows').check();
  await expect(page.getByTestId('course-coverage-audit-lab')).toContainText('State remaining boundaries instead of pretending the course proves the repo result');
  await expect(page.getByTestId('course-coverage-audit-lab')).not.toContainText('Start from zero quantum computing');
});

test('shows final glossary only as a late-course reference', async ({ page }) => {
  await openLesson(page, 'repo-baselines');

  await expect(page.getByRole('heading', { name: 'Full course glossary' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Vocabulary spine' })).toHaveCount(0);
  await expect(page.getByTestId('page-vocab')).toHaveCount(0);
  await expect(page.locator('.glossary-grid')).toContainText('Baseline');
  await expect(page.locator('.glossary-grid')).toContainText('Promoted candidate');
});

test('maps checked artifacts to audit questions and claim limits', async ({ page }) => {
  await openLesson(page, 'point-add-boundary');

  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('Artifact atlas');
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('current_baseline_status.json');
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('Gate blocked with 5 required rows');
  await page.getByTestId('artifact-atlas-lab').getByRole('button', { name: /Point-add equivalence/ }).click();
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('streamed_lookup_tail_leaf_equivalence.json');
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('80/80 checked cases pass');
  await page.getByLabel('Locate artifact path').check();
  await page.getByLabel('Read status and scope').check();
  await page.getByLabel('State what it does not prove').check();
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('Artifact audit: pass');

  await openLesson(page, 'zkp-boundary');
  await selectRouteLab(page, /Artifact atlas/);
  await page.getByTestId('artifact-atlas-lab').getByRole('button', { name: /Proof publication status/ }).click();
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('proof_publication_status.json');
  await expect(page.getByTestId('artifact-atlas-lab')).toContainText('Publication ready: no');
});

test('teaches the result confidence ladder before saying accepted baseline', async ({ page }) => {
  await openLesson(page, 'zkp-boundary');
  await selectRouteLab(page, /Confidence ladder/);

  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Result confidence ladder');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Highest justified rung');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Semantic boundary');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Wording audit: too strong');
  await page.getByLabel('Claim wording').selectOption('candidate');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Wording audit: allowed for selected evidence');
  await page.getByLabel('Evidence Single primitive stream').check();
  await page.getByLabel('Evidence Owner capacity').check();
  await page.getByLabel('Evidence Fresh proof wrapper').check();
  await page.getByLabel('Evidence Accepted baseline gate').check();
  await page.getByLabel('Claim wording').selectOption('accepted baseline');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Highest justified rung');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Accepted baseline gate');
  await expect(page.getByTestId('confidence-ladder-lab')).toContainText('Wording audit: allowed for selected evidence');
});

test('lets the learner derive peak qubits from a mini engine', async ({ page }) => {
  await openLesson(page, 'mini-engine');

  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Mini resource engine');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Engine audit: fail');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Peak live qubits: 10');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Owner capacity');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Cleanup');
  await page.getByLabel('Owner for partial scratch').selectOption('scratch_workspace');
  await page.getByLabel('Add source uncompute row').check();
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Engine audit: pass');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('Peak live qubits: 9');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('assigned and sized');
  await expect(page.getByTestId('mini-resource-engine-lab')).toContainText('scratch dies early');
});

test('shows how one opcode lowers to primitive rows and liveness intervals', async ({ page }) => {
  await openLesson(page, 'mini-engine');
  await selectRouteLab(page, /Opcode lowering/);

  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('Opcode lowering microscope');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('select_field_if_flag bit slice');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('ccx');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('Non-Clifford');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('Lowering audit: pass');
  await page.getByLabel('Remove cleanup rows').check();
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('Lowering audit: fail');
  await page.getByLabel('Lowering source opcode').selectOption('qroam_load');
  await page.getByLabel('Remove cleanup rows').uncheck();
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('qroam_chunk_stream target bit');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('Non-Clifford');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('2');
  await expect(page.getByTestId('opcode-lowering-lab')).toContainText('qroam_target');
});

test('teaches schedule optimization by shortening live intervals', async ({ page }) => {
  await openLesson(page, 'netlists');
  await selectRouteLab(page, /Schedule optimizer/);

  await expect(page.getByTestId('schedule-optimizer-lab')).toContainText('Schedule optimizer lab');
  await expect(page.getByTestId('schedule-optimizer-lab')).toContainText('Schedule audit: fail');
  await expect(page.getByTestId('schedule-optimizer-lab')).toContainText('Peak live qubits: 14');
  await page.getByLabel('Alpha scratch cleanup row').fill('4');
  await page.getByLabel('Beta scratch cleanup row').fill('5');
  await expect(page.getByTestId('schedule-optimizer-lab')).toContainText('Schedule audit: pass');
  await expect(page.getByTestId('schedule-optimizer-lab')).toContainText('Peak live qubits: 9');
});

test('teaches optimization tradeoffs from the hybrid bridge search', async ({ page }) => {
  await openLesson(page, 'optimization');
  await selectRouteLab(page, /Optimization mission/);

  await expect(page.getByTestId('optimization-mission-lab')).toContainText('Optimization mission');
  await expect(page.getByTestId('optimization-mission-lab')).toContainText('Mission audit: blocked');
  await page.getByLabel('Optimization candidate').selectOption('projective_five_slot_no_inverse_core');
  await expect(page.getByTestId('optimization-mission-lab')).toContainText('not executable/promoted');
  await page.getByLabel('Require executable promoted candidate').uncheck();
  await expect(page.getByTestId('optimization-mission-lab')).toContainText('Mission audit: pass');
  await page.getByLabel('Optimization candidate').selectOption('projective_six_slot_with_lookup_workspace_reduced_to_fit');
  await expect(page.getByTestId('optimization-mission-lab')).toContainText('non-Clifford misses target');
  await expect(page.getByTestId('optimization-mission-lab')).toContainText('67.45M');
});

test('teaches point-add semantic boundary cases from equivalence artifacts', async ({ page }) => {
  await openLesson(page, 'point-add-boundary');

  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('Point-add boundary debugger');
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('80/80');
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('lookup infinity');
  await page.getByTestId('point-add-boundary-debugger').getByRole('button', { name: /inverse pair/ }).click();
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('P == -Q');
  await page.getByLabel('Test only random point-add cases').check();
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('Boundary audit: fail');
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('Covered checked cases: 16/80');
  await expect(page.getByTestId('point-add-boundary-debugger')).toContainText('doubling');
});

test('shows real modular accumulator lowering obligations', async ({ page }) => {
  await openLesson(page, 'modular-lowering');
  await selectRouteLab(page, /Accumulator lowering/);

  await expect(page.getByTestId('accumulator-lowering-lab')).toContainText('Modular accumulator lowering');
  await expect(page.getByTestId('accumulator-lowering-lab')).toContainText('1,448,433');
  await expect(page.getByTestId('accumulator-lowering-lab')).toContainText('2,137,410');
  await page.getByRole('button', { name: /pseudo mersenne high column fold/ }).click();
  await expect(page.getByTestId('accumulator-lowering-lab')).toContainText('2,805');
  await page.getByLabel('Show only promoted accumulator facts').check();
  await expect(page.getByTestId('accumulator-lowering-lab')).toContainText('No hidden promotion steps displayed.');
});

test('teaches modular scratch lifecycle cleanup obligations', async ({ page }) => {
  await openLesson(page, 'cleanup');
  await selectRouteLab(page, /Scratch lifecycle/);

  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Scratch lifecycle lab');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('720,896');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('510');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Current stream status: invalid_abandoned_temporary_and_targets');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Lifecycle audit: blocked');
  await page.getByLabel('Add consume row').check();
  await page.getByLabel('Replay cleanup controls').check();
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Lifecycle audit: pass');
  await page.getByLabel('Scratch lifecycle route').selectOption('zero_lift_guard');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('missing source controls for cleanup');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Lifecycle audit: blocked');
  await page.getByLabel('Expose guard predicate controls').check();
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Lifecycle audit: pass');
  await expect(page.getByTestId('accumulator-scratch-lifecycle-lab')).toContainText('Guard cleanup rows still missing source controls: 510.');
});

test('teaches proof freshness, corpus size, and ZKP release gates', async ({ page }) => {
  await openLesson(page, 'zkp-boundary');
  await selectRouteLab(page, /ZKP boundary/);

  await expect(page.getByTestId('proof-boundary-lab')).toContainText('ZKP boundary lab');
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('what does the proof bind?');
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('is the claim physical?');
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('8 cases');
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('9024 cases');
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('Proof release gate: blocked');
  await page.getByLabel('Refresh proof fixtures against current input').check();
  await page.getByLabel('Close physical macro boundary').check();
  await page.getByLabel('Verify compressed and Groth16 proofs').check();
  await expect(page.getByTestId('proof-boundary-lab')).toContainText('Proof release gate: pass');
});

test('teaches the guard gap and quiz boundary', async ({ page }) => {
  await openLesson(page, 'owner-capacity');

  await page.getByLabel('Count clean-ladder zero-lift guard capacity').check();
  await expect(page.getByTestId('slot-liveness')).toContainText('2222');

  await openLesson(page, 'repo-baselines');
  await selectRouteLab(page, /Promotion audit/);
  await expect(page.getByTestId('baseline-promotion-lab')).toContainText('candidate only');
  await expect(page.getByTestId('baseline-promotion-lab')).toContainText('Close blockers');
  await openLesson(page, 'repo-baselines');
  await expect(page.getByTestId('lesson-pager')).toContainText('Lesson 23 of 23');
  await expect(page.getByTestId('lesson-pager').getByRole('button', { name: 'End' })).toBeDisabled();
  await page.getByRole('button', { name: 'Mark understood and finish course' }).click();
  await expect(page).toHaveURL(/#repo-baselines$/);
  await expect(page.getByTestId('quiz-panel')).toContainText('Final checkpoint');
  await expect(page.getByTestId('quiz-panel')).toContainText('Question 1 of 34');
  await expect(page.getByTestId('quiz-panel')).not.toContainText('What is the current accepted Clifford-complete physical baseline');
  await page.getByRole('button', { name: /Because it still has a lifetime/ }).click();
  await expect(page.getByTestId('quiz-panel')).toContainText('Score: 1/34');
  await page.getByRole('button', { name: 'Next question' }).click();
  await expect(page.getByTestId('quiz-panel')).toContainText('Question 2 of 34');
  await page.getByRole('button', { name: 'Review all questions' }).click();
  await expect(page.getByTestId('quiz-panel')).toContainText('What is the current accepted Clifford-complete physical baseline');
});
