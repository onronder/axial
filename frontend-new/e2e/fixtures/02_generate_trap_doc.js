#!/usr/bin/env node
/**
 * ============================================================
 * ARTIFACT 2: "Trap" Document Generator
 * ============================================================
 * 
 * Purpose: Generate a text file designed to trigger false identity detection.
 * The file contains keywords typically found in "Scope Identity" documents
 * but is a legitimate user document that should be searchable.
 * 
 * Usage: node 02_generate_trap_doc.js
 * Output: CONFIDENTIAL_PROJECT_OMEGA.txt in the same directory
 * ============================================================
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// The "Needle" - A unique passphrase that MUST be retrievable via search
const NEEDLE = "The blue falcon flies at midnight 998877";

// Document content designed to test identity masking
const trapContent = `
================================================================================
                    CONFIDENTIAL PROJECT OMEGA
                    Classification: Internal Use Only
================================================================================

SCOPE OVERVIEW
--------------
Project Omega represents our most ambitious initiative to date. This document
provides a comprehensive overview of the project scope, deliverables, and 
key milestones for Q4 2026.

IDENTITY SUMMARY
----------------
This project is spearheaded by the Advanced Research Division. The core team
identity consists of 12 senior engineers and 3 project managers working in
a hybrid capacity across multiple time zones.

PROJECT CONTEXT
---------------
The initiative was born from the need to consolidate multiple data streams
into a unified intelligence platform. The context of this work spans both
technical infrastructure and business process optimization.

KEY OBJECTIVES
--------------
1. Establish unified data governance framework
2. Implement real-time analytics pipeline
3. Deploy secure document management system
4. Create comprehensive audit trail mechanisms

SECRET ACCESS CODES
-------------------
For authorized personnel only:

Primary Access: ${NEEDLE}

This code must be memorized and never written down in non-secure locations.
The access sequence is rotated quarterly.

SCOPE IDENTITY MARKERS
----------------------
Each phase of the project has been assigned unique identity markers:
- Phase 1: ALPHA-OMEGA-7749
- Phase 2: BETA-OMEGA-8832
- Phase 3: GAMMA-OMEGA-9915

SUMMARY CONTEXT
---------------
The scope of this identity document establishes the foundational framework
for all subsequent project activities. All team members must familiarize
themselves with the context and summary provided herein.

DOCUMENT METADATA
-----------------
Created: ${new Date().toISOString()}
Version: 1.0.0
Status: Active
Classification: Confidential

================================================================================
                    END OF DOCUMENT
================================================================================
`;

// Output path
const outputDir = __dirname;
const outputFile = path.join(outputDir, 'CONFIDENTIAL_PROJECT_OMEGA.txt');

// Write the file
fs.writeFileSync(outputFile, trapContent.trim(), 'utf8');

console.log('✅ Trap document generated successfully!');
console.log(`   File: ${outputFile}`);
console.log(`   Size: ${fs.statSync(outputFile).size} bytes`);
console.log('');
console.log('🎯 The "Needle" passphrase embedded in this document:');
console.log(`   "${NEEDLE}"`);
console.log('');
console.log('📋 Keywords designed to trigger identity detection:');
console.log('   - "Scope Overview"');
console.log('   - "Identity Summary"');
console.log('   - "Project Context"');
console.log('   - "Scope Identity Markers"');
console.log('   - "Summary Context"');
console.log('');
console.log('✨ Next step: Upload this file via the Axio Hub UI');
