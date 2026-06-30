<template>
  <div class="settings-page">
    <!-- 403 for non-admin -->
    <div v-if="!isAdmin" class="forbidden-card">
      <div class="forbidden-icon">🔒</div>
      <h2>访问受限</h2>
      <p>系统设置仅限管理员访问。如需协助，请联系系统管理员。</p>
      <NuxtLink to="/dashboard" class="back-link">返回总览面板</NuxtLink>
    </div>

    <template v-else>
      <header class="page-header">
        <h1>系统设置</h1>
        <p class="page-subtitle">管理 AI 模型配置与系统更新</p>
      </header>

      <div class="settings-grid">
        <!-- AI Configuration -->
        <section class="config-card">
          <div class="card-header">
            <span class="card-icon">🤖</span>
            <div>
              <h2>AI 模型配置</h2>
              <p class="card-desc">配置发票识别的视觉模型参数</p>
            </div>
            <span v-if="aiSaved" class="status-pill saved">已配置</span>
            <span v-else class="status-pill empty">未配置</span>
          </div>

          <form @submit.prevent="saveAiConfig" class="config-form">
            <div class="field">
              <label class="field-label">模型选择</label>
              <div class="select-wrapper">
                <select v-model="aiForm.model" class="field-select">
                  <option v-for="m in modelOptions" :key="m.value" :value="m.value">
                    {{ m.label }}
                  </option>
                </select>
                <svg class="select-chevron" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
              </div>
              <span class="field-hint">选择用于发票识别的 GLM 视觉模型</span>
            </div>

            <div class="field">
              <label class="field-label">API 密钥</label>
              <div class="input-password-wrapper">
                <input
                  v-model="aiForm.apiKey"
                  :type="showKey ? 'text' : 'password'"
                  class="field-input"
                  placeholder="输入 API 密钥"
                  autocomplete="off"
                />
                <button type="button" class="toggle-btn" @click="showKey = !showKey" :title="showKey ? '隐藏' : '显示'">
                  <svg v-if="!showKey" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                </button>
              </div>
              <span class="field-hint">当前密钥：{{ aiStatus.maskedKey || '未设置' }}</span>
            </div>

            <div class="field">
              <label class="field-label">API 地址</label>
              <input v-model="aiForm.apiUrl" type="text" class="field-input" placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions" />
              <span class="field-hint">可选，留空使用默认地址</span>
            </div>

            <transition name="msg-fade">
              <div v-if="aiMsg" class="form-msg" :class="aiMsgType">{{ aiMsg }}</div>
            </transition>

            <div class="form-actions-row">
              <button type="submit" class="save-btn" :disabled="aiSaving">
                <span v-if="aiSaving" class="btn-spinner"></span>
                {{ aiSaving ? '保存中...' : '保存配置' }}
              </button>
              <button type="button" class="test-btn" :disabled="testing || aiSaving" @click="testModel">
                <span v-if="testing" class="btn-spinner"></span>
                {{ testing ? '测试中...' : '测试连接' }}
              </button>
            </div>

            <transition name="msg-fade">
              <div v-if="testResult" class="form-msg" :class="testResult?.success ? 'success' : 'error'">
                {{ testResult?.text }}
              </div>
            </transition>
          </form>
        </section>

        <!-- Summary AI Configuration -->
        <section class="config-card">
          <div class="card-header">
            <span class="card-icon">✨</span>
            <div>
              <h2>AI 总结配置</h2>
              <p class="card-desc">配置财务总结与自然语言查询的 LLM 模型（支持 DeepSeek、OpenAI 兼容接口）</p>
            </div>
            <span v-if="summaryAiSaved" class="status-pill saved">已配置</span>
            <span v-else class="status-pill empty">未配置</span>
          </div>

          <form @submit.prevent="saveSummaryAiConfig" class="config-form">
            <div class="field">
              <label class="field-label">模型名称</label>
              <input v-model="summaryAiForm.model" type="text" class="field-input" placeholder="deepseek-chat" />
              <span class="field-hint">输入模型 ID，如 deepseek-chat、gpt-4o-mini 或其他 OpenAI 兼容模型</span>
            </div>

            <div class="field">
              <label class="field-label">API 密钥</label>
              <div class="input-password-wrapper">
                <input
                  v-model="summaryAiForm.apiKey"
                  :type="summaryShowKey ? 'text' : 'password'"
                  class="field-input"
                  placeholder="输入 API 密钥"
                  autocomplete="off"
                />
                <button type="button" class="toggle-btn" @click="summaryShowKey = !summaryShowKey" :title="summaryShowKey ? '隐藏' : '显示'">
                  <svg v-if="!summaryShowKey" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                  <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
                </button>
              </div>
              <span class="field-hint">当前密钥：{{ summaryAiStatus.maskedKey || '未设置' }}</span>
            </div>

            <div class="field">
              <label class="field-label">API 地址</label>
              <input v-model="summaryAiForm.apiUrl" type="text" class="field-input" placeholder="https://api.deepseek.com/v1/chat/completions" />
              <span class="field-hint">支持 OpenAI 兼容接口，留空使用 DeepSeek 默认地址</span>
            </div>

            <transition name="msg-fade">
              <div v-if="summaryAiMsg" class="form-msg" :class="summaryAiMsgType">{{ summaryAiMsg }}</div>
            </transition>

            <div class="form-actions-row">
              <button type="submit" class="save-btn" :disabled="summaryAiSaving">
                <span v-if="summaryAiSaving" class="btn-spinner"></span>
                {{ summaryAiSaving ? '保存中...' : '保存配置' }}
              </button>
              <button type="button" class="test-btn" :disabled="summaryTesting || summaryAiSaving" @click="testSummaryModel">
                <span v-if="summaryTesting" class="btn-spinner"></span>
                {{ summaryTesting ? '测试中...' : '测试连接' }}
              </button>
            </div>

            <transition name="msg-fade">
              <div v-if="summaryTestResult" class="form-msg" :class="summaryTestResult?.success ? 'success' : 'error'">
                {{ summaryTestResult?.text }}
              </div>
            </transition>
          </form>
        </section>

        <!-- Update Check -->
        <section class="config-card">
          <div class="card-header">
            <span class="card-icon">🔄</span>
            <div>
              <h2>系统更新</h2>
              <p class="card-desc">检查并安装最新版本</p>
            </div>
            <span class="version-badge">v{{ currentVersion }}</span>
          </div>

          <div class="update-section">
            <div class="version-row">
              <span class="version-label">当前版本</span>
              <span class="version-value">v{{ currentVersion }}</span>
            </div>

            <div v-if="updateState === 'has_update'" class="update-notice">
              <div class="update-notice-header">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                <span>新版本可用：v{{ latestVersion }}</span>
                <span v-if="updateReleaseName" class="release-name">{{ updateReleaseName }}</span>
              </div>
              <p v-if="updateInfo" class="update-notes">{{ updateInfo }}</p>

              <!-- 手动更新步骤 -->
              <div v-if="manualSteps" class="manual-update-steps">
                <p class="commands-label">{{ manualSteps.title }}</p>
                <p class="manual-desc">{{ manualSteps.description }}</p>
                <div class="steps-list">
                  <div v-for="s in manualSteps.steps" :key="s.step" class="step-item">
                    <span class="step-number">{{ s.step }}</span>
                    <div class="step-content">
                      <span class="step-title">{{ s.title }}</span>
                      <span class="step-desc">{{ s.description }}</span>
                      <div class="command-block">
                        <code>{{ s.command }}</code>
                        <button class="copy-btn" @click="copyCommand(s.command)" :title="copiedStep === s.step ? '已复制' : '复制'">
                          <svg v-if="copiedStep !== s.step" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                          <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
                <div class="one-liner-block">
                  <p class="one-liner-label">一键命令（复制后在服务器执行）：</p>
                  <div class="command-block">
                    <code>{{ manualSteps.one_liner }}</code>
                    <button class="copy-btn" @click="copyCommand(manualSteps.one_liner)" :title="copiedOneLiner ? '已复制' : '复制'">
                      <svg v-if="!copiedOneLiner" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                      <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                    </button>
                  </div>
                </div>
                <p class="step-note">{{ manualSteps.note }}</p>
              </div>

              <a v-if="updateDownloadUrl" :href="updateDownloadUrl" target="_blank" class="github-link">
                查看 GitHub 发布页面
              </a>
            </div>

            <div v-else-if="updateState === 'up_to_date'" class="update-status ok">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              已是最新版本
            </div>

            <div v-else-if="updateState === 'error'" class="update-status error">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              {{ updateError || '检查失败，请稍后重试' }}
            </div>

            <button
              class="check-btn"
              :disabled="checking"
              @click="checkUpdate"
              v-if="updateState !== 'has_update' || updateState === 'error'"
            >
              <span v-if="checking" class="btn-spinner"></span>
              {{ checking ? '检查中...' : '检查更新' }}
            </button>
          </div>
        </section>

        <!-- Data Backup & Restore -->
        <section class="config-card backup-card">
          <div class="card-header">
            <span class="card-icon">💾</span>
            <div>
              <h2>数据备份与恢复</h2>
              <p class="card-desc">全量备份数据库、发票文件、用户头像及系统配置</p>
            </div>
          </div>

          <!-- Quick Backup -->
          <div class="backup-quick">
            <div class="backup-quick-row">
              <div class="backup-quick-info">
                <span class="backup-quick-label">手动全量备份</span>
                <span class="backup-quick-hint">包含数据库 + 发票文件 + 头像 + 系统配置</span>
              </div>
              <button
                class="backup-primary-btn"
                :disabled="backupInProgress"
                @click="startBackup"
              >
                <span v-if="backupInProgress" class="btn-spinner"></span>
                <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                {{ backupInProgress ? '备份中...' : '立即备份' }}
              </button>
            </div>
            <!-- Progress -->
            <div v-if="backupInProgress" class="backup-progress">
              <div class="progress-bar-track">
                <div class="progress-bar-fill" :style="{ width: backupProgress + '%' }"></div>
              </div>
              <span class="progress-text">{{ backupProgress }}% · {{ backupProgressMsg }}</span>
            </div>
            <transition name="msg-fade">
              <div v-if="backupActionMsg" class="form-msg" :class="backupActionType">{{ backupActionMsg }}</div>
            </transition>
          </div>

          <!-- Scheduled Backup Config -->
          <div class="backup-schedule">
            <div class="schedule-header">
              <span class="schedule-title">定时备份</span>
              <label class="toggle-switch">
                <input type="checkbox" v-model="scheduleConfig.enabled" @change="saveScheduleConfig" />
                <span class="toggle-slider"></span>
              </label>
            </div>
            <div v-if="scheduleConfig.enabled" class="schedule-fields">
              <div class="schedule-row">
                <div class="schedule-field">
                  <label class="field-label">备份频率</label>
                  <div class="select-wrapper">
                    <select v-model="scheduleConfig.frequency" class="field-select field-select-sm" @change="saveScheduleConfig">
                      <option value="daily">每天</option>
                      <option value="weekly">每周一</option>
                      <option value="monthly">每月1号</option>
                    </select>
                    <svg class="select-chevron" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>
                  </div>
                </div>
                <div class="schedule-field">
                  <label class="field-label">执行时间</label>
                  <input v-model="scheduleConfig.time" type="time" class="field-input field-input-sm" @change="saveScheduleConfig" />
                </div>
                <div class="schedule-field">
                  <label class="field-label">保留份数</label>
                  <input v-model.number="scheduleConfig.retentionCount" type="number" min="1" max="100" class="field-input field-input-sm" @change="saveScheduleConfig" />
                </div>
              </div>
              <span class="schedule-hint">
                将{{ scheduleConfig.frequency === 'daily' ? '每天' : scheduleConfig.frequency === 'weekly' ? '每周一' : '每月1号' }}
                {{ scheduleConfig.time }} 自动执行全量备份，保留最近 {{ scheduleConfig.retentionCount }} 份
              </span>
            </div>
          </div>

          <!-- Local Restore -->
          <ClientOnly>
            <div class="backup-local-restore">
              <div class="restore-header">
                <span class="restore-title">从本地恢复备份</span>
                <span class="restore-hint">选择一个系统备份文件（.tar.gz）直接恢复全部数据</span>
              </div>

              <!-- State: Idle dropzone -->
              <div
                v-if="!localRestoreFile && !localRestoreInProgress"
                class="restore-dropzone"
                :class="{ 'restore-dropzone-active': dropzoneActive }"
                @dragover.prevent="dropzoneActive = true"
                @dragleave.prevent="dropzoneActive = false"
                @drop.prevent="onDropFile"
              >
                <input
                  ref="localRestoreInput"
                  type="file"
                  accept=".tar.gz"
                  class="local-restore-file-input"
                  @change="onLocalFileSelected"
                />
                <div class="restore-dropzone-icon">
                  <svg viewBox="0 0 48 48" width="48" height="48" fill="none">
                    <rect x="4" y="8" width="40" height="32" rx="3" stroke="currentColor" stroke-width="2.5" fill="none"/>
                    <path d="M4 18h40" stroke="currentColor" stroke-width="2.5"/>
                    <circle cx="10" cy="13" r="2" fill="currentColor"/>
                    <circle cx="16" cy="13" r="2" fill="currentColor"/>
                    <path d="M24 34l-6-7h4V24h4v3h4l-6 7z" fill="currentColor" opacity="0.5"/>
                  </svg>
                </div>
                <span class="restore-dropzone-text">拖拽 .tar.gz 备份文件到此处</span>
                <span class="restore-dropzone-divider">— 或 —</span>
                <button
                  class="restore-browse-btn"
                  @click="pickLocalRestoreFile"
                >
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
                  浏览文件
                </button>
              </div>

              <!-- State: File selected -->
              <div v-else-if="localRestoreFile && !localRestoreInProgress" class="restore-preview">
                <div class="restore-file-card">
                  <div class="restore-file-card-icon">
                    <svg viewBox="0 0 48 48" width="40" height="40" fill="none">
                      <rect x="8" y="4" width="32" height="40" rx="3" stroke="currentColor" stroke-width="2.5"/>
                      <path d="M16 4v40M8 14h24M8 24h24M8 34h24" stroke="currentColor" stroke-width="1.5" opacity="0.3"/>
                      <path d="M32 20l-8 8-4-4-4 4" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>
                    </svg>
                  </div>
                  <div class="restore-file-card-info">
                    <span class="restore-file-card-name">{{ localRestoreFile.name }}</span>
                    <span class="restore-file-card-meta">
                      {{ formatFileSize(localRestoreFile.size) }}
                      <template v-if="localRestoreFile.lastModified">
                        · {{ formatDateTime(new Date(localRestoreFile.lastModified).toISOString()) }}
                      </template>
                    </span>
                  </div>
                  <button class="restore-file-card-remove" @click="clearLocalRestore" title="清除选择">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
                <button class="restore-action-btn" @click="confirmLocalRestore">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                  从该备份恢复
                </button>
                <p class="restore-warning">⚠ 恢复操作将覆盖当前数据库及全部文件，不可撤销</p>
              </div>

              <!-- State: Restoring -->
              <div v-else-if="localRestoreInProgress" class="restore-progress-section">
                <div class="restore-progress-header">
                  <span class="restore-progress-spinner"></span>
                  <span class="restore-progress-label">数据恢复进行中…</span>
                </div>
                <div class="restore-progress-track">
                  <div class="restore-progress-fill" :style="{ width: localRestoreProgress + '%' }"></div>
                  <div class="restore-progress-shimmer"></div>
                </div>
                <span class="restore-progress-status">{{ localRestoreProgressMsg }}</span>
              </div>

              <!-- Messages -->
              <transition name="msg-fade">
                <div v-if="localRestoreMsg" class="form-msg" :class="localRestoreMsgType">{{ localRestoreMsg }}</div>
              </transition>
            </div>
          </ClientOnly>

          <!-- Backup History -->
          <div class="backup-history">
            <div class="history-header">
              <span class="history-title">备份记录</span>
              <button class="refresh-btn" @click="loadBackups" :disabled="backupsLoading">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ 'spin-anim': backupsLoading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              </button>
            </div>

            <div v-if="backupsLoading && backups.length === 0" class="history-empty">
              <div class="btn-spinner" style="margin: 0 auto;"></div>
            </div>
            <div v-else-if="backups.length === 0" class="history-empty">
              暂无备份记录
            </div>

            <div v-else class="history-list">
              <div v-for="b in backups" :key="b.id" class="history-item">
                <div class="history-item-main">
                  <div class="history-item-top">
                    <span class="history-type-badge" :class="b.backup_type">
                      {{ b.backup_type === 'manual' ? '手动' : b.backup_type === 'scheduled' ? '定时' : '恢复' }}
                    </span>
                    <span class="history-status" :class="b.status">
                      <span v-if="b.status === 'running'" class="mini-spinner"></span>
                      {{ b.status === 'pending' ? '等待中' : b.status === 'running' ? '进行中' : b.status === 'completed' ? '已完成' : '失败' }}
                    </span>
                    <span class="history-date">{{ formatDateTime(b.created_at) }}</span>
                  </div>
                  <div class="history-item-detail">
                    <span v-if="b.file_size" class="history-size">{{ formatFileSize(b.file_size) }}</span>
                    <span v-if="b.file_count" class="history-files">{{ b.file_count }} 个文件</span>
                    <span v-if="b.created_by_name" class="history-creator">by {{ b.created_by_name }}</span>
                    <span v-if="b.status === 'running'" class="history-progress-msg">{{ b.progress_message }}</span>
                    <span v-if="b.status === 'failed' && b.error_message" class="history-error" :title="b.error_message">{{ b.error_message }}</span>
                  </div>
                </div>
                <div class="history-actions" v-if="b.status === 'completed' && b.backup_type !== 'restore'">
                  <button class="action-btn download" @click="downloadBackup(b.id)" title="下载">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  </button>
                  <button class="action-btn restore" @click="confirmRestore(b.id)" title="恢复">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>
                  </button>
                  <button class="action-btn delete" @click="deleteBackup(b.id)" title="删除">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Restore Confirm Modal -->
        <Teleport to="body">
          <transition name="modal-fade">
            <div v-if="restoreConfirmVisible" class="modal-overlay" @mousedown.self="restoreConfirmVisible = false">
              <div class="modal-content">
                <div class="modal-icon">⚠️</div>
                <h3 class="modal-title">确认数据恢复</h3>
                <p class="modal-desc">
                  <template v-if="restoreTargetId === -1">
                    将从本地文件 <strong>{{ localRestoreFile?.name }}</strong> 恢复数据。<br/>
                  </template>
                  恢复操作将<strong>覆盖当前数据库和文件</strong>，此操作不可撤销。
                </p>
                <div v-if="restoreInProgress" class="restore-progress">
                  <div class="progress-bar-track">
                    <div class="progress-bar-fill" :style="{ width: restoreProgress + '%' }"></div>
                  </div>
                  <span class="progress-text">{{ restoreProgress }}% · {{ restoreProgressMsg }}</span>
                </div>
                <div class="modal-actions">
                  <button class="modal-btn cancel" @click="restoreConfirmVisible = false" :disabled="restoreInProgress">取消</button>
                  <button class="modal-btn confirm" @click="restoreTargetId === -1 ? executeLocalRestore() : executeRestore()" :disabled="restoreInProgress">
                    <span v-if="restoreInProgress" class="btn-spinner"></span>
                    {{ restoreInProgress ? '恢复中...' : '确认恢复' }}
                  </button>
                </div>
              </div>
            </div>
          </transition>
        </Teleport>

      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'

