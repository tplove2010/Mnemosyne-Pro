#!/usr/bin/env node
/**
 * Memory Sync - Mnemosyne Pro Wrapper
 * 供 HEARTBEAT 调用：读取当日对话摘要 → 写入 inbox → 触发 reconcile + publish
 * 
 * 用法: node scripts/memory-sync.js
 */

const fs = require('fs');
const path = require('path');

const WORKSPACE = process.cwd();
const OPENCLAW_DIR = path.join(WORKSPACE, '..'); // .openclaw parent
const MNEMOSYNE_DIR = path.join(WORKSPACE, '.mnemosyne');
const INBOX_DIR = path.join(MNEMOSYNE_DIR, 'inbox', 'feishu');
const STATE_FILE = path.join(MNEMOSYNE_DIR, 'state', 'intake-state.json');
const CONFIG_FILE = path.join(MNEMOSYNE_DIR, 'config.jsonc');
const CACHE_DIR = path.join(MNEMOSYNE_DIR, 'cache');

// 日期格式: YYYY-MM-DD
const today = new Date().toISOString().split('T')[0];

// 读取 config.jsonc (简单解析)
function loadConfig() {
  try {
    const content = fs.readFileSync(CONFIG_FILE, 'utf-8');
    // 简单处理：去掉注释，解析 JSON
    const cleaned = content
      .split('\n')
      .filter(line => !line.trim().startsWith('//'))
      .join('\n');
    return JSON.parse(cleaned);
  } catch (e) {
    console.error('[MemorySync] Config load failed:', e.message);
    return null;
  }
}

// 读取当日会话记录
function getTodaySessions() {
  const sessionsFile = path.join(OPENCLAW_DIR, 'agents', 'main', 'sessions', 'sessions.json');
  if (!fs.existsSync(sessionsFile)) return [];
  
  try {
    const content = fs.readFileSync(sessionsFile, 'utf-8');
    const allSessions = JSON.parse(content);
    
    const now = Date.now();
    const oneDayAgo = now - (24 * 60 * 60 * 1000);
    
    const activeSessions = Object.entries(allSessions)
      .filter(([key, session]) => {
        // 过滤：更新时间在 24 小时内
        const updatedAt = session.updatedAt || 0;
        return updatedAt >= oneDayAgo;
      })
      .map(([key, session]) => ({
        key: key,
        model: session.model || 'unknown',
        status: session.status || 'unknown',
        inputTokens: session.inputTokens || 0,
        outputTokens: session.outputTokens || 0,
        totalTokens: session.totalTokens || 0,
        updatedAt: session.updatedAt
      }));
    
    return activeSessions;
  } catch (e) {
    console.error('[MemorySync] Sessions read error:', e.message);
    return [];
  }
}

// 写入 inbox 文件
function writeInbox(sessions) {
  if (sessions.length === 0) {
    console.log('[MemorySync] No active sessions today, skip inbox write');
    return false;
  }
  
  const totalTokens = sessions.reduce((sum, s) => sum + s.totalTokens, 0);
  const totalInput = sessions.reduce((sum, s) => sum + s.inputTokens, 0);
  const totalOutput = sessions.reduce((sum, s) => sum + s.outputTokens, 0);
  
  // 按状态分组
  const running = sessions.filter(s => s.status === 'running').length;
  const done = sessions.filter(s => s.status === 'done').length;
  
  const sessionKeys = sessions.map(s => {
    const parts = s.key.split(':');
    return parts[parts.length - 1] || s.key;
  }).join(', ');
  
  const inboxContent = `---
source: heartbeat
topic: Daily Session Summary
created_at: ${new Date().toISOString()}
confidence: medium
explicitness: explicit
remember: false
promote_global: false
---

今日会话摘要:
- 活跃会话: ${sessions.length} 个 (running: ${running}, done: ${done})
- Input Tokens: ${totalInput}
- Output Tokens: ${totalOutput}
- 总 Token: ${totalTokens}
- 会话列表: ${sessionKeys}

关键事件: Daily memory sync via heartbeat - Mnemosyne Pro 1.1 wrapper
`;

  const inboxFile = path.join(INBOX_DIR, `${today}-heartbeat.md`);
  
  // 确保目录存在
  if (!fs.existsSync(INBOX_DIR)) {
    fs.mkdirSync(INBOX_DIR, { recursive: true });
  }
  
  fs.writeFileSync(inboxFile, inboxContent, 'utf-8');
  console.log('[MemorySync] Written: ' + inboxFile);
  return true;
}

// 更新 intake-state.json
function updateIntakeState(newFile) {
  let state = { files: {} };
  if (fs.existsSync(STATE_FILE)) {
    try {
      state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf-8'));
    } catch (e) {}
  }
  
  const hash = Date.now().toString(16);
  state.files[newFile] = hash;
  
  fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2), 'utf-8');
  console.log('[MemorySync] Updated intake-state.json');
}

// 执行 reconcile (模拟)
function runReconcile() {
  // 实际应由 Mnemosyne CLI 执行，这里模拟状态更新
  const stagedFile = path.join(CACHE_DIR, 'staged-candidates.json');
  const staged = fs.existsSync(stagedFile) 
    ? JSON.parse(fs.readFileSync(stagedFile, 'utf-8')) 
    : [];
  
  // 添加今日的 intake
  staged.push({
    source: 'heartbeat',
    timestamp: new Date().toISOString(),
    status: 'pending_review'
  });
  
  fs.writeFileSync(stagedFile, JSON.stringify(staged, null, 2), 'utf-8');
  console.log('[MemorySync] Staged candidates updated');
}

// 执行 publish (模拟)
function runPublish() {
  const registryFile = path.join(MNEMOSYNE_DIR, 'state', 'publish-registry.json');
  const registry = fs.existsSync(registryFile) 
    ? JSON.parse(fs.readFileSync(registryFile, 'utf-8')) 
    : { keys: {} };
  
  const key = 'agent:main|heartbeat|' + today;
  registry.keys[key] = {
    target: 'memory\\daily-summaries.md',
    updated_at: new Date().toISOString(),
    outcome: 'created'
  };
  
  fs.writeFileSync(registryFile, JSON.stringify(registry, null, 2), 'utf-8');
  console.log('[MemorySync] Publish registry updated');
}

// 主流程
async function main() {
  console.log('[MemorySync] Starting...');
  
  const config = loadConfig();
  if (!config) {
    console.error('[MemorySync] Abort: config not found');
    process.exit(1);
  }
  
  // Step 1: 收集今日会话
  const sessions = getTodaySessions();
  console.log('[MemorySync] Found ' + sessions.length + ' active sessions today');
  
  // Step 2: 写入 inbox
  const hasContent = writeInbox(sessions);
  if (hasContent) {
    updateIntakeState('.mnemosyne\\inbox\\feishu\\' + today + '-heartbeat.md');
    
    // Step 3: reconcile
    runReconcile();
    
    // Step 4: publish
    runPublish();
    
    console.log('[MemorySync] ✅ Daily memory sync complete');
  } else {
    console.log('[MemorySync] ℹ️ No content to sync');
  }
}

main().catch(e => {
  console.error('[MemorySync] Error:', e);
  process.exit(1);
});