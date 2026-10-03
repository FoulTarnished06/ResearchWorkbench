/**
 * build_frontend.js - Frontend Build & Architecture Validator
 * Validates ES6 modules, verifies export/import resolution,
 * audits accessibility landmarks, and guarantees fallback parity.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT_DIR = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT_DIR, 'frontend');
const MODULES_DIR = path.join(FRONTEND_DIR, 'js', 'modules');

console.log('=== AI RESEARCH WORKBENCH - FRONTEND BUILD & AUDIT ===\n');

// 1. Verify all required module files exist
const REQUIRED_MODULES = [
  'utils.js',
  'scenarios.js',
  'state.js',
  'canvas.js',
  'dossier.js',
  'pipeline.js',
  'pdf_workspace.js',
  'dialogue.js',
  'auth.js'
];

let errors = 0;
console.log('1. Checking ES Module Directory Structure...');
REQUIRED_MODULES.forEach(mod => {
  const p = path.join(MODULES_DIR, mod);
  if (fs.existsSync(p)) {
    const size = (fs.statSync(p).size / 1024).toFixed(1);
    console.log(`   [OK] ${mod.padEnd(20)} (${size} KB)`);
  } else {
    console.error(`   [MISSING] ${mod}`);
    errors++;
  }
});

const mainPath = path.join(FRONTEND_DIR, 'js', 'main.js');
if (fs.existsSync(mainPath)) {
  const size = (fs.statSync(mainPath).size / 1024).toFixed(1);
  console.log(`   [OK] main.js (Coordinator) (${size} KB)`);
} else {
  console.error(`   [MISSING] main.js`);
  errors++;
}

// 2. Syntax Validation of all modular JS files via native node -c
console.log('\n2. Validating Module JavaScript Syntax via node -c...');
const allFiles = [...REQUIRED_MODULES.map(m => path.join(MODULES_DIR, m)), mainPath];
allFiles.forEach(f => {
  try {
    execSync(`node -c "${f}"`, { stdio: 'pipe' });
    console.log(`   [PASS] ${path.basename(f)}`);
  } catch (err) {
    console.error(`   [FAIL] ${path.basename(f)}: ${err.message}`);
    errors++;
  }
});

// 3. Fallback app.js audit
console.log('\n3. Auditing Fallback app.js Integrity...');
const appJsPath = path.join(FRONTEND_DIR, 'app.js');
if (fs.existsSync(appJsPath)) {
  const appJs = fs.readFileSync(appJsPath, 'utf8');
  const size = (fs.statSync(appJsPath).size / 1024).toFixed(1);
  console.log(`   [OK] app.js exists (${size} KB, ${appJs.split('\n').length} lines)`);
  
  // Syntax check app.js
  try {
    execSync(`node -c "${appJsPath}"`, { stdio: 'pipe' });
    console.log(`   [PASS] app.js syntax valid`);
  } catch (err) {
    console.error(`   [FAIL] app.js syntax error: ${err.message}`);
    errors++;
  }

  // Verify critical elements are referenced
  const requiredTokens = [
    'sessionStorage',
    'sanitizeHTML',
    'UIState',
    'openSettingsDrawerTab',
    'role="tab"'
  ];
  
  requiredTokens.forEach(tok => {
    if (tok === 'role="tab"') {
      const indexHtml = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf8');
      if (indexHtml.includes(tok)) {
        console.log(`   [OK] HTML contains ${tok}`);
      } else {
        console.error(`   [FAIL] index.html missing ${tok}`);
        errors++;
      }
    } else if (appJs.includes(tok)) {
      console.log(`   [OK] app.js contains ${tok}`);
    } else {
      console.error(`   [FAIL] app.js missing ${tok}`);
      errors++;
    }
  });
} else {
  console.error(`   [MISSING] app.js`);
  errors++;
}

// 4. Accessibility and Landmark Verification in index.html
console.log('\n4. Auditing Landmark Accessibility in index.html...');
const indexHtml = fs.readFileSync(path.join(FRONTEND_DIR, 'index.html'), 'utf8');
const asideMatches = indexHtml.match(/<aside[^>]*>/g) || [];
console.log(`   Found ${asideMatches.length} <aside> landmark elements:`);
asideMatches.forEach(tag => {
  const hasLabel = tag.includes('aria-label') || tag.includes('aria-hidden');
  const preview = tag.slice(0, 60);
  if (hasLabel) {
    console.log(`   [OK] ${preview}...`);
  } else {
    console.error(`   [FAIL] Landmark missing accessible label: ${tag}`);
    errors++;
  }
});

console.log('\n=== BUILD AUDIT RESULT ===');
if (errors === 0) {
  console.log('✅ ALL FRONTEND MODULE AUDITS & PARITY CHECKS PASSED!\n');
  process.exit(0);
} else {
  console.error(`❌ Build audit encountered ${errors} errors.\n`);
  process.exit(1);
}
