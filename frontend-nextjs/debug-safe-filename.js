#!/usr/bin/env node
/**
 * Debug getSafeFileName function
 */
const path = require('path');

const getSafeFileName = (fileUrl) => {
  try {
    const url = new URL(fileUrl, 'http://local');
    const file = url.searchParams.get('file') ?? path.basename(url.pathname);
    console.log('url.pathname:', url.pathname);
    console.log('file from searchParams or basename:', file);
    if (!file) throw new Error('Missing drawing file reference.');
    const safeName = path.basename(file);
    console.log('safeName via path.basename:', safeName);
    console.log('safeName === file?', safeName === file);
    if (safeName !== file) throw new Error('Invalid drawing file reference.');
    return safeName;
  } catch (e) {
    console.error('Error in getSafeFileName:', e.message);
    throw e;
  }
};

const fileName = '1776345711034-conv-20260416195751-d4507cae-大堂-集控楼Drawing1-1-.pdf';
console.log('Testing getSafeFileName with:', fileName);
console.log('='.repeat(60));

try {
  const result = getSafeFileName(fileName);
  console.log('Result:', result);
} catch (e) {
  console.log('Caught error:', e.message);
}