import { useUserStore } from '~/stores/userStore'

const { $api, $config } = useNuxtApp()
const apiBase = $config.public.apiBase as string
const userStore = useUserStore()
userStore.loadFromStorage()

const isAdmin = computed(() => userStore.userType === 'admin')

const modelOptions = [
  { value: 'GLM-4V-Flash', label: 'GLM-4V-Flash（推荐）' },
  { value: 'GLM-4.7-Flash', label: 'GLM-4.7-Flash' },
  { value: 'GLM-4.6V-Flash', label: 'GLM-4.6V-Flash' },
  { value: 'GLM-4.1V-Thinking-Flash', label: 'GLM-4.1V-Thinking-Flash' },
  { value: 'GLM-4-Flash-250414', label: 'GLM-4-Flash-250414' },
]

// ---- AI Config ----
const aiForm = reactive({ model: 'GLM-4V-Flash', apiKey: '', apiUrl: '' })
const aiStatus = reactive({ maskedKey: '' })
const showKey = ref(false)
const aiSaving = ref(false)
const aiSaved = ref(false)
const aiMsg = ref('')
const aiMsgType = ref('success')
let aiMsgTimer: ReturnType<typeof setTimeout> | null = null

function showAiMsg(text: string, type: 'success' | 'error') {
  aiMsg.value = text
  aiMsgType.value = type
  if (aiMsgTimer) clearTimeout(aiMsgTimer)
  aiMsgTimer = setTimeout(() => { aiMsg.value = '' }, 4000)
}

