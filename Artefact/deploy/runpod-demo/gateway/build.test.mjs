import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, readFile, writeFile, rm, cp, copyFile} from 'node:fs/promises';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {fileURLToPath} from 'node:url';
import {buildFrontend} from './build.mjs';

const source = fileURLToPath(new URL('../../../web/', import.meta.url));
test('build uses current frontend, keeps local files unchanged, and is repeatable', async () => {
  const temp = await mkdtemp(join(tmpdir(), 'qa-gateway-'));
  try {
    const before = await readFile(join(source, 'app.js'), 'utf8');
    const output = join(temp, 'public');
    await buildFrontend(source, output);
    const script = await readFile(join(output, 'app.js'), 'utf8');
    assert.ok(script.indexOf('await waitForDemoServer(controller.signal)') < script.indexOf("await fetch(API + '/api/ask/stream'"));
    assert.equal(script.split('await waitForDemoServer(controller.signal)').length, 2);
    const html = await readFile(join(output, 'index.html'), 'utf8');
    assert.equal(html.split('id="demoConnection"').length, 2);
    assert.match(html, /demo-connection.js/);
    assert.equal(await readFile(join(output, 'api-config.js'), 'utf8'), 'window.API_BASE = "";\n');
    await buildFrontend(source, output);
    assert.equal(await readFile(join(output, 'app.js'), 'utf8'), script);
    assert.equal(await readFile(join(source, 'app.js'), 'utf8'), before);
    await assert.rejects(buildFrontend(source, source), /separate/);
  } finally {
    await rm(temp, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
});

test('unexpected frontend change fails before writing output', async () => {
  const temp = await mkdtemp(join(tmpdir(), 'qa-gateway-'));
  try {
    const fixture = join(temp, 'source');
    await mkdir(fixture);
    await copyFile(join(source, 'app.js'), join(fixture, 'app.js'));
    await copyFile(join(source, 'index.html'), join(fixture, 'index.html'));
    await writeFile(join(fixture, 'app.js'), 'unrecognized frontend');
    const output = join(temp, 'public');
    await assert.rejects(buildFrontend(fixture, output), /Frontend changed/);
    await assert.rejects(readFile(join(output, 'app.js')), {code: 'ENOENT'});
  } finally {
    await rm(temp, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
});
