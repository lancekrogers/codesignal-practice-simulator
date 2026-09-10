import { expect, test } from "@playwright/test";
import {
  readPngDimensions,
  sanitizeFailureScreenshot,
} from "./failure_artifacts.mjs";

const PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
  "base64",
);

test("generates a valid black PNG with the source dimensions", () => {
  const sanitized = sanitizeFailureScreenshot(PNG);

  expect(readPngDimensions(sanitized)).toEqual(readPngDimensions(PNG));
  expect(sanitized).not.toEqual(PNG);
});

test("rejects failure screenshots with unbounded dimensions", () => {
  const header = Buffer.alloc(33);
  PNG.subarray(0, 8).copy(header);
  header.writeUInt32BE(13, 8);
  Buffer.from("IHDR", "ascii").copy(header, 12);
  header.writeUInt32BE(8193, 16);
  header.writeUInt32BE(1, 20);
  header.writeUInt32BE(
    crc32(header.subarray(12, 29)),
    29,
  );

  expect(() => sanitizeFailureScreenshot(header)).toThrow(
    /dimensions or format are out of bounds/u,
  );
});

function crc32(buffer) {
  let crc = 0xffffffff;
  for (const byte of buffer) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}
