/**
 * Remotion SSR render script.
 *
 * Bundles the Remotion project, selects the VideoComposition,
 * and renders to MP4 (H.264 + AAC).
 *
 * Usage:
 *   node src/render.mjs --props <props.json> --output <output.mp4>
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { bundle } from '@remotion/bundler';
import { selectComposition, renderMedia } from '@remotion/renderer';

function parseArgs() {
  const args = process.argv.slice(2);
  let propsFile = null;
  let outputFile = null;
  let concurrency = Math.max(1, Math.floor(os.cpus().length / 2));

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--props' && args[i + 1]) {
      propsFile = args[++i];
    } else if (args[i] === '--output' && args[i + 1]) {
      outputFile = args[++i];
    } else if (args[i] === '--concurrency' && args[i + 1]) {
      concurrency = parseInt(args[++i], 10) || concurrency;
    }
  }

  if (!propsFile) {
    console.error('Error: --props <json-file> is required');
    process.exit(1);
  }
  if (!outputFile) {
    console.error('Error: --output <path> is required');
    process.exit(1);
  }

  return { propsFile, outputFile, concurrency };
}

async function main() {
  const { propsFile, outputFile, concurrency } = parseArgs();

  // Read input props
  const propsData = fs.readFileSync(propsFile, 'utf-8');
  const inputProps = JSON.parse(propsData);

  // Resolve relative paths in props against project root
  const projectRoot = process.cwd();
  if (inputProps.audioSrc && !path.isAbsolute(inputProps.audioSrc)) {
    inputProps.audioSrc = path.resolve(projectRoot, inputProps.audioSrc);
  }
  if (inputProps.backgroundImages) {
    inputProps.backgroundImages = inputProps.backgroundImages.map((img) =>
      path.isAbsolute(img) ? img : path.resolve(projectRoot, img)
    );
  }

  console.log(`Bundling Remotion project...`);
  const bundleLocation = await bundle({
    entryPoint: path.resolve(projectRoot, 'src/index.ts'),
    webpackOverride: (config) => config,
  });
  console.log(`Bundle ready: ${bundleLocation}`);

  console.log(`Selecting composition...`);
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: 'VideoComposition',
    inputProps,
  });
  console.log(`Composition: ${composition.width}x${composition.height} @ ${composition.fps}fps, ${composition.durationInFrames} frames`);

  console.log(`Rendering to: ${outputFile}`);
  await renderMedia({
    composition,
    serveUrl: bundleLocation,
    codec: 'h264',
    outputLocation: outputFile,
    inputProps,
    crf: 18,
    preset: 'fast',
    concurrency,
    onProgress: ({ progress }) => {
      const pct = Math.round(progress * 100);
      process.stdout.write(`\rRendering: ${pct}%`);
    },
  });

  console.log(`\nDone! Output: ${outputFile}`);
}

main().catch((err) => {
  console.error(`\nRender failed: ${err.message}`);
  process.exit(1);
});
