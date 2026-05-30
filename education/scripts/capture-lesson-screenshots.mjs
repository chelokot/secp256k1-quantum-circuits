import { chromium } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const args = new Map();
for (let index = 2; index < process.argv.length; index += 1) {
  const raw = process.argv[index];
  if (!raw.startsWith('--')) continue;
  const [key, inlineValue] = raw.slice(2).split('=');
  if (inlineValue !== undefined) {
    args.set(key, inlineValue);
    continue;
  }
  const next = process.argv[index + 1];
  if (next !== undefined && !next.startsWith('--')) {
    args.set(key, next);
    index += 1;
  } else {
    args.set(key, true);
  }
}

const rootDir = path.resolve(import.meta.dirname, '..');
const coursePath = path.join(rootDir, 'src/content/course.ts');
const outDir = path.resolve(rootDir, String(args.get('out-dir') ?? 'visual-audit'));
const port = Number(args.get('port') ?? 5178);
const width = Number(args.get('width') ?? 1800);
const height = Number(args.get('height') ?? 1200);
const fullPage = args.has('full-page');
const baseUrl = args.get('base-url') ? String(args.get('base-url')).replace(/\/$/, '') : `http://127.0.0.1:${port}`;
const useExisting = args.has('base-url') || args.has('use-existing');

const courseSource = await readFile(coursePath, 'utf8');
const lessons = [...courseSource.matchAll(/id: '([^']+)',\s*\n\s*module: '([^']+)',\s*\n\s*title: '([^']+)'/g)]
  .map((match, index) => ({
    index: index + 1,
    id: match[1],
    module: match[2],
    title: match[3],
  }));

if (lessons.length === 0) {
  throw new Error(`No lessons found in ${coursePath}`);
}

const waitForServer = async (url) => {
  const startedAt = Date.now();
  let lastError = null;
  while (Date.now() - startedAt < 120_000) {
    try {
      const response = await fetch(url);
      if (response.ok) return;
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  const detail = lastError instanceof Error ? `: ${lastError.message}` : '';
  throw new Error(`Timed out waiting for ${url}${detail}`);
};

let server = null;
if (!useExisting) {
  server = spawn('npm', ['run', 'dev', '--', '--host', '127.0.0.1', '--port', String(port)], {
    cwd: rootDir,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  server.stdout.on('data', (chunk) => process.stdout.write(chunk));
  server.stderr.on('data', (chunk) => process.stderr.write(chunk));
}

try {
  await waitForServer(baseUrl);
  await mkdir(outDir, { recursive: true });

  const browser = await chromium.launch();
  try {
    const manifest = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      viewport: { width, height },
      fullPage,
      lessonCount: lessons.length,
      lessons: [],
    };

    for (const lesson of lessons) {
      const page = await browser.newPage({ viewport: { width, height } });
      const fileName = `${String(lesson.index).padStart(2, '0')}-${lesson.id}.png`;
      const screenshotPath = path.join(outDir, fileName);
      await page.goto(`${baseUrl}/#${lesson.id}`);
      await page.screenshot({ path: screenshotPath, fullPage });
      await page.close();
      manifest.lessons.push({ ...lesson, screenshot: fileName });
      console.log(`[visual-audit] ${lesson.index}/${lessons.length} ${lesson.id} -> ${fileName}`);
    }

    await writeFile(path.join(outDir, 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`);
    console.log(`[visual-audit] wrote ${manifest.lessons.length} screenshots to ${path.relative(rootDir, outDir)}`);
  } finally {
    await browser.close();
  }
} finally {
  if (server !== null) {
    await new Promise((resolve) => {
      server.once('exit', resolve);
      server.kill('SIGINT');
    });
  }
}