async function loadAiConfig() {
  try {
    const { data } = await $api.get('/system/config')
    if (data.code === 200) {
      const cfg = data.data
      aiForm.model = cfg.ai_model?.value || 'GLM-4V-Flash'
      aiForm.apiUrl = cfg.ai_api_url?.value || ''
      aiStatus.maskedKey = cfg.ai_api_key?.has_value ? cfg.ai_api_key.value : ''
      aiSaved.value = !!(cfg.ai_model?.has_value || cfg.ai_api_key?.has_value)
    }
  } catch (e) {
    // silent
  }
}

async function saveAiConfig() {
  aiSaving.value = true
  try {
    const configs: Record<string, string> = {}
    if (aiForm.model) configs.ai_model = aiForm.model
    if (aiForm.apiKey) configs.ai_api_key = aiForm.apiKey
    if (aiForm.apiUrl) configs.ai_api_url = aiForm.apiUrl

    const { data } = await $api.put('/system/config', { configs })
    if (data.code === 200) {
      showAiMsg('AI 配置保存成功', 'success')
      aiForm.apiKey = ''
      aiSaved.value = true
      await loadAiConfig()
    } else {
      showAiMsg(data.message || '保存失败', 'error')
    }
  } catch (e: any) {
    showAiMsg(e.response?.data?.message || '保存失败，请稍后重试', 'error')
  } finally {
    aiSaving.value = false
  }
}

// ---- Test Model ----
const testing = ref(false)
const testResult = ref<{ success: boolean; text: string } | null>(null)
let testMsgTimer: ReturnType<typeof setTimeout> | null = null

async function testModel() {
  testing.value = true
  testResult.value = null
  try {
    const { data } = await $api.post('/system/test-model')
    if (data.code === 200) {
      testResult.value = {
        success: true,
        text: `测试通过 · 模型 ${data.data.model} · 延迟 ${data.data.latency_ms}ms`
      }
    } else {
      testResult.value = { success: false, text: data.message || '测试失败' }
    }
  } catch (e: any) {
    testResult.value = {
      success: false,
      text: e.response?.data?.message || '测试请求失败'
    }
  } finally {
    testing.value = false
    if (testMsgTimer) clearTimeout(testMsgTimer)
    testMsgTimer = setTimeout(() => { testResult.value = null }, 6000)
  }
}

