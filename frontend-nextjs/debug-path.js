#!/usr/bin/env node
/**
 * Debug the floor-plan API path resolution
 */
const path = require('path');
const fs = require('fs');

// Get the UPLOAD_DIR similar to how the API does it
const UPLOAD_DIR = path.join(process.cwd(), '.uploads', 'plan-drawings');
console.log('UPLOAD_DIR:', UPLOAD_DIR);
console.log('process.cwd():', process.cwd());
console.log('Directory exists:', fs.existsSync(UPLOAD_DIR));

// List files in the directory
if (fs.existsSync(UPLOAD_DIR)) {
  const files = fs.readdirSync(UPLOAD_DIR);
  console.log('Files in directory:', files.length);
  console.log('Recent files:', files.slice(-3));
  
  // Test with the file name
  const fileName = '1776345711034-conv-20260416195751-d4507cae-大堂-集控楼Drawing1-1-.pdf';
  const filePath = path.join(UPLOAD_DIR, fileName);
  console.log('\nTesting path for:', fileName);
  console.log('Full path:', filePath);
  console.log('File exists:', fs.existsSync(filePath));
  
  // Try other variations
  const decoded = decodeURI(fileName);
  console.log('\nDecoded file name:', decoded);
  console.log('Decoded path:', path.join(UPLOAD_DIR, decoded));
  console.log('Decoded exists:', fs.existsSync(path.join(UPLOAD_DIR, decoded)));
} else {
  console.log('UPLOAD_DIR does not exist!');
}
