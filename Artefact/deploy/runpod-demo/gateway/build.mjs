import {createHash} from 'node:crypto';
import {cp, mkdir, readFile, readdir, writeFile} from 'node:fs/promises';
import {dirname, extname, join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const here = fileURLToPath(new URL('.', import.meta.url));
const extensions = new Set(['.html', '.css', '.js', '.json', '.svg', '.png', '.ico', '.woff', '.woff2']);

function replaceOnce(text, before, after) {
  if (text.split(before).length !== 2) {
    throw new Error('Frontend changed; review the deployment adapter before building.');
  }
  return text.replace(before, after);
}

export async function buildFrontend(source, output) {
  source = resolve(source);
  output = resolve(output);
  if (source === output || output.startsWith(source + '/') || output.startsWith(source + '\\')) {
    throw new Error('Build output must be separate from the source frontend.');
  }
  let script = await readFile(join(source, 'app.js'), 'utf8');
  let html = await readFile(join(source, 'index.html'), 'utf8');
  script = replaceOnce(script,
    "    const response = await fetch(API + '/api/ask/stream', {",
    "    await waitForDemoServer(controller.signal);\n    const response = await fetch(API + '/api/ask/stream', {");
  script = replaceOnce(script,
    "el('status').textContent = ready ? 'Layanan terhubung' : 'Layanan belum siap';",
    "el('status').textContent = ready ? 'Layanan terhubung' : status.deployment_mode === 'on_demand' ? 'Siap diaktifkan' : 'Layanan belum siap';");
  script = replaceOnce(script,
    "    clearTimeout(queueTimer); controller = null; setBusy(false);",
    "    el('demoConnection').hidden = true;\n    clearTimeout(queueTimer); controller = null; setBusy(false);");
  html = replaceOnce(html, '<script src="api-config.js"></script>',
    '<script src="api-config.js"></script>\n<script src="demo-connection.js" defer></script>');
  html = replaceOnce(html, '  <form id="questionForm"',
    '<p id="demoConnection" role="status" aria-live="polite" hidden style="max-width:70rem;margin:1rem auto;padding:1rem;color:#16334a;background:#e7f4fb;border-radius:12px"></p>\n  <form id="questionForm"');

  const manifest = {};
  const checksum = async path => createHash('sha256').update(await readFile(path)).digest('hex');
  async function copyAssets(from, to) {
    await mkdir(to, {recursive: true});
    for (const entry of await readdir(from, {withFileTypes: true})) {
      if (entry.name.startsWith('.')) continue;
      const input = join(from, entry.name);
      const target = join(to, entry.name);
      if (entry.isDirectory()) await copyAssets(input, target);
      else if (entry.isFile() && extensions.has(extname(entry.name).toLowerCase())) {
        await cp(input, target);
        manifest[relative(output, target).replaceAll('\\', '/')] = await checksum(target);
      }
    }
  }
  await copyAssets(source, output);
  await writeFile(join(output, 'app.js'), script);
  await writeFile(join(output, 'index.html'), html);
  await writeFile(join(output, 'api-config.js'), 'window.API_BASE = "";\n');
  await cp(join(here, 'demo-connection.js'), join(output, 'demo-connection.js'));
  for (const name of ['app.js', 'index.html', 'api-config.js', 'demo-connection.js']) {
    manifest[name] = await checksum(join(output, name));
  }
  await writeFile(join(dirname(output), 'public-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildFrontend(resolve(here, '../../../web'), join(here, 'public'));
  console.log('Frontend ready: gateway/public');
}