// ---- Summary AI Config ----
const summaryAiForm = reactive({ model: 'deepseek-chat', apiKey: '', apiUrl: '' })
const summaryAiStatus = reactive({ maskedKey: '' })
const summaryShowKey = ref(false)
const summaryAiSaving = ref(false)
const summaryAiSaved = ref(false)
const summaryAiMsg = ref('')
const summaryAiMsgType = ref('success')
let summaryAiMsgTimer: ReturnType<typeof setTimeout> | null = null

function showSummaryAiMsg(text: string, type: 'success' | 'error') {
  summaryAiMsg.value = text
  summaryAiMsgType.value = type
  if (summaryAiMsgTimer) clearTimeout(summaryAiMsgTimer)
  summaryAiMsgTimer = setTimeout(() => { summaryAiMsg.value = '' }, 4000)
}

async function loadSummaryAiConfig() {
  try {
    const { data } = await $api.get('/system/config')
    if (data.code === 200) {
      const cfg = data.data
      summaryAiForm.model = cfg.summary_ai_model?.value || 'deepseek-chat'
      summaryAiForm.apiUrl = cfg.summary_ai_api_url?.value || ''
      summaryAiStatus.maskedKey = cfg.summary_ai_api_key?.has_value ? cfg.summary_ai_api_key.value : ''
      summaryAiSaved.value = !!(cfg.summary_ai_model?.has_value || cfg.summary_ai_api_key?.has_value)
    }
  } catch (e) {
    // silent
  }
}

async function saveSummaryAiConfig() {
  summaryAiSaving.value = true
  try {
    const configs: Record<string, string> = {}
    if (summaryAiForm.model) configs.summary_ai_model = summaryAiForm.model
    if (summaryAiForm.apiKey) configs.summary_ai_api_key = summaryAiForm.apiKey
    if (summaryAiForm.apiUrl) configs.summary_ai_api_url = summaryAiForm.apiUrl

    const { data } = await $api.put('/system/config', { configs })
    if (data.code === 200) {
      showSummaryAiMsg('AI 总结配置保存成功', 'success')
      summaryAiForm.apiKey = ''
      summaryAiSaved.value = true
      await loadSummaryAiConfig()
    } else {
      showSummaryAiMsg(data.message || '保存失败', 'error')
    }
  } catch (e: any) {
    showSummaryAiMsg(e.response?.data?.message || '保存失败，请稍后重试', 'error')
  } finally {
    summaryAiSaving.value = false
  }
}

// ---- Test Summary Model ----
const summaryTesting = ref(false)
const summaryTestResult = ref<{ success: boolean; text: string } | null>(null)
let summaryTestMsgTimer: ReturnType<typeof setTimeout> | null = null

async function testSummaryModel() {
  summaryTesting.value = true
  summaryTestResult.value = null
  try {
    const { data } = await $api.post('/system/test-summary-model')
    if (data.code === 200) {
      summaryTestResult.value = {
        success: true,
        text: `测试通过 · 模型 ${data.data.model} · 延迟 ${data.data.latency_ms}ms`
      }
    } else {
      summaryTestResult.value = { success: false, text: data.message || '测试失败' }
    }
  } catch (e: any) {
    summaryTestResult.value = {
      success: false,
      text: e.response?.data?.message || '测试请求失败'
    }
  } finally {
    summaryTesting.value = false
    if (summaryTestMsgTimer) clearTimeout(summaryTestMsgTimer)
    summaryTestMsgTimer = setTimeout(() => { summaryTestResult.value = null }, 6000)
  }
}

// ---- Update Check ----
const currentVersion = ref('1.0.0')
const latestVersion = ref('')
const updateInfo = ref('')
const updateReleaseName = ref('')
const updateDownloadUrl = ref('')
const manualSteps = ref<any>(null)
const updateState = ref<'idle' | 'checking' | 'has_update' | 'up_to_date' | 'error'>('idle')
const updateError = ref('')
const checking = ref(false)
const copiedStep = ref<number | null>(null)
const copiedOneLiner = ref(false)
let copyTimer: ReturnType<typeof setTimeout> | null = null

async function loadCurrentVersion() {
  try {
    const { data } = await $api.get('/system/config')
    if (data.code === 200 && data.data?._version?.value) {
      currentVersion.value = data.data._version.value
    }
  } catch { /* silent */ }
}

async function copyCommand(cmd: string, stepNum?: number) {
  try {
    await navigator.clipboard.writeText(cmd)
  } catch {
    const ta = document.createElement('textarea')
    ta.value = cmd
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  }
  if (typeof stepNum === 'number') {
    copiedStep.value = stepNum
  } else {
    copiedOneLiner.value = true
  }
  if (copyTimer) clearTimeout(copyTimer)
  copyTimer = setTimeout(() => {
    copiedStep.value = null
    copiedOneLiner.value = false
  }, 2000)
}

async function checkUpdate() {
  checking.value = true
  updateState.value = 'checking'
  try {
    const { data } = await $api.get('/system/check-update')
    if (data.code === 200) {
      if (data.data.has_update) {
        updateState.value = 'has_update'
        latestVersion.value = data.data.update_info?.version || data.data.latest_version
        updateInfo.value = data.data.update_info?.release_notes || ''
        updateReleaseName.value = data.data.update_info?.release_name || ''
        updateDownloadUrl.value = data.data.update_info?.download_url || ''
        manualSteps.value = data.data.manual_steps || null
      } else {
        updateState.value = 'up_to_date'
      }
    } else {
      updateState.value = 'error'
      updateError.value = data.message || '检查失败'
    }
  } catch (e: any) {
    updateState.value = 'error'
    updateError.value = e.response?.data?.message || '网络错误'
  } finally {
    checking.value = false
  }
}

// ---- Backup & Restore ----
const backups = ref<any[]>([])
const backupsLoading = ref(false)
const backupInProgress = ref(false)
const currentBackupId = ref<number | null>(null)
const backupProgress = ref(0)
const backupProgressMsg = ref('')
const backupActionMsg = ref('')
const backupActionType = ref<'success' | 'error'>('success')
let backupPollTimer: ReturnType<typeof setInterval> | null = null
let backupMsgTimer: ReturnType<typeof setTimeout> | null = null

// 定时备份配置
const scheduleConfig = reactive({
  enabled: false,
  frequency: 'daily',
  time: '03:00',
  retentionCount: 10,
})

// 恢复确认
const restoreConfirmVisible = ref(false)
const restoreTargetId = ref<number | null>(null)
const restoreInProgress = ref(false)
const restoreProgress = ref(0)
const restoreProgressMsg = ref('')

// 本地文件恢复
const localRestoreInput = ref<HTMLInputElement | null>(null)
const localRestoreFile = ref<File | null>(null)
const localRestoreInProgress = ref(false)
const localRestoreProgress = ref(0)
const localRestoreProgressMsg = ref('')
const localRestoreMsg = ref('')
const localRestoreMsgType = ref<'success' | 'error'>('success')
const dropzoneActive = ref(false)
let localRestorePollTimer: ReturnType<typeof setInterval> | null = null
let localRestoreMsgTimer: ReturnType<typeof setTimeout> | null = null

function formatFileSize(bytes: number | null): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  let size = bytes
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++ }
  return size.toFixed(i === 0 ? 0 : 1) + ' ' + units[i]
}

function formatDateTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n: number) => n.toString().padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function showBackupMsg(text: string, type: 'success' | 'error') {
  backupActionMsg.value = text
  backupActionType.value = type
  if (backupMsgTimer) clearTimeout(backupMsgTimer)
  backupMsgTimer = setTimeout(() => { backupActionMsg.value = '' }, 5000)
}

async function loadBackups() {
  backupsLoading.value = true
  try {
    const { data } = await $api.get('/system/backups', { params: { page: 1, per_page: 20 } })
    if (data.code === 200) {
      backups.value = data.data.items || []
    }
  } catch { /* silent */ } finally {
    backupsLoading.value = false
  }
}

