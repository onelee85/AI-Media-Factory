import { parseSrt, SubtitleSegment } from './parseSubtitles';

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string) {
  if (condition) {
    console.log(`  ✓ ${message}`);
    passed++;
  } else {
    console.error(`  ✗ ${message}`);
    failed++;
  }
}

function assertEqual(actual: unknown, expected: unknown, message: string) {
  assert(JSON.stringify(actual) === JSON.stringify(expected), `${message} — expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

console.log('parseSubtitles.test.ts\n');

// Test 1: Empty input
console.log('Test 1: Empty input returns []');
const empty = parseSrt('');
assertEqual(empty, [], 'Empty string returns empty array');

// Test 2: Single subtitle
console.log('Test 2: Single subtitle block');
const single = parseSrt('1\n00:00:01,000 --> 00:00:03,500\nHello world');
assert(single.length === 1, 'Returns 1 segment');
assertEqual(single[0].id, 1, 'id = 1');
assertEqual(single[0].text, 'Hello world', 'text = "Hello world"');
assertEqual(single[0].startMs, 1000, 'startMs = 1000');
assertEqual(single[0].endMs, 3500, 'endMs = 3500');
assertEqual(single[0].startFrame, 30, 'startFrame = 30 (at 30fps)');
assertEqual(single[0].endFrame, 105, 'endFrame = 105 (at 30fps)');

// Test 3: Multi-line subtitle text
console.log('Test 3: Multi-line text joins with space');
const multi = parseSrt('1\n00:00:00,000 --> 00:00:02,000\nLine one\nLine two');
assertEqual(multi[0].text, 'Line one Line two', 'Multi-line joined with space');

// Test 4: Multiple subtitles
console.log('Test 4: Multiple subtitle blocks');
const multiBlock = parseSrt(
  '1\n00:00:01,000 --> 00:00:03,000\nFirst\n\n2\n00:00:04,000 --> 00:00:06,500\nSecond'
);
assertEqual(multiBlock.length, 2, 'Returns 2 segments');
assertEqual(multiBlock[0].text, 'First', 'First segment text');
assertEqual(multiBlock[1].text, 'Second', 'Second segment text');
assertEqual(multiBlock[1].startMs, 4000, 'Second segment startMs');
assertEqual(multiBlock[1].endMs, 6500, 'Second segment endMs');

// Test 5: Custom FPS
console.log('Test 5: Custom FPS conversion');
const fps24 = parseSrt('1\n00:00:01,000 --> 00:00:03,000\nTest', 24);
assertEqual(fps24[0].startFrame, 24, 'startFrame at 24fps');
assertEqual(fps24[0].endFrame, 72, 'endFrame at 24fps');

// Test 6: Invalid/empty blocks
console.log('Test 6: Invalid input handling');
const invalid = parseSrt('garbage data here');
assertEqual(invalid, [], 'Invalid input returns empty array');

console.log(`\nResults: ${passed} passed, ${failed} failed`);

if (failed > 0) {
  process.exit(1);
}
