#!/usr/bin/env node
const { readFileSync, writeFileSync } = require("fs");
const path = require("path");
const { transform, Features } = require("lightningcss");

const inputPath = process.argv[2];
if (!inputPath) {
    console.error("Usage: node scripts/minify-css.js <css-file>");
    process.exit(1);
}

const resolvedPath = path.resolve(inputPath);
let source;
try {
    source = readFileSync(resolvedPath);
} catch (err) {
    console.error(`Failed to read CSS file: ${resolvedPath}`);
    console.error(err.message);
    process.exit(1);
}

const result = transform({
    filename: resolvedPath,
    code: source,
    minify: true,
    sourceMap: false,
    drafts: { customMedia: true, customProperties: true, registerProperty: true },
    nonStandard: { deepSelectorCombinator: true },
    include: Features.Nesting | Features.MediaQueries,
    exclude: Features.LogicalProperties | Features.DirSelector | Features.LightDark,
    targets: {
        safari: (16 << 16) | 1024,
        ios_saf: (16 << 16) | 1024,
        firefox: 0x800000,
        chrome: 0x6f0000,
    },
    errorRecovery: true,
});

if (result.warnings && result.warnings.length > 0) {
    for (const warning of result.warnings) {
        if (warning.message.includes("Unknown at rule: @property")) {
            continue;
        }
        console.warn(warning.message);
    }
}

writeFileSync(resolvedPath, result.code);