async function loadScheduleConfig() {
  try {
    const { data } = await $api.get('/system/backup/config')
    if (data.code === 200) {
      scheduleConfig.enabled = data.data.enabled
      scheduleConfig.frequency = data.data.frequency
      scheduleConfig.time = data.data.time
      scheduleConfig.retentionCount = data.data.retention_count
    }
  } catch { /* silent */ }
}

async function saveScheduleConfig() {
  try {
    const { data } = await $api.put('/system/backup/config', {
      enabled: scheduleConfig.enabled,
      frequency: scheduleConfig.frequency,
      time: scheduleConfig.time,
      retention_count: scheduleConfig.retentionCount,
    })
    if (data.code === 200) {
      showBackupMsg('定时备份配置已保存', 'success')
    } else {
      showBackupMsg(data.message || '保存失败', 'error')
    }
  } catch (e: any) {
    showBackupMsg(e.response?.data?.message || '保存失败', 'error')
  }
}

function startPolling(backupId: number) {
  currentBackupId.value = backupId
  backupProgress.value = 0
  backupProgressMsg.value = '准备中...'
  if (backupPollTimer) clearInterval(backupPollTimer)
  backupPollTimer = setInterval(async () => {
    try {
      const { data } = await $api.get('/system/backups', { params: { page: 1, per_page: 5 } })
      if (data.code !== 200) return
      const record = data.data.items.find((b: any) => b.id === backupId)
      if (!record) return
      backupProgress.value = record.progress || 0
      backupProgressMsg.value = record.progress_message || ''
      if (record.status === 'completed' || record.status === 'failed') {
        stopPolling()
        backupInProgress.value = false
        if (record.status === 'completed') {
          showBackupMsg('备份完成', 'success')
        } else {
          showBackupMsg(record.error_message || '备份失败', 'error')
        }
        loadBackups()
      }
    } catch { /* silent */ }
  }, 1500)
}

function stopPolling() {
  if (backupPollTimer) { clearInterval(backupPollTimer); backupPollTimer = null }
}

async function startBackup() {
  backupInProgress.value = true
  backupActionMsg.value = ''
  try {
    const { data } = await $api.post('/system/backup')
    if (data.code === 200 && data.data?.id) {
      startPolling(data.data.id)
    } else {
      backupInProgress.value = false
      showBackupMsg(data.message || '备份请求失败', 'error')
    }
  } catch (e: any) {
    backupInProgress.value = false
    showBackupMsg(e.response?.data?.message || '备份请求失败', 'error')
  }
}

async function downloadBackup(id: number) {
  const token = localStorage.getItem('token')
  if (!token) { alert('请先登录'); return }

  // 构造直接访问后端的下载URL（通过?token=参数传递JWT，支持浏览器原生下载）
  const downloadUrl = `${apiBase}/system/backup/${id}/download?token=${encodeURIComponent(token)}`
  console.log('[备份下载] 开始下载:', downloadUrl)

  // 直接用浏览器原生下载，无超时限制，大文件也可以正常下载
  window.open(downloadUrl, '_blank')
}

function confirmRestore(id: number) {
  restoreTargetId.value = id
  restoreConfirmVisible.value = true
  restoreInProgress.value = false
  restoreProgress.value = 0
  restoreProgressMsg.value = ''
}

async function executeRestore() {
  if (!restoreTargetId.value) return
  restoreInProgress.value = true
  try {
    const { data } = await $api.post(`/system/backup/restore/${restoreTargetId.value}`, { confirm: true })
    if (data.code === 200) {
      restoreProgressMsg.value = '恢复任务已启动，正在执行...'
      // 轮询恢复进度
      const pollTimer = setInterval(async () => {
        try {
          const { data: listData } = await $api.get('/system/backups', { params: { page: 1, per_page: 10 } })
          if (listData.code !== 200) return
          // 查找最新的 restore 类型记录
          const restore = listData.data.items.find((b: any) => b.backup_type === 'restore')
          if (restore) {
            restoreProgress.value = restore.progress || 0
            restoreProgressMsg.value = restore.progress_message || ''
            if (restore.status === 'completed') {
              clearInterval(pollTimer)
              restoreInProgress.value = false
              restoreConfirmVisible.value = false
              showBackupMsg('数据恢复完成', 'success')
              loadBackups()
            } else if (restore.status === 'failed') {
              clearInterval(pollTimer)
              restoreInProgress.value = false
              showBackupMsg(restore.error_message || '恢复失败', 'error')
            }
          }
        } catch { /* silent */ }
      }, 1500)
    } else {
      restoreInProgress.value = false
      showBackupMsg(data.message || '恢复请求失败', 'error')
    }
  } catch (e: any) {
    restoreInProgress.value = false
    showBackupMsg(e.response?.data?.message || '恢复请求失败', 'error')
  }
}

async function deleteBackup(id: number) {
  if (!confirm('确定删除该备份记录及文件？')) return
  try {
    const { data } = await $api.delete(`/system/backup/${id}`)
    if (data.code === 200) {
      showBackupMsg('备份已删除', 'success')
      loadBackups()
    } else {
      showBackupMsg(data.message || '删除失败', 'error')
    }
  } catch (e: any) {
    showBackupMsg(e.response?.data?.message || '删除失败', 'error')
  }
}

// ---- Local Restore ----
function pickLocalRestoreFile() {
  localRestoreInput.value?.click()
}

function onLocalFileSelected(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  localRestoreFile.value = file
  localRestoreMsg.value = ''
  // 重置 input 以便再次选择同名文件
  input.value = ''
}

function onDropFile(event: DragEvent) {
  dropzoneActive.value = false
  const file = event.dataTransfer?.files?.[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.tar.gz')) {
    showLocalRestoreMsg('只支持 .tar.gz 格式的备份文件', 'error')
    return
  }
  localRestoreFile.value = file
  localRestoreMsg.value = ''
}

function clearLocalRestore() {
  localRestoreFile.value = null
  localRestoreMsg.value = ''
}

function showLocalRestoreMsg(text: string, type: 'success' | 'error') {
  localRestoreMsg.value = text
  localRestoreMsgType.value = type
  if (localRestoreMsgTimer) clearTimeout(localRestoreMsgTimer)
  localRestoreMsgTimer = setTimeout(() => { localRestoreMsg.value = '' }, 5000)
}

function confirmLocalRestore() {
  if (!localRestoreFile.value) return
  restoreConfirmVisible.value = true
  // 复用现有恢复确认弹窗，但标记为本地恢复模式
  restoreTargetId.value = -1 // 负数表示本地恢复
  restoreInProgress.value = false
  restoreProgress.value = 0
  restoreProgressMsg.value = ''
}

