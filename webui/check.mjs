import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const packageJson = JSON.parse(readFileSync(join(root, "package.json"), "utf8"));
const lockfile = JSON.parse(
  readFileSync(join(root, "package-lock.json"), "utf8"),
);
const runtimeNoticeSpec = JSON.parse(
  readFileSync(join(root, "LICENSES", "runtime-notices.json"), "utf8"),
);
const expected = {
  "@playwright/test": "1.63.0",
  esbuild: "0.28.2",
  "monaco-editor": "0.56.0",
};
const requiredRuntimeNoticeMapping = {
  entry_points: ["monaco-editor"],
  packages: {
    dompurify: [
      { source: "LICENSE", snapshot: "dompurify.Apache-2.0.txt" },
      { source: "LICENSE-MPL", snapshot: "dompurify.MPL-2.0.txt" },
    ],
    marked: [{ source: "LICENSE.md", snapshot: "marked.MIT.txt" }],
    "monaco-editor": [
      { source: "LICENSE", snapshot: "monaco-editor.MIT.txt" },
      {
        source: "ThirdPartyNotices.txt",
        snapshot: "monaco-editor.ThirdPartyNotices.txt",
      },
    ],
  },
};

const errors = [];
if (packageJson.scripts.build !== "node build.mjs") {
  errors.push("build must target build.mjs");
}
if (packageJson.scripts.check !== "node --check check.mjs && node check.mjs") {
  errors.push("check must run the local metadata check");
}
if (packageJson.scripts["check-assets"] !== "python3 ../scripts/check_assets.py") {
  errors.push("check-assets must run the packaged asset checker");
}
if (packageJson.scripts["test:browser"] !== "playwright test") {
  errors.push("test:browser must use the local Playwright CLI");
}
if (packageJson.dependencies) {
  errors.push("runtime dependencies are not allowed");
}
if (JSON.stringify(packageJson.devDependencies) !== JSON.stringify(expected)) {
  errors.push("package.json has unexpected tool versions");
}
if (lockfile.lockfileVersion !== 3) {
  errors.push("package-lock.json must use lockfileVersion 3");
}
if (
  JSON.stringify(lockfile.packages?.[""]?.devDependencies) !==
  JSON.stringify(expected)
) {
  errors.push("the lockfile root does not match package.json");
}

for (const [name, version] of Object.entries(expected)) {
  const record = lockfile.packages?.[`node_modules/${name}`];
  if (record?.version !== version || !record?.resolved || !record?.integrity) {
    errors.push(`${name} is missing exact lock metadata`);
  }
}

const licenseFiles = readdirSync(join(root, "LICENSES"));
if (!licenseFiles.includes("monaco-editor.MIT.txt")) {
  errors.push("the Monaco MIT notice is missing");
}
const runtimePackages = runtimePackageClosure();
if (
  JSON.stringify(runtimePackages) !==
  JSON.stringify(Object.keys(requiredRuntimeNoticeMapping.packages).sort())
) {
  errors.push("runtime lockfile closure does not match the locked notice packages");
}
for (const name of runtimePackages) {
  const record = lockfile.packages?.[`node_modules/${name}`];
  const notices = runtimeNoticeSpec.packages?.[name];
  if (!record || !notices?.length) {
    errors.push(`${name} is missing a lockfile-driven runtime notice`);
    continue;
  }
  for (const notice of notices) {
    const snapshot = join(root, "LICENSES", notice.snapshot);
    const installed = join(root, "node_modules", ...name.split("/"), notice.source);
    if (!licenseFiles.includes(notice.snapshot)) {
      errors.push(`${name}/${notice.source} has no shipped notice snapshot`);
      continue;
    }
    try {
      if (!readFileSync(snapshot).equals(readFileSync(installed))) {
        errors.push(`${name}/${notice.source} notice snapshot is not exact`);
      }
    } catch {
      errors.push(`${name}/${notice.source} notice source is unavailable`);
    }
  }
}
if (!readFileSync(join(root, "PROVENANCE.md"), "utf8").includes("0.56.0")) {
  errors.push("PROVENANCE.md does not record Monaco 0.56.0");
}
if (
  JSON.stringify(runtimeNoticeSpec) !==
  JSON.stringify(requiredRuntimeNoticeMapping)
) {
  errors.push("runtime-notices.json does not match the locked runtime mapping");
}

if (errors.length) {
  console.error(errors.map((error) => `- ${error}`).join("\n"));
  process.exitCode = 1;
} else {
  console.log("webui metadata, lockfile, and license checks passed");
}

function runtimePackageClosure() {
  const discovered = new Set();
  const visit = (name) => {
    if (discovered.has(name)) return;
    const record = lockfile.packages?.[`node_modules/${name}`];
    if (!record) {
      errors.push(`runtime package is missing from package-lock.json: ${name}`);
      return;
    }
    discovered.add(name);
    for (const dependency of Object.keys(record.dependencies || {}).sort()) {
      visit(dependency);
    }
  };
  for (const name of runtimeNoticeSpec.entry_points || []) visit(name);
  return [...discovered].sort();
}