async function executeLocalRestore() {
  if (!localRestoreFile.value) return
  restoreInProgress.value = true
  localRestoreInProgress.value = true
  localRestoreMsg.value = ''

  try {
    const formData = new FormData()
    formData.append('file', localRestoreFile.value)
    formData.append('confirm', 'true')

    const { data } = await $api.post('/system/backup/restore/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })

    if (data.code === 200 && data.data?.id) {
      localRestoreProgressMsg.value = '恢复任务已启动，正在执行...'
      restoreConfirmVisible.value = false

      // 轮询恢复进度
      const recordId = data.data.id
      localRestorePollTimer = setInterval(async () => {
        try {
          const { data: listData } = await $api.get('/system/backups', { params: { page: 1, per_page: 20 } })
          if (listData.code !== 200) return
          const record = listData.data.items.find((b: any) => b.id === recordId)
          if (record) {
            localRestoreProgress.value = record.progress || 0
            localRestoreProgressMsg.value = record.progress_message || ''
            if (record.status === 'completed') {
              stopLocalRestorePoll()
              localRestoreInProgress.value = false
              clearLocalRestore()
              showBackupMsg('数据恢复完成', 'success')
              loadBackups()
            } else if (record.status === 'failed') {
              stopLocalRestorePoll()
              localRestoreInProgress.value = false
              restoreInProgress.value = false
              showLocalRestoreMsg(record.error_message || '恢复失败', 'error')
            }
          } else {
            // 旧记录可能已被 DROP SCHEMA 销毁；查找最近完成的恢复记录
            const completedRestore = listData.data.items.find(
              (b: any) => b.backup_type === 'restore' && b.status === 'completed'
            )
            if (completedRestore) {
              stopLocalRestorePoll()
              localRestoreInProgress.value = false
              clearLocalRestore()
              showBackupMsg('数据恢复完成', 'success')
              loadBackups()
            }
          }
        } catch { /* silent */ }
      }, 1500)
    } else {
      restoreInProgress.value = false
      restoreConfirmVisible.value = false
      showLocalRestoreMsg(data.message || '恢复请求失败', 'error')
    }
  } catch (e: any) {
    restoreInProgress.value = false
    restoreConfirmVisible.value = false
    showLocalRestoreMsg(e.response?.data?.message || '恢复请求失败', 'error')
  }
}

function stopLocalRestorePoll() {
  if (localRestorePollTimer) { clearInterval(localRestorePollTimer); localRestorePollTimer = null }
}

onMounted(() => {
  if (isAdmin.value) {
    loadCurrentVersion()
    loadAiConfig()
    loadSummaryAiConfig()
    loadBackups()
    loadScheduleConfig()
  }
})

onUnmounted(() => {
  stopPolling()
  stopLocalRestorePoll()
  if (backupMsgTimer) clearTimeout(backupMsgTimer)
  if (localRestoreMsgTimer) clearTimeout(localRestoreMsgTimer)
})

// Head
useHead({ title: '系统设置 - 财务管理系统' })
</script>

<style scoped>
.settings-page {
  max-width: 800px;
  margin: 0 auto;
}

/* ---- Forbidden ---- */
.forbidden-card {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.forbidden-icon { font-size: 3rem; margin-bottom: 1rem; }
.forbidden-card h2 { margin: 0 0 .5rem; color: #2c3e50; font-size: 1.3rem; }
.forbidden-card p { margin: 0 0 1.5rem; color: #666; font-size: .9rem; }
.back-link {
  display: inline-block;
  padding: .6rem 1.5rem;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border-radius: 6px;
  text-decoration: none;
  font-size: .9rem;
  transition: opacity .2s;
}
.back-link:hover { opacity: .85; }

/* ---- Page Header ---- */
.page-header {
  margin-bottom: 2rem;
}
.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
  font-weight: 700;
  color: #1a252f;
  letter-spacing: -.02em;
}
.page-subtitle {
  margin: .3rem 0 0;
  color: #8899a6;
  font-size: .9rem;
}

/* ---- Cards ---- */
.settings-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}
.config-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  border: 1px solid rgba(0,0,0,.04);
}
.card-header {
  display: flex;
  align-items: center;
  gap: .75rem;
  margin-bottom: 1.25rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #f0f2f5;
}
.card-icon { font-size: 1.3rem; }
.card-header h2 { margin: 0; font-size: 1.05rem; font-weight: 600; color: #2c3e50; }
.card-desc { margin: .15rem 0 0; font-size: .82rem; color: #8899a6; }

.status-pill {
  margin-left: auto;
  font-size: .75rem;
  padding: .25rem .65rem;
  border-radius: 20px;
  font-weight: 500;
}
.status-pill.saved { background: #eafaf1; color: #1e7e34; }
.status-pill.empty { background: #fef3e2; color: #b7791f; }

.version-badge {
  margin-left: auto;
  font-size: .78rem;
  font-weight: 600;
  color: #667eea;
  background: rgba(102,126,234,.1);
  padding: .2rem .6rem;
  border-radius: 4px;
}

/* ---- Form ---- */
.config-form { display: flex; flex-direction: column; gap: 1rem; }
.field { display: flex; flex-direction: column; gap: .3rem; }
.field-label {
  font-size: .85rem;
  font-weight: 600;
  color: #334155;
}
.field-hint {
  font-size: .78rem;
  color: #94a3b8;
}

/* Select */
.select-wrapper {
  position: relative;
}
.field-select {
  width: 100%;
  padding: .65rem .75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  color: #1e293b;
  background: white;
  appearance: none;
  cursor: pointer;
  transition: border-color .2s, box-shadow .2s;
  min-height: 44px;
  box-sizing: border-box;
}
.field-select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,.12);
}
.select-chevron {
  position: absolute;
  right: .75rem;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #94a3b8;
}

/* Input */
.field-input {
  width: 100%;
  padding: .65rem .75rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  color: #1e293b;
  transition: border-color .2s, box-shadow .2s;
  min-height: 44px;
  box-sizing: border-box;
}
.field-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,.12);
}
.field-input::placeholder { color: #cbd5e1; }

.input-password-wrapper {
  position: relative;
  display: flex;
}
.input-password-wrapper .field-input {
  padding-right: 2.75rem;
}
.toggle-btn {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  cursor: pointer;
  color: #94a3b8;
  transition: color .2s;
}
.toggle-btn:hover { color: #475569; }

/* Buttons */
.form-actions-row {
  display: flex;
  gap: .75rem;
  align-items: center;
}

.test-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .7rem 1.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  min-height: 44px;
  background: white;
  color: #334155;
}
.test-btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.test-btn:disabled { opacity: .55; cursor: not-allowed; }

.save-btn, .check-btn, .update-now-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .7rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all .2s;
  min-height: 44px;
}
.save-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  align-self: flex-start;
}
.save-btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.save-btn:disabled { opacity: .55; cursor: not-allowed; }

.check-btn {
  background: white;
  color: #334155;
  border: 1px solid #e2e8f0;
  margin-top: 1rem;
}
.check-btn:hover:not(:disabled) { background: #f8fafc; border-color: #cbd5e1; }
.check-btn:disabled { opacity: .55; cursor: not-allowed; }

.update-now-btn {
  background: linear-gradient(135deg, #27ae60, #2ecc71);
  color: white;
  margin-top: .75rem;
}
.update-now-btn:hover:not(:disabled) { opacity: .9; }
.update-now-btn:disabled { opacity: .55; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: currentColor;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Messages */
.form-msg {
  padding: .6rem .85rem;
  border-radius: 8px;
  font-size: .85rem;
  font-weight: 500;
}
.form-msg.success { background: #eafaf1; color: #1e7e34; }
.form-msg.error { background: #fdf2f2; color: #9b1c1c; }

.msg-fade-enter-active, .msg-fade-leave-active { transition: all .25s ease; }
.msg-fade-enter-from, .msg-fade-leave-to { opacity: 0; transform: translateY(-4px); }

/* ---- Update Section ---- */
.update-section { padding-top: .25rem; }
.version-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: .6rem 0;
}
.version-label { color: #64748b; font-size: .9rem; }
.version-value { font-weight: 600; color: #1e293b; font-size: .9rem; }

.update-notice {
  margin-top: .75rem;
  padding: 1rem;
  background: linear-gradient(135deg, #eff6ff, #f0f9ff);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
}
.update-notice-header {
  display: flex;
  align-items: center;
  gap: .5rem;
  font-weight: 600;
  color: #1e40af;
  margin-bottom: .35rem;
  flex-wrap: wrap;
}
.release-name {
  font-size: .78rem;
  font-weight: 400;
  color: #64748b;
}
.update-notes {
  font-size: .85rem;
  color: #475569;
  margin: .5rem 0;
  white-space: pre-wrap;
  max-height: 120px;
  overflow-y: auto;
}

.update-status {
  display: flex;
  align-items: center;
  gap: .5rem;
  margin-top: .75rem;
  padding: .6rem .85rem;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 500;
}
.update-status.ok { background: #eafaf1; color: #1e7e34; }
.update-status.error { background: #fdf2f2; color: #9b1c1c; }

/* ---- Update Commands ---- */
.update-commands {
  margin-top: 1rem;
}
.commands-label {
  font-size: .85rem;
  color: #475569;
  margin-bottom: .5rem;
  font-weight: 500;
}
.command-block {
  position: relative;
  background: #1e293b;
  border-radius: 8px;
  padding: .75rem 2.5rem .75rem 1rem;
  overflow-x: auto;
}
.command-block code {
  color: #e2e8f0;
  font-size: .82rem;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  white-space: nowrap;
}
.copy-btn {
  position: absolute;
  right: .5rem;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255,255,255,.1);
  border: none;
  border-radius: 4px;
  padding: .35rem;
  cursor: pointer;
  color: #94a3b8;
  transition: all .2s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.copy-btn:hover {
  background: rgba(255,255,255,.2);
  color: white;
}
.commands-hint {
  font-size: .78rem;
  color: #94a3b8;
  margin-top: .4rem;
}
.update-action {
  margin-top: .75rem;
}

.update-progress-notice {
  margin-top: .75rem;
  padding: .85rem;
  background: linear-gradient(135deg, #eff6ff, #f0f9ff);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
}
.update-progress-header {
  display: flex;
  align-items: center;
  gap: .5rem;
  font-size: .88rem;
  font-weight: 500;
  color: #1e40af;
}
.update-progress-hint {
  font-size: .78rem;
  color: #64748b;
  margin: .4rem 0 0;
}

.github-link {
  display: inline-block;
  margin-top: .75rem;
  color: #667eea;
  font-size: .85rem;
  text-decoration: none;
}
.github-link:hover {
  text-decoration: underline;
}

/* ---- Manual Update Steps ---- */
.manual-update-steps {
  margin-top: .75rem;
}
.manual-desc {
  font-size: .82rem;
  color: #64748b;
  margin-bottom: .75rem;
}
.steps-list {
  display: flex;
  flex-direction: column;
  gap: .6rem;
  margin-bottom: .75rem;
}
.step-item {
  display: flex;
  gap: .75rem;
  padding: .7rem;
  background: #f8fafc;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  align-items: flex-start;
}
.step-number {
  flex-shrink: 0;
  width: 1.5rem;
  height: 1.5rem;
  background: #667eea;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .75rem;
  font-weight: 700;
  margin-top: .1rem;
}
.step-content {
  flex: 1;
  min-width: 0;
}
.step-title {
  display: block;
  font-size: .85rem;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: .15rem;
}
.step-desc {
  display: block;
  font-size: .78rem;
  color: #64748b;
  margin-bottom: .4rem;
}
.step-content .command-block {
  margin-top: .25rem;
}
.step-content .command-block code {
  font-size: .75rem;
}
.one-liner-block {
  margin-top: .75rem;
  padding: .75rem;
  background: linear-gradient(135deg, #fefce8, #fffbeb);
  border: 1px solid #fde68a;
  border-radius: 8px;
}
.one-liner-label {
  font-size: .82rem;
  font-weight: 600;
  color: #92400e;
  margin-bottom: .4rem;
}
.step-note {
  font-size: .76rem;
  color: #94a3b8;
  margin-top: .6rem;
  font-style: italic;
}
/* Hide old update action and progress */
.update-action,
.update-progress-notice,
.commands-hint {
  display: none;
}

/* ---- Backup Quick ---- */
.backup-quick {
  padding: .25rem 0 1rem;
  border-bottom: 1px solid #f0f2f5;
}
.backup-quick-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}
.backup-quick-info { display: flex; flex-direction: column; gap: .15rem; }
.backup-quick-label { font-size: .9rem; font-weight: 600; color: #1e293b; }
.backup-quick-hint { font-size: .78rem; color: #94a3b8; }

.backup-primary-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .45rem;
  padding: .6rem 1.3rem;
  border: none;
  border-radius: 8px;
  font-size: .88rem;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  transition: all .2s;
  white-space: nowrap;
  flex-shrink: 0;
}
.backup-primary-btn:hover:not(:disabled) { opacity: .9; transform: translateY(-1px); }
.backup-primary-btn:disabled { opacity: .55; cursor: not-allowed; }

.backup-progress { margin-top: .75rem; }
.progress-bar-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 3px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 3px;
  transition: width .3s ease;
}
.progress-text {
  display: block;
  margin-top: .35rem;
  font-size: .78rem;
  color: #64748b;
}

/* ---- Backup Schedule ---- */
.backup-schedule {
  padding: 1rem 0;
  border-bottom: 1px solid #f0f2f5;
}
.schedule-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.schedule-title { font-size: .9rem; font-weight: 600; color: #1e293b; }

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 24px;
  cursor: pointer;
}
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
  position: absolute;
  inset: 0;
  background: #cbd5e1;
  border-radius: 12px;
  transition: background .2s;
}
.toggle-slider::before {
  content: '';
  position: absolute;
  width: 18px;
  height: 18px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: transform .2s;
}
.toggle-switch input:checked + .toggle-slider { background: #667eea; }
.toggle-switch input:checked + .toggle-slider::before { transform: translateX(18px); }

.schedule-fields { margin-top: .75rem; display: flex; flex-direction: column; gap: .6rem; }
.schedule-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: .6rem;
}
.schedule-field { display: flex; flex-direction: column; gap: .25rem; }
.field-select-sm, .field-input-sm {
  padding: .5rem .65rem;
  font-size: .85rem;
  min-height: 38px;
}
.schedule-hint {
  font-size: .78rem;
  color: #94a3b8;
  line-height: 1.4;
}

/* ---- Local Restore ---- */
.backup-local-restore {
  padding: 1rem 0;
  border-bottom: 1px solid #f0f2f5;
}

.restore-header {
  display: flex;
  flex-direction: column;
  gap: .15rem;
  margin-bottom: .75rem;
}
.restore-title {
  font-size: .9rem;
  font-weight: 600;
  color: #1e293b;
}
.restore-hint {
  font-size: .78rem;
  color: #94a3b8;
}

/* Dropzone */
.restore-dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: 1.75rem 1rem;
  border: 2px dashed #cbd5e1;
  border-radius: 10px;
  background: #f8fafc;
  cursor: pointer;
  transition: all .25s ease;
  position: relative;
}
.local-restore-file-input {
  display: none;
}
.restore-dropzone:hover,
.restore-dropzone-active {
  border-color: #667eea;
  background: #f0f2ff;
  box-shadow: inset 0 0 0 1px rgba(102,126,234,.08);
}
.restore-dropzone-active {
  border-color: #667eea;
  background: #eef0ff;
  transform: scale(1.01);
}
.restore-dropzone-icon {
  color: #94a3b8;
  transition: color .25s;
}
.restore-dropzone:hover .restore-dropzone-icon,
.restore-dropzone-active .restore-dropzone-icon {
  color: #667eea;
}
.restore-dropzone-text {
  font-size: .85rem;
  color: #475569;
  font-weight: 500;
}
.restore-dropzone-divider {
  font-size: .75rem;
  color: #cbd5e1;
  letter-spacing: .02em;
}
.restore-browse-btn {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  padding: .45rem 1rem;
  border: 1.5px solid #cbd5e1;
  border-radius: 6px;
  background: white;
  color: #475569;
  font-size: .82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all .2s;
}
.restore-browse-btn:hover {
  border-color: #667eea;
  color: #667eea;
  background: #f8faff;
}

/* File Preview Card */
.restore-preview {
  display: flex;
  flex-direction: column;
  gap: .75rem;
}
.restore-file-card {
  display: flex;
  align-items: center;
  gap: .75rem;
  padding: .75rem .85rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
}
.restore-file-card-icon {
  flex-shrink: 0;
  color: #667eea;
  opacity: .85;
}
.restore-file-card-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: .15rem;
}
.restore-file-card-name {
  font-size: .85rem;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.restore-file-card-meta {
  font-size: .76rem;
  color: #94a3b8;
}
.restore-file-card-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  border-radius: 6px;
  transition: all .15s;
  flex-shrink: 0;
}
.restore-file-card-remove:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* Restore Action Button */
.restore-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  padding: .65rem 0;
  width: 100%;
  border: none;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  box-shadow: 0 2px 6px rgba(102,126,234,.25);
  transition: all .2s ease;
}
.restore-action-btn:hover {
  box-shadow: 0 4px 12px rgba(102,126,234,.35);
  transform: translateY(-1px);
}
.restore-action-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(102,126,234,.2);
}

.restore-warning {
  margin: 0;
  font-size: .76rem;
  color: #b45309;
  text-align: center;
  line-height: 1.45;
}

/* Restore Progress */
.restore-progress-section {
  display: flex;
  flex-direction: column;
  gap: .6rem;
}
.restore-progress-header {
  display: flex;
  align-items: center;
  gap: .55rem;
}
.restore-progress-spinner {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 2.5px solid #e0e7ff;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
.restore-progress-label {
  font-size: .85rem;
  font-weight: 600;
  color: #1e293b;
}
.restore-progress-track {
  position: relative;
  height: 8px;
  background: #e2e8f0;
  border-radius: 4px;
  overflow: hidden;
}
.restore-progress-fill {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, #667eea, #764ba2);
  border-radius: 4px;
  transition: width .4s ease;
}
.restore-progress-shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255,255,255,.35) 30%,
    rgba(255,255,255,.35) 70%,
    transparent 100%
  );
  border-radius: 4px;
  animation: shimmer 2s ease-in-out infinite;
}
@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.restore-progress-status {
  font-size: .78rem;
  color: #64748b;
}

/* ---- Backup History ---- */
.backup-history { padding-top: 1rem; }
.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: .6rem;
}
.history-title { font-size: .9rem; font-weight: 600; color: #1e293b; }
.refresh-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border: none;
  background: none;
  cursor: pointer;
  color: #94a3b8;
  border-radius: 6px;
  transition: all .2s;
}
.refresh-btn:hover { background: #f1f5f9; color: #475569; }
.spin-anim { animation: spin .8s linear infinite; }

.history-empty {
  text-align: center;
  padding: 2rem 1rem;
  color: #94a3b8;
  font-size: .88rem;
}

.history-list { display: flex; flex-direction: column; gap: .5rem; }
.history-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .7rem .85rem;
  background: #f8fafc;
  border-radius: 8px;
  gap: .75rem;
  transition: background .15s;
}
.history-item:hover { background: #f1f5f9; }
.history-item-main { flex: 1; min-width: 0; }
.history-item-top {
  display: flex;
  align-items: center;
  gap: .5rem;
  flex-wrap: wrap;
}
.history-type-badge {
  font-size: .72rem;
  padding: .15rem .45rem;
  border-radius: 4px;
  font-weight: 600;
}
.history-type-badge.manual { background: #e0e7ff; color: #3730a3; }
.history-type-badge.scheduled { background: #fef3c7; color: #92400e; }
.history-type-badge.restore { background: #fce7f3; color: #9d174d; }

.history-status {
  display: inline-flex;
  align-items: center;
  gap: .3rem;
  font-size: .75rem;
  font-weight: 500;
}
.history-status.pending { color: #b45309; }
.history-status.running { color: #2563eb; }
.history-status.completed { color: #16a34a; }
.history-status.failed { color: #dc2626; }

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid #bfdbfe;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin .6s linear infinite;
}

.history-date {
  font-size: .78rem;
  color: #94a3b8;
  margin-left: auto;
}
.history-item-detail {
  display: flex;
  align-items: center;
  gap: .6rem;
  margin-top: .25rem;
  flex-wrap: wrap;
}
.history-size, .history-files, .history-creator {
  font-size: .78rem;
  color: #64748b;
}
.history-progress-msg {
  font-size: .78rem;
  color: #2563eb;
}
.history-error {
  font-size: .78rem;
  color: #dc2626;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-actions {
  display: flex;
  gap: .35rem;
  flex-shrink: 0;
}
.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  background: transparent;
}
.action-btn.download { color: #667eea; }
.action-btn.download:hover { background: #e0e7ff; }
.action-btn.restore { color: #16a34a; }
.action-btn.restore:hover { background: #dcfce7; }
.action-btn.delete { color: #94a3b8; }
.action-btn.delete:hover { background: #fee2e2; color: #dc2626; }

/* ---- Restore Modal ---- */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}
.modal-content {
  background: white;
  border-radius: 14px;
  padding: 2rem;
  max-width: 420px;
  width: 100%;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, .15);
}
.modal-icon { font-size: 2.5rem; margin-bottom: .75rem; }
.modal-title { margin: 0 0 .5rem; font-size: 1.1rem; font-weight: 700; color: #1e293b; }
.modal-desc {
  font-size: .88rem;
  color: #475569;
  line-height: 1.6;
  margin: 0 0 1.25rem;
}
.modal-desc strong { color: #dc2626; }

.restore-progress { margin-bottom: 1.25rem; }
.modal-actions {
  display: flex;
  gap: .75rem;
  justify-content: center;
}
.modal-btn {
  padding: .6rem 1.5rem;
  border-radius: 8px;
  font-size: .9rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all .2s;
  display: inline-flex;
  align-items: center;
  gap: .4rem;
}
.modal-btn.cancel {
  background: #f1f5f9;
  color: #475569;
}
.modal-btn.cancel:hover { background: #e2e8f0; }
.modal-btn.confirm {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: white;
}
.modal-btn.confirm:hover:not(:disabled) { opacity: .9; }
.modal-btn:disabled { opacity: .55; cursor: not-allowed; }

.modal-fade-enter-active, .modal-fade-leave-active { transition: opacity .2s ease; }
.modal-fade-enter-from, .modal-fade-leave-to { opacity: 0; }

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .settings-page { padding: 0; }
  .page-header h1 { font-size: 1.3rem; }
  .config-card { padding: 1.15rem; border-radius: 10px; }
  .schedule-row { grid-template-columns: 1fr; }
  .backup-quick-row { flex-direction: column; align-items: flex-start; }
  .backup-primary-btn { width: 100%; }
  .restore-dropzone { padding: 1.25rem .75rem; }
  .restore-file-card { flex-wrap: wrap; }
  .history-item { flex-direction: column; align-items: flex-start; }
  .history-actions { align-self: flex-end; }
  .modal-content { padding: 1.5rem; }
}
@media (max-width: 480px) {
  .page-header h1 { font-size: 1.15rem; }
  .page-subtitle { font-size: 0.8rem; }
  .config-card { padding: 0.9rem; border-radius: 8px; }
  .card-header h2 { font-size: 1rem; }
  .config-card input,
  .config-card select,
  .config-card textarea { font-size: 16px; min-height: 44px; }
  .schedule-row select,
  .schedule-row input { min-height: 44px; }
  .form-actions-row { flex-direction: column; gap: 0.5rem; }
  .form-actions-row button { width: 100%; min-height: 44px; justify-content: center; }
  .backup-quick-row .quick-input { width: 100%; min-height: 44px; }
  .restore-browse-btn { min-height: 44px; }
  .restore-action-btn { min-height: 44px; }
  .history-item { padding: 0.75rem; }
  .history-actions { align-self: stretch; display: flex; gap: 4px; }
  .history-actions .action-btn { min-width: 44px; min-height: 44px; }
  .modal-content { padding: 1rem; max-width: 95vw; }
  .forbidden-card { padding: 2rem 1rem; }
  .command-block code { font-size: 0.72rem; white-space: pre-wrap; word-break: break-all; }
}
</style>
