<template>
  <div class="purchases-page">
    <div class="page-header">
      <button @click="goBack" class="back-button">← 返回</button>
      <h1 class="page-title">{{ event?.event_name || '购买记录' }}</h1>
      <div class="header-actions">
        <button @click="showAddModal = true" class="action-button primary">+ 添加记录</button>
        <button @click="viewMembers" class="action-button members">👥 查看人员</button>
        <button @click="exportData" class="action-button export">📤 导出数据</button>
        <button @click="batchReimburse" class="action-button reimburse" :disabled="selectedRecords.length === 0" v-if="canReview">
          批量报销 ({{ selectedRecords.length }})
        </button>
        <button @click="deleteSelected" class="action-button danger" :disabled="selectedRecords.length === 0">
          删除 ({{ selectedRecords.length }})
        </button>
      </div>
    </div>

    <!-- 统计面板 -->
    <div v-if="stats" class="stats-panel">
      <div class="stat-card total">
        <span class="stat-label">总支出</span>
        <span class="stat-value">¥ {{ formatMoney(stats.total_amount) }}</span>
      </div>
      <div class="stat-card invoice">
        <span class="stat-label">发票总额</span>
        <span class="stat-value">¥ {{ formatMoney(stats.invoice_total) }}</span>
      </div>
      <div class="stat-card pending">
        <span class="stat-label">待报销</span>
        <span class="stat-value">¥ {{ formatMoney(stats.pending_reimburse) }}</span>
      </div>
      <div class="stat-card count">
        <span class="stat-label">记录数</span>
        <span class="stat-value">{{ stats.total_count }}</span>
      </div>
    </div>

    <!-- 过滤面板 -->
    <div class="filter-panel">
      <div class="filter-header">
        <div class="filter-header-left">
          <button @click="filterCollapsed = !filterCollapsed" class="collapse-btn" :title="filterCollapsed ? '展开筛选' : '收起筛选'">
            <span class="collapse-icon">{{ filterCollapsed ? '▶' : '▼' }}</span>
          </button>
          <h3>筛选条件</h3>
        </div>
        <button @click="resetFilters" class="reset-btn">重置</button>
      </div>
      <div v-show="!filterCollapsed" class="filter-grid">
        <div class="filter-group filter-group-span-2">
          <label>日期范围</label>
          <div class="date-range">
            <input v-model="filters.startDate" type="date" placeholder="开始日期" />
            <span class="range-separator">至</span>
            <input v-model="filters.endDate" type="date" placeholder="结束日期" />
          </div>
        </div>
        <div class="filter-group filter-group-span-2">
          <label>金额范围</label>
          <div class="amount-range">
            <input v-model.number="filters.minAmount" type="number" step="0.01" min="0" placeholder="最小金额" />
            <span class="range-separator">至</span>
            <input v-model.number="filters.maxAmount" type="number" step="0.01" min="0" placeholder="最大金额" />
          </div>
        </div>
        <div class="filter-group">
          <label>上传人</label>
          <input v-model="filters.uploader" type="text" placeholder="搜索上传人" />
        </div>
        <div class="filter-group">
          <label>发票状态</label>
          <select v-model="filters.invoiceStatus">
            <option value="">全部</option>
            <option value="has_invoice">有发票</option>
            <option value="no_invoice">无发票</option>
          </select>
        </div>
        <div class="filter-group">
          <label>审核状态</label>
          <select v-model="filters.reviewStatus">
            <option value="">全部</option>
            <option value="pending">待审核</option>
            <option value="approved">已通过</option>
            <option value="rejected">已拒绝</option>
          </select>
        </div>
        <div class="filter-group">
          <label>报销状态</label>
          <select v-model="filters.reimburseStatus">
            <option value="">全部</option>
            <option value="reimbursed">已报销</option>
            <option value="not_reimbursed">未报销</option>
          </select>
        </div>
      </div>
      <div v-show="!filterCollapsed" class="filter-actions">
        <button @click="applyFilters" class="apply-btn">应用筛选</button>
      </div>
    </div>

    <!-- 排序与操作栏 -->
    <div class="records-toolbar">
      <div class="sort-control">
        <label>排序方式：</label>
        <select v-model="sortBy" class="sort-select">
          <option value="default">上传顺序</option>
          <option value="purchase_date">购物时间</option>
          <option value="item_name">名称（字典序）</option>
          <option value="purchase_platform">平台</option>
          <option value="amount">金额</option>
        </select>
        <button @click="sortAsc = !sortAsc" class="sort-order-btn" :title="sortAsc ? '升序' : '降序'">
          {{ sortAsc ? '↑ 升序' : '↓ 降序' }}
        </button>
      </div>
      <div class="toolbar-right">
        <span class="record-count">共 {{ filteredRecords.length }} 条记录</span>
      </div>
    </div>

    <!-- 购买记录列表 -->
    <div class="records-table-container">
      <table class="records-table">
        <thead>
          <tr>
            <th class="checkbox-col"><input type="checkbox" v-model="selectAll" @change="toggleSelectAll" /></th>
            <th>物品名称</th>
            <th>平台</th>
            <th>金额</th>
            <th>购物日期</th>
            <th>上传人</th>
            <th>发票状态</th>
            <th>审核状态</th>
            <th>报销状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in filteredRecords" :key="record.display_id || record.record_id" :class="{ 'has-invoice': record.has_invoice, 'is-invoice-record': record.record_type === 'invoice' }">
            <td class="checkbox-col">
              <input type="checkbox" :value="record.display_id || record.record_id" v-model="selectedRecords" />
            </td>
            <td>
              {{ record.item_name }}
              <span v-if="record.record_type === 'invoice'" class="record-type-tag">发票</span>
              <span v-else class="record-type-tag purchase">购物</span>
            </td>
            <td><span class="platform-badge">{{ record.purchase_platform || '-' }}</span></td>
            <td class="amount">¥{{ parseFloat(record.amount).toFixed(2) }}</td>
            <td>{{ formatDate(record.purchase_date) }}</td>
            <td>{{ record.uploader_name || '未知' }}</td>
            <td>
              <span class="invoice-badge" :class="record.has_invoice ? 'yes' : 'no'">
                {{ record.has_invoice ? '有发票' : '无发票' }}
              </span>
            </td>
            <td>
              <span class="status-badge" :class="record.status">{{ getStatusText(record.status) }}</span>
            </td>
            <td>
              <span class="reimburse-badge" :class="{ 'is-reimbursed': record.is_reimbursed }">
                {{ record.is_reimbursed ? '已报销' : '未报销' }}
              </span>
            </td>
            <td>
              <div class="action-buttons">
                <button @click="viewRecord(record)" class="btn-view-sm" title="查看详情">👁</button>
                <button v-if="canModifyRecord(record)" @click="editRecord(record)" class="btn-edit-sm" title="编辑">✏</button>
                <button v-if="record.has_invoice && !record.is_reimbursed && canReview" @click="reimburseRecord(record)" class="btn-reimburse-sm" title="报销">💰</button>
                <button v-if="canReview && record.status === 'pending'" @click="approveRecord(record)" class="btn-approve-sm" title="通过">✓</button>
                <button v-if="canModifyRecord(record)" @click="deleteSingle(record)" class="btn-delete-sm" title="删除">X</button>
              </div>
            </td>
          </tr>
          <tr v-if="filteredRecords.length === 0">
            <td :colspan="10" class="empty-row">没有符合条件的购买记录</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 添加/编辑记录弹窗 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="closeAddModal">
        <div class="modal-content large">
          <!-- 顶部装饰条 -->
          <div class="modal-accent"></div>

          <div class="modal-header">
            <div class="modal-title-group">
              <h2>{{ editingRecord ? '编辑购买记录' : '添加购买记录' }}</h2>
              <span class="modal-subtitle">{{ editingRecord ? '修改购买信息和发票详情' : '填写购买信息并上传凭证' }}</span>
            </div>
            <button @click="closeAddModal" class="close-btn">&times;</button>
          </div>

          <div class="modal-body">
            <form @submit.prevent="saveRecord" class="purchase-form">
              <!-- 基本信息 -->
              <div class="form-section">
                <div class="section-header-row">
                  <div class="section-icon-box blue">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
                  </div>
                  <h3 class="section-title">基本信息</h3>
                  <span class="required-tag">必填</span>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>物品/项目名称</label>
                    <div class="input-shell">
                      <input v-model="form.item_name" type="text" required placeholder="如：键盘、鼠标、交通费等" />
                    </div>
                  </div>
                  <div class="form-group">
                    <label>购买平台</label>
                    <div class="input-shell">
                      <select v-model="form.purchase_platform" required>
                        <option value="">请选择平台</option>
                        <option value="淘宝">淘宝</option>
                        <option value="京东">京东</option>
                        <option value="拼多多">拼多多</option>
                        <option value="闲鱼">闲鱼</option>
                        <option value="天猫">天猫</option>
                        <option value="当当">当当</option>
                        <option value="美团">美团</option>
                        <option value="饿了么">饿了么</option>
                        <option value="线下实体店">线下实体店</option>
                        <option value="其他">其他</option>
                      </select>
                    </div>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label>实际开销（元）</label>
                    <div class="input-shell">
                      <span class="input-prefix">&yen;</span>
                      <input v-model.number="form.amount" type="number" step="0.01" min="0" required placeholder="0.00" class="has-prefix" />
                    </div>
                  </div>
                  <div class="form-group">
                    <label>购物时间</label>
                    <div class="input-shell">
                      <input v-model="form.purchase_date" type="date" required />
                    </div>
                  </div>
                </div>
                <div class="form-group">
                  <label>备注</label>
                  <div class="input-shell">
                    <textarea v-model="form.remarks" rows="2" placeholder="可选，填写其他说明"></textarea>
                  </div>
                </div>
              </div>

              <!-- 购物凭证 -->
              <div class="form-section">
                <div class="section-header-row">
                  <div class="section-icon-box green">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                  </div>
                  <h3 class="section-title">购物凭证</h3>
                  <span class="required-tag">必填</span>
                </div>
                <div class="upload-area" :class="{ 'has-file': receiptPreviewSrc }" @click="$refs.receiptInput.click()">
                  <input ref="receiptInput" type="file" accept="image/*" @change="handleReceiptUpload" hidden />
                  <div v-if="!receiptPreviewSrc" class="upload-placeholder">
                    <div class="upload-icon-circle">
                      <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                    </div>
                    <p class="upload-main-text">点击上传购物凭证图片</p>
                    <p class="upload-hint">支持 JPG、PNG 格式</p>
                  </div>
                  <div v-else class="file-preview">
                    <div class="receipt-preview-container">
                      <div class="fixed-preview-box receipt-fixed">
                        <img :src="receiptPreviewSrc" class="preview-img" @click.stop="showImageModal(receiptPreviewSrc)" />
                        <button type="button" @click.stop="$refs.receiptInput.click()" class="reupload-overlay-btn" title="重新上传">
                          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                        </button>
                      </div>
                      <div class="file-info-bar">
                        <span class="file-info-name">{{ form.receipt_image_name || '凭证图片' }}</span>
                        <span v-if="receiptFileSize" class="file-info-size">{{ receiptFileSize }}</span>
                      </div>
                    </div>
                    <button type="button" @click.stop="removeReceipt" class="remove-btn" title="移除">
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                    </button>
                  </div>
                </div>
              </div>

              <!-- 发票信息 -->
              <div class="form-section invoice-section" :class="{ 'section-active': form.has_invoice }">
                <div class="section-header-row">
                  <div class="section-icon-box amber">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1Z"/></svg>
                  </div>
                  <h3 class="section-title">发票信息</h3>
                  <label class="toggle-switch">
                    <input type="checkbox" v-model="form.has_invoice" />
                    <span class="toggle-track"><span class="toggle-thumb"></span></span>
                    <span class="toggle-label">{{ form.has_invoice ? '有发票' : '无发票' }}</span>
                  </label>
                </div>

                  <div v-if="form.has_invoice" class="invoice-form">
                    <!-- AI解析状态提示 -->
                    <div v-if="aiParseError" class="ai-error-banner">
                      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                      <span>{{ aiParseError }}</span>
                      <button type="button" @click="aiParseError = ''" class="ai-error-close">&times;</button>
                    </div>

                    <!-- 上传发票 -->
                    <div class="invoice-upload-zone" :class="{ 'has-file': form.invoice_file_key || invoiceLocalFile }" @click="$refs.invoiceInput.click()">
                      <input ref="invoiceInput" type="file" accept=".pdf,image/*" @change="handleInvoiceUpload" hidden />
                      <div v-if="!form.invoice_file_key && !invoiceLocalFile" class="upload-placeholder">
                        <div class="upload-icon-circle amber">
                          <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                        </div>
                        <p class="upload-main-text">点击上传发票文件</p>
                        <p class="upload-hint">支持 PDF、JPG、PNG 格式</p>
                      </div>
                      <div v-else class="invoice-file-bar">
                        <div class="invoice-file-icon">
                          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        <div class="invoice-file-meta">
                          <span class="invoice-file-name">{{ form.invoice_original_filename || '发票文件' }}</span>
                          <span v-if="invoiceFileSize" class="invoice-file-size">{{ invoiceFileSize }}</span>
                        </div>
                        <div class="invoice-file-actions">
                          <button type="button" @click.stop="$refs.invoiceInput.click()" class="invoice-action-btn" title="重新上传">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                          </button>
                          <button type="button" @click.stop="removeInvoice" class="invoice-action-btn danger" title="移除">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                          </button>
                        </div>
                      </div>
                    </div>

                    <!-- 发票预览区域 -->
                    <div v-if="form.invoice_file_key || invoiceLocalFile" class="invoice-details">
                      <div v-if="form._preview_display_url || form.invoice_file_key || _invoice_blob_url" class="invoice-preview-panel">
                        <div class="preview-panel-header">
                          <div class="preview-panel-title">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
                            <span>发票预览</span>
                          </div>
                          <button
                            v-if="!parsingInvoice && !invoiceImageLoading"
                            type="button"
                            @click.stop="parseInvoiceFromUrl"
                            class="ai-parse-trigger"
                          >
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a10 10 0 1 0 10 10"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                            {{ parseApplied ? '重新解析' : 'AI解析' }}
                          </button>
                          <span v-else-if="parsingInvoice" class="ai-parsing-badge">
                            <span class="btn-spinner-sm"></span>
                            解析中...
                          </span>
                        </div>

                        <div class="image-container" @click.stop="invoiceFilePreviewSrc && !imageLoadingError ? showImageModal(invoiceFilePreviewSrc) : undefined">
                          <div v-if="invoiceImageLoading" class="image-loading">
                            <div class="loading-spinner"></div>
                            <p>图片加载中...</p>
                          </div>

                          <img
                            v-else-if="!imageLoadingError && invoiceFilePreviewSrc"
                            :src="invoiceFilePreviewSrc"
                            class="invoice-thumbnail"
                            @load="onInvoiceImageLoad"
                            @error="onInvoiceImageError"
                            title="点击查看大图"
                            :alt="form.invoice_original_filename || '发票图片'"
                          />

                          <div v-else-if="form._is_pdf || isPdfFile(form._preview_display_url)" class="pdf-preview-card">
                            <div class="pdf-icon-wrap">
                              <svg viewBox="0 0 48 48" width="44" height="44" fill="none"><rect x="6" y="2" width="36" height="44" rx="4" fill="#f59e0b" opacity="0.1"/><rect x="6" y="2" width="36" height="44" rx="4" stroke="#f59e0b" stroke-width="1.5"/><path d="M14 16h20M14 22h20M14 28h14" stroke="#f59e0b" stroke-width="1.5" stroke-linecap="round"/><text x="24" y="42" text-anchor="middle" font-size="8" font-weight="700" fill="#f59e0b">PDF</text></svg>
                            </div>
                            <div class="pdf-info">
                              <span class="pdf-filename">{{ form.invoice_original_filename || '发票文件.pdf' }}</span>
                              <span class="pdf-hint">PDF已上传，可AI解析或手动填写</span>
                            </div>
                          </div>

                          <div v-else class="image-error">
                            <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#ef4444" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                            <p>图片加载失败</p>
                            <button type="button" @click="retryLoadImage" class="retry-btn">重试</button>
                          </div>
                        </div>
                      </div>

                      <!-- 发票详情表单 -->
                      <div class="invoice-fields-grid">
                        <div class="form-group">
                          <label>商品名称</label>
                          <div class="input-shell">
                            <input v-model="form.item_name_from_invoice" type="text" placeholder="自动提取或手动填写" />
                          </div>
                        </div>
                        <div class="form-group">
                          <label>发票号码</label>
                          <div class="input-shell">
                            <input v-model="form.invoice_number" type="text" placeholder="自动提取或手动填写" />
                          </div>
                        </div>
                        <div class="form-group">
                          <label>价税合计（元）</label>
                          <div class="input-shell">
                            <span class="input-prefix">&yen;</span>
                            <input v-model.number="form.total_amount" type="number" step="0.01" min="0" placeholder="0.00" class="has-prefix" />
                          </div>
                        </div>
                        <div class="form-group">
                          <label>开票时间</label>
                          <div class="input-shell">
                            <input v-model="form.invoice_date" type="date" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
              </div>

              <!-- 操作按钮 -->
              <div class="form-actions">
                <button type="button" @click="closeAddModal" class="cancel-btn">取消</button>
                <button type="submit" class="submit-btn" :disabled="saving">
                  <span v-if="saving" class="btn-spinner-sm"></span>
                  {{ saving ? '保存中...' : (editingRecord ? '保存修改' : '提交记录') }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

    <!-- 详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal-content large detail-modal">
        <div class="modal-header">
          <h2>购买记录详情</h2>
          <button @click="showDetailModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body" v-if="currentRecord">
          <!-- 基本信息 -->
          <div class="detail-section">
            <div class="detail-section-label">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
              <span>基本信息</span>
            </div>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">物品名称</span>
                <span class="detail-value">{{ currentRecord.item_name }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">购买平台</span>
                <span class="detail-value">{{ currentRecord.purchase_platform }}</span>
              </div>
              <div class="detail-item accent">
                <span class="detail-label">实际开销</span>
                <span class="detail-value amount">&yen;{{ parseFloat(currentRecord.amount).toFixed(2) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">购物日期</span>
                <span class="detail-value">{{ formatDate(currentRecord.purchase_date) }}</span>
              </div>
              <div v-if="currentRecord.remarks" class="detail-item full-width">
                <span class="detail-label">备注</span>
                <span class="detail-value">{{ currentRecord.remarks }}</span>
              </div>
            </div>
          </div>

          <!-- 发票信息 -->
          <div v-if="currentRecord.has_invoice" class="detail-section">
            <div class="detail-section-label amber">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 2v20l2-1 2 1 2-1 2 1 2-1 2 1 2-1 2 1V2l-2 1-2-1-2 1-2-1-2 1-2-1-2 1-2-1Z"/></svg>
              <span>发票信息</span>
            </div>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">发票号码</span>
                <span class="detail-value mono">{{ currentRecord.invoice_number || '-' }}</span>
              </div>
              <div class="detail-item accent">
                <span class="detail-label">价税合计</span>
                <span class="detail-value amount">&yen;{{ parseFloat(currentRecord.total_amount || 0).toFixed(2) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">开票时间</span>
                <span class="detail-value">{{ formatDate(currentRecord.invoice_date) }}</span>
              </div>
              <div v-if="currentRecord.item_name_from_invoice" class="detail-item">
                <span class="detail-label">商品名称</span>
                <span class="detail-value">{{ currentRecord.item_name_from_invoice }}</span>
              </div>
            </div>
          </div>

          <!-- 图片预览 -->
          <div class="detail-section">
            <div class="detail-section-label">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
              <span>图片预览</span>
            </div>
            <div class="detail-images">
              <div class="detail-image-card">
                <div class="detail-image-header">购物凭证</div>
                <div class="detail-image-body" @click="showImageModal(getFullImageUrl(currentRecord.receipt_image_url))">
                  <img
                    :src="getFullImageUrl(currentRecord.receipt_image_url)"
                    class="detail-preview-img"
                    @error="(e) => e.target.style.display='none'"
                  />
                  <div class="detail-image-hint">点击放大查看</div>
                </div>
              </div>
              <div v-if="currentRecord.has_invoice" class="detail-image-card">
                <div class="detail-image-header amber">发票预览</div>
                <div class="detail-image-body" @click="invoiceDetailPreviewUrl ? showImageModal(invoiceDetailPreviewUrl) : undefined">
                  <img
                    v-if="invoiceDetailPreviewUrl"
                    :src="invoiceDetailPreviewUrl"
                    class="detail-preview-img"
                    @error="(e) => { e.target.style.display='none'; invoiceDetailPreviewError = true }"
                  />
                  <div v-if="!invoiceDetailPreviewUrl || invoiceDetailPreviewError" class="detail-image-empty">
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#d1d5db" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <span>暂无发票预览</span>
                  </div>
                  <div v-if="invoiceDetailPreviewUrl && !invoiceDetailPreviewError" class="detail-image-hint">点击放大查看</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 图片放大弹窗 (支持缩放/拖拽/手势) -->
    <div
      v-if="showImageZoomModal"
      ref="zoomOverlayRef"
      class="image-zoom-overlay"
      @wheel.prevent="onZoomWheel"
      @mousedown="onZoomMouseDown"
      @mousemove="onZoomMouseMove"
      @mouseup="onZoomMouseUp"
      @mouseleave="onZoomMouseUp"
      @touchstart="onZoomTouchStart"
      @touchmove.prevent="onZoomTouchMove"
      @touchend="onZoomTouchEnd"
    >
      <button @click="showImageZoomModal = false" class="zoom-close-btn">&times;</button>
      <div class="zoom-controls">
        <button @click="zoomScale = Math.min(5, zoomScale + 0.5)" title="放大">+</button>
        <span>{{ Math.round(zoomScale * 100) }}%</span>
        <button @click="zoomScale = Math.max(0.5, zoomScale - 0.5)" title="缩小">-</button>
        <button @click="resetZoom" title="重置">1:1</button>
      </div>
      <img
        ref="zoomImageRef"
        :src="zoomImageUrl"
        class="zoomed-image"
        :style="zoomImageStyle"
        draggable="false"
      />
    </div>

    <!-- Toast通知 -->
      <div v-if="toastVisible" class="toast-notification" :class="toastType">
        <span class="toast-icon" v-if="toastType === 'success'">&#10003;</span>
        <span class="toast-icon" v-else-if="toastType === 'error'">&#10007;</span>
        <span class="toast-icon" v-else>&#9432;</span>
        <span class="toast-text">{{ toastMessage }}</span>
      </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useEventStore } from '~/stores/eventStore'

definePageMeta({ layout: 'default' })

const { $api } = useNuxtApp()
const route = useRoute()
const router = useRouter()
const eventStore = useEventStore()

const eventId = computed(() => route.params.id)
const event = ref(null)
const records = ref([])
const stats = ref(null)
const selectedRecords = ref([])
const showAddModal = ref(false)
const showDetailModal = ref(false)
const editingRecord = ref(null)
const currentRecord = ref(null)
const invoiceDetailPreviewError = ref(false)
const saving = ref(false)
const parsingInvoice = ref(false)
const showImageZoomModal = ref(false)
const zoomImageUrl = ref('')
const invoiceParseResult = ref(null)
const parseApplied = ref(false)
const imageLoadingError = ref(false)
const invoiceImageLoading = ref(false)
const aiParseError = ref('')

// 拖拽/缩放状态
const zoomScale = ref(1)
const zoomPanX = ref(0)
const zoomPanY = ref(0)
const isDragging = ref(false)
const dragStartX = ref(0)
const dragStartY = ref(0)
const dragStartPanX = ref(0)
const dragStartPanY = ref(0)
const lastTouchDist = ref(0)
const zoomOverlayRef = ref(null)
const zoomImageRef = ref(null)

// 本地文件存储（延迟上传）
const receiptLocalFile = ref(null)
const invoiceLocalFile = ref(null)
const _receipt_blob_url = ref('')
const _invoice_blob_url = ref('')
const _invoice_preview_blob = ref(null) // PDF转图片的Blob，用于上传到服务器

// 计算预览源（本地blob优先）
const receiptPreviewSrc = computed(() => {
  return _receipt_blob_url.value || form.value.receipt_image_url || ''
})
const invoiceFilePreviewSrc = computed(() => {
  if (_invoice_blob_url.value) return _invoice_blob_url.value
  if (form.value._preview_display_url) return getFullImageUrl(form.value._preview_display_url)
  return ''
})
const invoiceDetailPreviewUrl = computed(() => {
  if (!currentRecord.value) return ''
  const r = currentRecord.value
  // 优先使用预览URL（来自COS预签名或本地路径），回退到发票文件URL
  const url = r.invoice_preview_url || r.invoice_url || ''
  return url ? getFullImageUrl(url) : ''
})
const receiptFileSize = computed(() => {
  if (receiptLocalFile.value) return formatFileSize(receiptLocalFile.value.size)
  return ''
})
const invoiceFileSize = computed(() => {
  if (invoiceLocalFile.value) return formatFileSize(invoiceLocalFile.value.size)
  return ''
})
const zoomImageStyle = computed(() => ({
  transform: `translate(${zoomPanX.value}px, ${zoomPanY.value}px) scale(${zoomScale.value})`,
  cursor: isDragging.value ? 'grabbing' : 'grab'
}))

// Toast notification
const toastMessage = ref('')
const toastType = ref('info')
const toastVisible = ref(false)
let toastTimer = null

function showToast(msg, type = 'info', duration = 3000) {
  toastMessage.value = msg
  toastType.value = type
  toastVisible.value = true
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toastVisible.value = false }, duration)
}

function isPdfFile(url) {
  if (!url) return false
  const clean = url.split('?')[0].toLowerCase()
  return clean.endsWith('.pdf')
}

function formatFileSize(bytes) {
  if (!bytes) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

// ========== 图片缩放/拖拽 ==========
function resetZoom() {
  zoomScale.value = 1
  zoomPanX.value = 0
  zoomPanY.value = 0
}

function onZoomWheel(e) {
  const delta = e.deltaY > 0 ? -0.15 : 0.15
  zoomScale.value = Math.max(0.5, Math.min(5, zoomScale.value + delta))
}

function onZoomMouseDown(e) {
  if (e.target.closest('.zoom-close-btn') || e.target.closest('.zoom-controls')) return
  isDragging.value = true
  dragStartX.value = e.clientX
  dragStartY.value = e.clientY
  dragStartPanX.value = zoomPanX.value
  dragStartPanY.value = zoomPanY.value
}

function onZoomMouseMove(e) {
  if (!isDragging.value) return
  zoomPanX.value = dragStartPanX.value + (e.clientX - dragStartX.value)
  zoomPanY.value = dragStartPanY.value + (e.clientY - dragStartY.value)
}

function onZoomMouseUp() {
  isDragging.value = false
}

function onZoomTouchStart(e) {
  if (e.touches.length === 2) {
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    lastTouchDist.value = Math.sqrt(dx * dx + dy * dy)
  } else if (e.touches.length === 1) {
    isDragging.value = true
    dragStartX.value = e.touches[0].clientX
    dragStartY.value = e.touches[0].clientY
    dragStartPanX.value = zoomPanX.value
    dragStartPanY.value = zoomPanY.value
  }
}

function onZoomTouchMove(e) {
  if (e.touches.length === 2) {
    const dx = e.touches[0].clientX - e.touches[1].clientX
    const dy = e.touches[0].clientY - e.touches[1].clientY
    const dist = Math.sqrt(dx * dx + dy * dy)
    if (lastTouchDist.value > 0) {
      const scaleDiff = (dist - lastTouchDist.value) * 0.008
      zoomScale.value = Math.max(0.5, Math.min(5, zoomScale.value + scaleDiff))
    }
    lastTouchDist.value = dist
  } else if (e.touches.length === 1 && isDragging.value) {
    zoomPanX.value = dragStartPanX.value + (e.touches[0].clientX - dragStartX.value)
    zoomPanY.value = dragStartPanY.value + (e.touches[0].clientY - dragStartY.value)
  }
}

function onZoomTouchEnd(e) {
  if (e.touches.length < 2) lastTouchDist.value = 0
  if (e.touches.length === 0) isDragging.value = false
}

const form = ref({
  item_name: '',
  purchase_platform: '',
  purchase_date: '',
  amount: null,
  remarks: '',
  receipt_image_url: '',
  receipt_image_name: '',
  receipt_file_md5: '',
  has_invoice: false,
  invoice_file_key: '',
  invoice_preview_key: '',
  invoice_original_filename: '',
  invoice_md5: '',
  _preview_display_url: '',
  _is_pdf: false,
  item_name_from_invoice: '',
  invoice_number: '',
  total_amount: null,
  invoice_date: ''
})

const currentUser = ref(null)

// 缩放弹窗 ESC 关闭
watch(showImageZoomModal, (val) => {
  if (val) {
    resetZoom()
    const handler = (e) => { if (e.key === 'Escape') showImageZoomModal.value = false }
    document.addEventListener('keydown', handler)
    showImageZoomModal._handler = handler
  } else {
    if (showImageZoomModal._handler) {
      document.removeEventListener('keydown', showImageZoomModal._handler)
      delete showImageZoomModal._handler
    }
  }
})

// 过滤条件
const filters = ref({
  startDate: '',
  endDate: '',
  minAmount: null,
  maxAmount: null,
  uploader: '',
  invoiceStatus: '',
  reviewStatus: '',
  reimburseStatus: ''
})

const filterCollapsed = ref(false)
const sortBy = ref('default')
const sortAsc = ref(false)

// 过滤后的记录
const filteredRecords = computed(() => {
  let result = records.value.filter(record => {
    // 日期过滤
    if (filters.value.startDate) {
      const recordDate = new Date(record.purchase_date)
      const startDate = new Date(filters.value.startDate)
      if (recordDate < startDate) return false
    }
    if (filters.value.endDate) {
      const recordDate = new Date(record.purchase_date)
      const endDate = new Date(filters.value.endDate)
      endDate.setHours(23, 59, 59, 999)
      if (recordDate > endDate) return false
    }

    // 金额过滤
    if (filters.value.minAmount !== null && filters.value.minAmount !== '') {
      if (parseFloat(record.amount) < filters.value.minAmount) return false
    }
    if (filters.value.maxAmount !== null && filters.value.maxAmount !== '') {
      if (parseFloat(record.amount) > filters.value.maxAmount) return false
    }

    // 上传人过滤
    if (filters.value.uploader) {
      const uploaderName = record.uploader_name || ''
      if (!uploaderName.toLowerCase().includes(filters.value.uploader.toLowerCase())) return false
    }

    // 发票状态过滤
    if (filters.value.invoiceStatus) {
      if (filters.value.invoiceStatus === 'has_invoice' && !record.has_invoice) return false
      if (filters.value.invoiceStatus === 'no_invoice' && record.has_invoice) return false
    }

    // 审核状态过滤
    if (filters.value.reviewStatus && record.status) {
      if (record.status !== filters.value.reviewStatus) return false
    }

    // 报销状态过滤
    if (filters.value.reimburseStatus) {
      if (filters.value.reimburseStatus === 'reimbursed' && !record.is_reimbursed) return false
      if (filters.value.reimburseStatus === 'not_reimbursed' && record.is_reimbursed) return false
    }

    return true
  })

  // 排序
  result = [...result].sort((a, b) => {
    let cmp = 0
    switch (sortBy.value) {
      case 'purchase_date':
        cmp = new Date(a.purchase_date || 0) - new Date(b.purchase_date || 0)
        break
      case 'item_name':
        cmp = (a.item_name || '').localeCompare(b.item_name || '', 'zh')
        break
      case 'purchase_platform':
        cmp = (a.purchase_platform || '').localeCompare(b.purchase_platform || '', 'zh')
        break
      case 'amount':
        cmp = parseFloat(a.amount || 0) - parseFloat(b.amount || 0)
        break
      default:
        cmp = new Date(a.created_at || 0) - new Date(b.created_at || 0)
        break
    }
    return sortAsc.value ? cmp : -cmp
  })

  return result
})

// 应用过滤
const applyFilters = () => {
}

// 重置过滤
const resetFilters = () => {
  filters.value = {
    startDate: '',
    endDate: '',
    minAmount: null,
    maxAmount: null,
    uploader: '',
    invoiceStatus: '',
    reviewStatus: '',
    reimburseStatus: ''
  }
}

const canReview = computed(() => {
  return ['admin', 'teacher', 'student_admin'].includes(currentUser.value?.user_type)
})

const canModifyRecord = (record) => {
  if (!currentUser.value) return false
  if (['admin', 'teacher', 'student_admin'].includes(currentUser.value.user_type)) return true
  return record.uploader_id === currentUser.value.user_id
}

const selectAll = computed({
  get: () => selectedRecords.value.length === records.value.length && records.value.length > 0,
  set: (val) => {
    if (val) {
      selectedRecords.value = records.value.map(r => r.record_id)
    } else {
      selectedRecords.value = []
    }
  }
})

onMounted(async () => {
  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null
  
  await loadEvent()
  await loadRecords()
})

const goBack = () => {
  router.push('/projects')
}

const viewMembers = () => {
  router.push(`/events/${eventId.value}/members`)
}

const loadEvent = async () => {
  try {
    const token = localStorage.getItem('token')
    const response = await $api.get(`/events/${eventId.value}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (response.data.code === 200) {
      event.value = response.data.data
      stats.value = {
        total_amount: response.data.data.spent_amount || 0,
        invoice_total: response.data.data.invoice_total_amount || 0,
        pending_reimburse: (parseFloat(response.data.data.invoice_total_amount || 0) - parseFloat(response.data.data.reimbursed_amount || 0)),
        total_count: (response.data.data.invoice_count || 0) + (response.data.data.purchase_record_count || 0)
      }
    }
  } catch (e) {
    console.error('加载赛事失败:', e.message)
  }
}

const loadRecords = async () => {
  try {
    const token = localStorage.getItem('token')
    
    const [purchaseResponse, invoiceResponse] = await Promise.all([
      $api.get(`/events/${eventId.value}/records`, {
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => ({ data: { code: 200, data: { records: [] } } })),
      $api.get(`/invoices?event_id=${eventId.value}`, {
        headers: { Authorization: `Bearer ${token}` }
      }).catch(() => ({ data: { code: 200, data: { invoices: [] } } }))
    ])
    
    let allRecords = []
    
    if (purchaseResponse.data.code === 200 && purchaseResponse.data.data?.records) {
      allRecords = allRecords.concat(purchaseResponse.data.data.records.map(r => ({
        ...r,
        record_type: 'purchase',
        display_id: `P${r.record_id}`
      })))
    }
    
    if (invoiceResponse.data.code === 200 && invoiceResponse.data.data?.invoices) {
      allRecords = allRecords.concat(invoiceResponse.data.data.invoices.map(inv => ({
        record_id: inv.invoice_id,
        item_name: inv.project_name || inv.file_name,
        purchase_platform: '发票上传',
        purchase_date: inv.invoice_date,
        amount: inv.amount,
        receipt_image_url: inv.image_url,
        receipt_image_name: inv.file_name,
        has_invoice: true,
        invoice_url: inv.image_url,
        invoice_name: inv.file_name,
        invoice_type: inv.invoice_type,
        invoice_number: inv.invoice_number,
        total_amount: inv.total_amount,
        invoice_date: inv.invoice_date,
        status: inv.status,
        is_reimbursed: inv.is_reimbursed,
        uploader_id: inv.uploader_id,
        uploader_name: inv.uploader_name,
        remarks: inv.remarks,
        created_at: inv.created_at,
        record_type: 'invoice',
        display_id: `I${inv.invoice_id}`
      })))
    }
    
    records.value = allRecords
    
    // 每次加载记录时都更新统计数据
    stats.value = {
      total_amount: allRecords.reduce((sum, r) => sum + parseFloat(r.amount || 0), 0),
      invoice_total: allRecords.filter(r => r.has_invoice).reduce((sum, r) => sum + parseFloat(r.total_amount || r.amount || 0), 0),
      pending_reimburse: allRecords.filter(r => r.has_invoice && !r.is_reimbursed).reduce((sum, r) => sum + parseFloat(r.total_amount || r.amount || 0), 0),
      total_count: allRecords.length
    }
  } catch (e) {
    console.error('加载记录失败:', e.message)
  }
}

const toggleSelectAll = () => {}

const viewRecord = (record) => {
  currentRecord.value = record
  invoiceDetailPreviewError.value = false
  showDetailModal.value = true
}

const editRecord = (record) => {
  editingRecord.value = record
  // 清理旧blob URL
  if (_receipt_blob_url.value) URL.revokeObjectURL(_receipt_blob_url.value)
  if (_invoice_blob_url.value) URL.revokeObjectURL(_invoice_blob_url.value)
  _receipt_blob_url.value = ''
  _invoice_blob_url.value = ''
  receiptLocalFile.value = null
  invoiceLocalFile.value = null
  aiParseError.value = ''

  form.value = {
    item_name: record.item_name,
    purchase_platform: record.purchase_platform,
    purchase_date: record.purchase_date,
    amount: record.amount,
    remarks: record.remarks || '',
    receipt_image_url: record.receipt_image_url,
    receipt_image_name: record.receipt_image_name,
    receipt_file_md5: record.receipt_file_md5 || '',
    has_invoice: record.has_invoice,
    invoice_file_key: record.invoice_file_key || '',
    invoice_preview_key: record.invoice_preview_key || '',
    invoice_original_filename: record.invoice_original_filename || '',
    invoice_md5: record.invoice_md5 || '',
    _preview_display_url: record.invoice_preview_url || record.invoice_url || '',
    _is_pdf: record.invoice_file_key?.endsWith('.pdf') || false,
    item_name_from_invoice: record.item_name_from_invoice || record.invoice_type || '',
    invoice_number: record.invoice_number || '',
    total_amount: record.total_amount || null,
    invoice_date: record.invoice_date || ''
  }
  showAddModal.value = true
}

const closeAddModal = () => {
  showAddModal.value = false
  editingRecord.value = null
  resetForm()
  if (_receipt_blob_url.value) URL.revokeObjectURL(_receipt_blob_url.value)
  if (_invoice_blob_url.value) URL.revokeObjectURL(_invoice_blob_url.value)
  _receipt_blob_url.value = ''
  _invoice_blob_url.value = ''
  receiptLocalFile.value = null
  invoiceLocalFile.value = null
}

const resetForm = () => {
  form.value = {
    item_name: '',
    purchase_platform: '',
    purchase_date: '',
    amount: null,
    remarks: '',
    receipt_image_url: '',
    receipt_image_name: '',
    receipt_file_md5: '',
    has_invoice: false,
    invoice_file_key: '',
    invoice_preview_key: '',
    invoice_original_filename: '',
    invoice_md5: '',
    _preview_display_url: '',
    _is_pdf: false,
    item_name_from_invoice: '',
    invoice_number: '',
    total_amount: null,
    invoice_date: ''
  }
  invoiceParseResult.value = null
  parseApplied.value = false
  aiParseError.value = ''
}

const handleReceiptUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 释放旧blob URL
  if (_receipt_blob_url.value) URL.revokeObjectURL(_receipt_blob_url.value)

  receiptLocalFile.value = file
  _receipt_blob_url.value = URL.createObjectURL(file)
  form.value.receipt_image_name = file.name
  form.value.receipt_image_url = '' // 清除旧服务器URL

  // 异步计算MD5用于提交时去重
  try {
    form.value.receipt_file_md5 = await calculateFileMD5(file)
  } catch (_) {}

  e.target.value = ''
}

const calculateFileMD5 = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const buffer = new Uint8Array(e.target.result)
        // Pure JS MD5 implementation
        function md5cycle(x, k) {
          let a = x[0], b = x[1], c = x[2], d = x[3]
          a = ff(a, b, c, d, k[0], 7, -680876936); d = ff(d, a, b, c, k[1], 12, -389564586)
          c = ff(c, d, a, b, k[2], 17, 606105819); b = ff(b, c, d, a, k[3], 22, -1044525330)
          a = ff(a, b, c, d, k[4], 7, -176418897); d = ff(d, a, b, c, k[5], 12, 1200080426)
          c = ff(c, d, a, b, k[6], 17, -1473231341); b = ff(b, c, d, a, k[7], 22, -45705983)
          a = ff(a, b, c, d, k[8], 7, 1770035416); d = ff(d, a, b, c, k[9], 12, -1958414417)
          c = ff(c, d, a, b, k[10], 17, -42063); b = ff(b, c, d, a, k[11], 22, -1990404162)
          a = ff(a, b, c, d, k[12], 7, 1804603682); d = ff(d, a, b, c, k[13], 12, -40341101)
          c = ff(c, d, a, b, k[14], 17, -1502002290); b = ff(b, c, d, a, k[15], 22, 1236535329)
          a = gg(a, b, c, d, k[1], 5, -165796510); d = gg(d, a, b, c, k[6], 9, -1069501632)
          c = gg(c, d, a, b, k[11], 14, 643717713); b = gg(b, c, d, a, k[0], 20, -373897302)
          a = gg(a, b, c, d, k[5], 5, -701558691); d = gg(d, a, b, c, k[10], 9, 38016083)
          c = gg(c, d, a, b, k[15], 14, -660478335); b = gg(b, c, d, a, k[4], 20, -405537848)
          a = gg(a, b, c, d, k[9], 5, 568446438); d = gg(d, a, b, c, k[14], 9, -1019803690)
          c = gg(c, d, a, b, k[3], 14, -187363961); b = gg(b, c, d, a, k[8], 20, 1163531501)
          a = gg(a, b, c, d, k[13], 5, -1444681467); d = gg(d, a, b, c, k[2], 9, -51403784)
          c = gg(c, d, a, b, k[7], 14, 1735328473); b = gg(b, c, d, a, k[12], 20, -1926607734)
          a = hh(a, b, c, d, k[5], 4, -378558); d = hh(d, a, b, c, k[8], 11, -2022574463)
          c = hh(c, d, a, b, k[11], 16, 1839030562); b = hh(b, c, d, a, k[14], 23, -35309556)
          a = hh(a, b, c, d, k[1], 4, -1530992060); d = hh(d, a, b, c, k[4], 11, 1272893353)
          c = hh(c, d, a, b, k[7], 16, -155497632); b = hh(b, c, d, a, k[10], 23, -1094730640)
          a = hh(a, b, c, d, k[13], 4, 681279174); d = hh(d, a, b, c, k[0], 11, -358537222)
          c = hh(c, d, a, b, k[3], 16, -722521979); b = hh(b, c, d, a, k[6], 23, 76029189)
          a = hh(a, b, c, d, k[9], 4, -640364487); d = hh(d, a, b, c, k[12], 11, -421815835)
          c = hh(c, d, a, b, k[15], 16, 530742520); b = hh(b, c, d, a, k[2], 23, -995338651)
          a = ii(a, b, c, d, k[0], 6, -198630844); d = ii(d, a, b, c, k[7], 10, 1126891415)
          c = ii(c, d, a, b, k[14], 15, -1416354905); b = ii(b, c, d, a, k[5], 21, -57434055)
          a = ii(a, b, c, d, k[12], 6, 1700485571); d = ii(d, a, b, c, k[3], 10, -1894986606)
          c = ii(c, d, a, b, k[10], 15, -1051523); b = ii(b, c, d, a, k[1], 21, -2054922799)
          a = ii(a, b, c, d, k[8], 6, 1873313359); d = ii(d, a, b, c, k[15], 10, -30611744)
          c = ii(c, d, a, b, k[6], 15, -1560198380); b = ii(b, c, d, a, k[13], 21, 1309151649)
          a = ii(a, b, c, d, k[4], 6, -145523070); d = ii(d, a, b, c, k[11], 10, -1120210379)
          c = ii(c, d, a, b, k[2], 15, 718787259); b = ii(b, c, d, a, k[9], 21, -343485551)
          x[0] = add32(a, x[0]); x[1] = add32(b, x[1]); x[2] = add32(c, x[2]); x[3] = add32(d, x[3])
        }
        function cmn(q, a, b, x, s, t) { a = add32(add32(a, q), add32(x, t)); return add32((a << s) | (a >>> (32 - s)), b) }
        function ff(a, b, c, d, x, s, t) { return cmn((b & c) | ((~b) & d), a, b, x, s, t) }
        function gg(a, b, c, d, x, s, t) { return cmn((b & d) | (c & (~d)), a, b, x, s, t) }
        function hh(a, b, c, d, x, s, t) { return cmn(b ^ c ^ d, a, b, x, s, t) }
        function ii(a, b, c, d, x, s, t) { return cmn(c ^ (b | (~d)), a, b, x, s, t) }
        function md51(s) {
          const n = s.length, state = [1732584193, -271733879, -1732584194, 271733878]
          let i
          for (i = 64; i <= n; i += 64) md5cycle(state, md5blk(s.subarray(i - 64, i)))
          s = s.subarray(i - 64)
          const tail = new Uint8Array(64)
          tail.set(s)
          tail[s.length] = 0x80
          if (s.length < 56) {
            tail[56] = (n * 8) & 0xff; tail[57] = (n >>> 3) & 0xff; tail[58] = (n >>> 11) & 0xff; tail[59] = (n >>> 19) & 0xff
            tail[60] = (n * 8) >>> 24; tail[61] = 0; tail[62] = 0; tail[63] = 0
          } else {
            md5cycle(state, md5blk(tail))
            tail.fill(0)
            tail[56] = (n * 8) & 0xff; tail[57] = (n >>> 3) & 0xff; tail[58] = (n >>> 11) & 0xff; tail[59] = (n >>> 19) & 0xff
            tail[60] = (n * 8) >>> 24
          }
          md5cycle(state, md5blk(tail))
          return state
        }
        function md5blk(s) {
          const blks = new Int32Array(16)
          for (let i = 0; i < 16; i++) blks[i] = s[i * 4] | (s[i * 4 + 1] << 8) | (s[i * 4 + 2] << 16) | (s[i * 4 + 3] << 24)
          return blks
        }
        function add32(a, b) { return (a + b) & 0xFFFFFFFF }
        function rhex(n) {
          const hc = '0123456789abcdef'
          let s = ''
          for (let j = 0; j < 4; j++) s += hc.charAt((n >> (j * 8 + 4)) & 0x0f) + hc.charAt((n >> (j * 8)) & 0x0f)
          return s
        }
        const x = md51(buffer)
        resolve(rhex(x[0]) + rhex(x[1]) + rhex(x[2]) + rhex(x[3]))
      } catch (error) {
        reject(error)
      }
    }
    reader.onerror = () => reject(reader.error)
    reader.readAsArrayBuffer(file)
  })
}

/**
 * 将PDF文件的第一页转换为图片Blob
 */
async function convertPdfToImage(file) {
  const pdfjsLib = await import('pdfjs-dist')
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    `https://cdn.jsdelivr.net/npm/pdfjs-dist@4.10.38/build/pdf.worker.min.mjs`

  const arrayBuffer = await file.arrayBuffer()
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
  const page = await pdf.getPage(1)

  const scale = 2.0
  const viewport = page.getViewport({ scale })
  const canvas = document.createElement('canvas')
  canvas.width = viewport.width
  canvas.height = viewport.height

  const ctx = canvas.getContext('2d')
  await page.render({ canvasContext: ctx, viewport }).promise

  return new Promise((resolve) => {
    canvas.toBlob((blob) => {
      resolve(blob)
    }, 'image/jpeg', 0.92)
  })
}

const handleInvoiceUpload = async (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 释放旧blob URL
  if (_invoice_blob_url.value) URL.revokeObjectURL(_invoice_blob_url.value)
  _invoice_preview_blob.value = null

  invoiceLocalFile.value = file
  const isPdf = file.name.toLowerCase().endsWith('.pdf')

  if (!isPdf) {
    _invoice_blob_url.value = URL.createObjectURL(file)
  } else {
    // PDF文件：转换为图片预览
    try {
      invoiceImageLoading.value = true
      const imageBlob = await convertPdfToImage(file)
      _invoice_preview_blob.value = imageBlob
      _invoice_blob_url.value = URL.createObjectURL(imageBlob)
    } catch (err) {
      console.error('PDF转图片失败:', err.message)
      _invoice_blob_url.value = ''
      _invoice_preview_blob.value = null
    } finally {
      invoiceImageLoading.value = false
    }
  }

  form.value.invoice_original_filename = file.name
  form.value._is_pdf = isPdf
  form.value.invoice_file_key = ''
  form.value.has_invoice = true

  try {
    form.value.invoice_md5 = await calculateFileMD5(file)
  } catch (_) {}

  imageLoadingError.value = false
  invoiceParseResult.value = null
  parseApplied.value = false
  aiParseError.value = ''

  e.target.value = ''

  // 自动触发AI解析
  await autoParseLocalInvoice()
}

const removeReceipt = () => {
  if (_receipt_blob_url.value) URL.revokeObjectURL(_receipt_blob_url.value)
  _receipt_blob_url.value = ''
  receiptLocalFile.value = null
  form.value.receipt_image_url = ''
  form.value.receipt_image_name = ''
  form.value.receipt_file_md5 = ''
}

const removeInvoice = () => {
  if (_invoice_blob_url.value) URL.revokeObjectURL(_invoice_blob_url.value)
  _invoice_blob_url.value = ''
  _invoice_preview_blob.value = null
  invoiceLocalFile.value = null
  form.value.invoice_file_key = ''
  form.value.invoice_preview_key = ''
  form.value.invoice_original_filename = ''
  form.value.invoice_md5 = ''
  form.value._preview_display_url = ''
  form.value._is_pdf = false
  form.value.has_invoice = false
  invoiceParseResult.value = null
  parseApplied.value = false
  aiParseError.value = ''
}

const showImageModal = (imageUrl) => {
  zoomImageUrl.value = getFullImageUrl(imageUrl)
  showImageZoomModal.value = true
}

const getFullImageUrl = (url) => {
  if (!url) return ''

  // blob: 和 data: URL 直接返回
  if (url.startsWith('blob:') || url.startsWith('data:')) {
    return url
  }

  // 如果已经是完整URL（http/https），直接返回
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url
  }

  // 如果是相对路径，根据当前环境确定基础URL
  const isDev = window.location.hostname === 'localhost' ||
                window.location.hostname === '127.0.0.1' ||
                window.location.hostname === '::1'

  const apiBase = isDev
    ? 'http://localhost:5000'
    : `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':' + window.location.port : ''}`

  const cleanPath = url.startsWith('/') ? url : `/${url}`
  return `${apiBase}${cleanPath}`
}

const onInvoiceImageLoad = () => {
  invoiceImageLoading.value = false
  imageLoadingError.value = false
}

const onInvoiceImageError = (e) => {
  invoiceImageLoading.value = false
  imageLoadingError.value = true
}

const retryLoadImage = () => {
  imageLoadingError.value = false
  invoiceImageLoading.value = true
  
  const currentUrl = form.value._preview_display_url || form.value.invoice_preview_url || form.value.invoice_url
  if (currentUrl) {
    const timestamp = Date.now()
    const separator = currentUrl.includes('?') ? '&' : '?'
    form.value._preview_display_url = `${currentUrl}${separator}_t=${timestamp}`
    
    setTimeout(() => {
      invoiceImageLoading.value = false
    }, 100)
  }
}

/**
 * 对本地发票文件执行AI解析（上传到parse-invoice端点）
 */
const autoParseLocalInvoice = async () => {
  if (!invoiceLocalFile.value) return

  // 获取用于AI解析的图片：PDF用转换后的预览图，图片直接用原文件
  const imageBlob = _invoice_preview_blob.value || invoiceLocalFile.value
  if (!imageBlob) return

  parsingInvoice.value = true
  invoiceParseResult.value = null
  parseApplied.value = false
  aiParseError.value = ''

  try {
    const token = localStorage.getItem('token')
    const formData = new FormData()
    const filename = invoiceLocalFile.value.name.replace(/\.pdf$/i, '.jpg')
    formData.append('file', imageBlob, filename)

    const response = await $api.post('/parse-image', formData, {
      headers: { Authorization: `Bearer ${token}` },
      timeout: 60000
    })

    if (response.data.code === 200 && response.data.data?.parsed_info) {
      const info = response.data.data.parsed_info
      invoiceParseResult.value = {
        item_name: info.item_name || '',
        invoice_number: info.invoice_number || '',
        amount: info.amount ? String(info.amount) : '',
        date: info.date || ''
      }
      if (info.item_name) form.value.item_name_from_invoice = info.item_name
      if (info.invoice_number) form.value.invoice_number = info.invoice_number
      if (info.amount) form.value.total_amount = parseFloat(info.amount)
      if (info.date) form.value.invoice_date = info.date
      parseApplied.value = true
      showToast('发票解析完成', 'success')
    } else {
      aiParseError.value = 'AI服务暂时不可用，请手动填写信息'
    }
  } catch (err) {
    console.error('发票解析失败:', err.message)
    aiParseError.value = 'AI服务暂时不可用，请手动填写信息'
  } finally {
    parsingInvoice.value = false
  }
}

const parseInvoiceFromUrl = async () => {
  if (!form.value.invoice_file_key && !invoiceLocalFile.value) {
    showToast('请先上传发票文件', 'error')
    return
  }

  // 如果有本地文件但还没有服务器key，先执行上传解析
  if (invoiceLocalFile.value && !form.value.invoice_file_key) {
    await autoParseLocalInvoice()
    return
  }

  parsingInvoice.value = true
  invoiceParseResult.value = null
  parseApplied.value = false

  try {
    const token = localStorage.getItem('token')
    let response

    if (editingRecord.value) {
      response = await $api.post(`/records/${editingRecord.value.record_id}/re-parse-invoice`, {}, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 120000
      })
    } else {
      showToast('发票信息已在上传时自动解析，请查看上方表单', 'info')
      parsingInvoice.value = false
      return
    }

    if (response.data.code === 200 && response.data.data?.parsed_info) {
      const info = response.data.data.parsed_info

      invoiceParseResult.value = {
        item_name: info.item_name || '',
        invoice_number: info.invoice_number || '',
        amount: info.amount ? String(info.amount) : '',
        date: info.date || ''
      }

      if (info.item_name) form.value.item_name_from_invoice = info.item_name
      if (info.invoice_number) form.value.invoice_number = info.invoice_number
      if (info.amount) form.value.total_amount = parseFloat(info.amount)
      if (info.date) form.value.invoice_date = info.date

      parseApplied.value = true
      showToast('发票重新解析完成', 'success')
    } else {
      showToast(response.data.message || '解析失败', 'error')
    }
  } catch (err) {
    console.error('解析失败:', err.message)
    const msg = err.response?.data?.message || '解析失败，请重试'
    showToast(msg, 'error')
  } finally {
    parsingInvoice.value = false
  }
}

const saveRecord = async () => {
  // 验证：必须有购物凭证（本地文件或已有服务器URL）
  if (!receiptLocalFile.value && !form.value.receipt_image_url) {
    alert('请上传购物凭证图片')
    return
  }

  saving.value = true
  aiParseError.value = ''

  try {
    const token = localStorage.getItem('token')
    const payload = { ...form.value }

    // === 步骤1: 上传购物凭证（如有新文件） ===
    if (receiptLocalFile.value) {
      const receiptForm = new FormData()
      receiptForm.append('file', receiptLocalFile.value)
      const receiptRes = await $api.post('/upload-file', receiptForm, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 60000
      })
      if (receiptRes.data.code === 200) {
        payload.receipt_image_url = receiptRes.data.data.image_url
        payload.receipt_file_md5 = receiptRes.data.data.file_md5 || payload.receipt_file_md5
      } else {
        throw new Error(receiptRes.data.message || '购物凭证上传失败')
      }
    }

    // === 步骤2: 上传发票到COS（如有新文件） ===
    if (invoiceLocalFile.value && payload.has_invoice && !payload.invoice_file_key) {
      const invoiceForm = new FormData()
      invoiceForm.append('file', invoiceLocalFile.value)
      // 附带客户端生成的预览图（PDF转图片），供服务端在自身转换失败时使用
      if (_invoice_preview_blob.value) {
        const previewName = invoiceLocalFile.value.name.replace(/\.pdf$/i, '.jpg')
        invoiceForm.append('preview_file', _invoice_preview_blob.value, previewName)
      }
      try {
        const invoiceRes = await $api.post('/parse-invoice', invoiceForm, {
          headers: { Authorization: `Bearer ${token}` },
          timeout: 120000
        })

        if (invoiceRes.data.code === 409) {
          const d = invoiceRes.data.data
          showToast(`检测到重复发票，已由 ${d.original_uploader || '未知用户'} 上传过`, 'error', 4000)
          saving.value = false
          return
        }

        if (invoiceRes.data.code === 200) {
          const d = invoiceRes.data.data
          payload.invoice_file_key = d.file_key
          payload.invoice_preview_key = d.preview_key
          payload.invoice_md5 = d.file_md5
          payload._preview_display_url = d.preview_url || d.file_url || ''
          payload._is_pdf = d.is_pdf || false

          // 填充AI解析结果
          if (d.parsed_info) {
            const info = d.parsed_info
            if (info.item_name && !payload.item_name) payload.item_name = info.item_name
            if (info.item_name) payload.item_name_from_invoice = info.item_name
            if (info.invoice_number) payload.invoice_number = info.invoice_number
            if (info.amount) payload.total_amount = parseFloat(info.amount)
            if (info.date) payload.invoice_date = info.date
          } else if (!d.parsed_info && !d.is_pdf) {
            // AI解析失败（非PDF），显示错误提示但不阻止提交
            aiParseError.value = 'AI服务暂时不可用，请手动填写信息'
          }
        } else {
          // 非409的其他错误
          aiParseError.value = 'AI服务暂时不可用，请手动填写信息'
        }
      } catch (invErr) {
        console.error('发票上传/解析失败:', invErr.message)
        if (invErr.response?.status === 409) {
          showToast('检测到重复发票文件，请勿重复上传', 'error')
          saving.value = false
          return
        }
        // 网络错误等，显示提示但允许手动填写
        aiParseError.value = 'AI服务暂时不可用，请手动填写信息'
      }
    }

    // === 步骤3: 提交表单数据 ===
    delete payload._preview_display_url
    delete payload._is_pdf

    if (!payload.item_name && payload.item_name_from_invoice) {
      payload.item_name = payload.item_name_from_invoice
    }
    delete payload.item_name_from_invoice

    let response
    if (editingRecord.value) {
      response = await $api.put(`/records/${editingRecord.value.record_id}`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } else {
      payload.event_id = eventId.value
      response = await $api.post(`/events/${eventId.value}/records`, payload, {
        headers: { Authorization: `Bearer ${token}` }
      })
    }

    if (response.data.code === 200 || response.data.code === 201) {
      closeAddModal()
      await loadRecords()
      eventStore.refreshAfterMutation(Number(eventId.value))
      showToast('记录保存成功', 'success')
    } else {
      alert(response.data.message || '保存失败')
    }
  } catch (error) {
    console.error('保存失败:', error.message)
    alert(error.message || '保存失败，请重试')
  } finally {
    saving.value = false
  }
}

const deleteSingle = async (record) => {
  if (!confirm(`确定要删除"${record.item_name}"这条记录吗？`)) return
  
  try {
    const token = localStorage.getItem('token')
    await $api.delete(`/records/${record.record_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
    eventStore.refreshAfterMutation(Number(eventId.value))
  } catch (e) {
    alert('删除失败')
  }
}

const deleteSelected = async () => {
  if (!confirm(`确定要删除选中的 ${selectedRecords.value.length} 条记录吗？`)) return
  
  for (const id of [...selectedRecords.value]) {
    try {
      const token = localStorage.getItem('token')
      await $api.delete(`/records/${id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
    } catch (e) {}
  }
  
  selectedRecords.value = []
  await loadRecords()
  eventStore.refreshAfterMutation(Number(eventId.value))
}

const approveRecord = async (record) => {
  try {
    const token = localStorage.getItem('token')
    await $api.post(`/records/${record.record_id}/approve`, { status: 'approved' }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
    eventStore.refreshAfterMutation(Number(eventId.value))
  } catch (e) {
    alert('操作失败')
  }
}

const reimburseRecord = async (record) => {
  if (!confirm(`确定要报销"${record.item_name}"吗？金额：¥${parseFloat(record.total_amount || record.amount).toFixed(2)}`)) return
  
  try {
    const token = localStorage.getItem('token')
    await $api.post(`/records/${record.record_id}/reimburse`, {}, {
      headers: { Authorization: `Bearer ${token}` }
    })
    await loadRecords()
    eventStore.refreshAfterMutation(Number(eventId.value))
  } catch (e) {
    alert(e.response?.data?.message || '操作失败')
  }
}

const batchReimburse = async () => {
  if (!confirm(`确定要批量报销选中的 ${selectedRecords.value.length} 条记录吗？`)) return
  
  for (const id of [...selectedRecords.value]) {
    const record = records.value.find(r => r.record_id === id)
    if (record?.has_invoice && !record.is_reimbursed) {
      try {
        const token = localStorage.getItem('token')
        await $api.post(`/records/${id}/reimburse`, {}, {
          headers: { Authorization: `Bearer ${token}` }
        })
      } catch (e) {}
    }
  }
  
  selectedRecords.value = []
  await loadRecords()
  eventStore.refreshAfterMutation(Number(eventId.value))
}

const exportData = () => {
  router.push(`/events/${eventId.value}/export`)
}

const getStatusText = (status) => {
  const map = { pending: '待审核', approved: '已通过', rejected: '已拒绝' }
  return map[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const formatMoney = (val) => {
  return parseFloat(val || 0).toFixed(2)
}
</script>

<style scoped>
.purchases-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.back-button {
  padding: 0.6rem 1rem;
  background: #f0f0f0;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}
.back-button:hover { background: #e0e0e0; }

.page-title {
  font-size: 1.8rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.action-button {
  padding: 0.7rem 1.2rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: white;
  font-size: 13px;
  font-weight: 500;
}
.action-button.primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.action-button.members { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }
.action-button.export { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); }
.action-button.reimburse { background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%); }
.action-button.danger { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); }
.action-button:disabled { opacity: 0.5; cursor: not-allowed; }

.stats-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 16px;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  border-left: 4px solid #3498db;
  text-align: center;
}
.stat-card.total { border-left-color: #667eea; }
.stat-card.invoice { border-left-color: #f39c12; }
.stat-card.pending { border-left-color: #e74c3c; }
.stat-card.count { border-left-color: #95a5a6; }

.stat-label { display: block; font-size: 12px; color: #7f8c8d; margin-bottom: 4px; }
.stat-value { display: block; font-size: 20px; font-weight: 700; color: #2c3e50; }

/* 排序与操作栏 */
.records-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  flex-wrap: wrap;
  gap: 0.75rem;
}
.sort-control {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 14px;
  color: #495057;
}
.sort-select {
  padding: 0.45rem 0.75rem;
  border: 1.5px solid #dee2e6;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  color: #2c3e50;
  cursor: pointer;
  outline: none;
}
.sort-select:focus { border-color: #667eea; }
.sort-order-btn {
  padding: 0.45rem 0.75rem;
  border: 1.5px solid #dee2e6;
  border-radius: 6px;
  background: #f8f9fa;
  cursor: pointer;
  font-size: 13px;
  color: #495057;
  transition: all 0.2s;
}
.sort-order-btn:hover { background: #e9ecef; border-color: #ced4da; }
.toolbar-right { display: flex; align-items: center; }
.record-count { font-size: 13px; color: #7f8c8d; }

.records-table-container {
  background: white;
  border-radius: 10px;
  overflow-x: auto;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.records-table {
  width: 100%;
  border-collapse: collapse;
}

.records-table th {
  background: #f8f9fa;
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 2px solid #e9ecef;
  white-space: nowrap;
}

.records-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  font-size: 13px;
  color: #333;
}

.records-table tr:hover { background: #fafbfc; }
.records-table tr.has-invoice { background: #fffbf0; }
.records-table tr.is-invoice-record { background: #f0f7ff; }

.checkbox-col { width: 40px; text-align: center; }
.platform-badge { 
  background: #e8f4fd; 
  color: #2980b9; 
  padding: 2px 8px; 
  border-radius: 10px; 
  font-size: 11px; 
}
.record-type-tag {
  display: inline-block;
  margin-left: 6px;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}
.record-type-tag.purchase { background: #e8f5e9; color: #2e7d32; }
.record-type-tag.invoice { background: #e3f2fd; color: #1565c0; }
.amount { font-weight: 600; color: #e74c3c; }

.invoice-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.invoice-badge.yes { background: #eaffea; color: #27ae60; }
.invoice-badge.no { background: #fff5f5; color: #e74c3c; }

.status-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.status-badge.pending { background: #fff8e6; color: #f39c12; }
.status-badge.approved { background: #eaffea; color: #27ae60; }
.status-badge.rejected { background: #fff5f5; color: #e74c3c; }

.reimburse-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.reimburse-badge:not(.is-reimbursed) { background: #f5f5f5; color: #999; }
.reimburse-badge.is-reimbursed { background: #e8f8f0; color: #27ae60; }

.action-buttons { display: flex; gap: 4px; flex-wrap: wrap; }
.btn-view-sm, .btn-edit-sm, .btn-delete-sm, .btn-approve-sm, .btn-reimburse-sm {
  padding: 4px 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}
.btn-view-sm { background: #3498db; color: white; }
.btn-edit-sm { background: #f39c12; color: white; }
.btn-delete-sm { background: #e74c3c; color: white; }
.btn-approve-sm { background: #27ae60; color: white; }
.btn-reimburse-sm { background: #9b59b6; color: white; }

.empty-row { text-align: center; padding: 40px !important; color: #999; }

/* 过滤面板样式 */
.filter-panel {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  border: 1px solid #e9ecef;
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.2rem;
}

.filter-header-left {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.filter-header h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #2c3e50;
  font-weight: 600;
}

.collapse-btn {
  width: 30px;
  height: 30px;
  border: 1.5px solid #dee2e6;
  border-radius: 6px;
  background: #f8f9fa;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  padding: 0;
}
.collapse-btn:hover {
  background: #e9ecef;
  border-color: #ced4da;
}
.collapse-icon {
  font-size: 10px;
  color: #6c757d;
  transition: transform 0.2s;
}

.reset-btn {
  padding: 0.5rem 1rem;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: #6c757d;
}

.reset-btn:hover {
  background: #e9ecef;
  border-color: #ced4da;
}

.filter-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.filter-group-span-2 {
  grid-column: span 2;
}

.filter-group label {
  font-size: 13px;
  font-weight: 500;
  color: #555;
}

.filter-group input,
.filter-group select {
  padding: 0.6rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.filter-group input:focus,
.filter-group select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,0.1);
}

.date-range,
.amount-range {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.date-range input,
.amount-range input {
  flex: 1;
}

.range-separator {
  font-size: 14px;
  color: #6c757d;
  white-space: nowrap;
}

.filter-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
}

.apply-btn {
  padding: 0.7rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  font-size: 14px;
}

@media (max-width: 768px) {
  .filter-grid {
    grid-template-columns: 1fr;
  }

  .filter-group-span-2 {
    grid-column: span 1;
  }

  .date-range,
  .amount-range {
    flex-direction: column;
    align-items: stretch;
  }

  .range-separator {
    text-align: center;
    padding: 0.2rem 0;
  }

  .records-toolbar {
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
  .sort-control {
    flex-wrap: wrap;
    justify-content: space-between;
  }
  .toolbar-right {
    justify-content: center;
  }
}

/* ========== MODAL OVERLAY ========== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  padding: 20px;
}

.modal-content {
  background: #fff;
  border-radius: 16px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 4px 16px rgba(0,0,0,0.08);
  position: relative;
}
.modal-content.large { max-width: 780px; }

.modal-accent {
  height: 4px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px 16px 0 0;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 1.25rem 1.5rem 1rem;
  border-bottom: 1px solid #f1f5f9;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 10;
  border-radius: 16px 16px 0 0;
}
.modal-title-group { display: flex; flex-direction: column; gap: 2px; }
.modal-header h2 { margin: 0; font-size: 1.2rem; font-weight: 700; color: #0f172a; }
.modal-subtitle { font-size: 0.8rem; color: #94a3b8; }
.close-btn {
  background: #f1f5f9;
  border: none;
  font-size: 1.3rem;
  cursor: pointer;
  color: #64748b;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
}
.close-btn:hover { background: #e2e8f0; color: #0f172a; }

.modal-body { padding: 1.25rem 1.5rem 1.5rem; }

.purchase-form { display: flex; flex-direction: column; gap: 1.25rem; }

/* ========== FORM SECTIONS ========== */
.form-section {
  background: #f8fafc;
  padding: 1.25rem;
  border-radius: 12px;
  border: 1px solid #e8ecf1;
}
.form-section:hover { border-color: #cbd5e1; }

.section-header-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 1rem;
}
.section-icon-box {
  width: 32px; height: 32px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.section-icon-box.blue { background: #eef2ff; color: #6366f1; }
.section-icon-box.green { background: #ecfdf5; color: #10b981; }
.section-icon-box.amber { background: #fffbeb; color: #f59e0b; }

.section-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
  flex: 1;
}
.required-tag {
  font-size: 0.68rem;
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white;
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.invoice-section { border-color: #fef3c7; }
.invoice-section.section-active { border-color: #fde68a; background: #fffbeb; }

/* ========== FORM ROWS & INPUTS ========== */
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }

.form-group { display: flex; flex-direction: column; gap: 0.35rem; }
.form-group label {
  font-size: 0.8rem;
  font-weight: 500;
  color: #475569;
}

.input-shell {
  position: relative;
  display: flex;
  align-items: center;
}
.input-shell input,
.input-shell select,
.input-shell textarea {
  width: 100%;
  padding: 0.65rem 0.85rem;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.88rem;
  color: #1e293b;
  background: #fff;
  outline: none;
}
.input-shell input:focus,
.input-shell select:focus,
.input-shell textarea:focus {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102,126,234,0.08);
}
.input-shell input::placeholder,
.input-shell textarea::placeholder { color: #b0b8c8; }
.input-shell textarea { resize: vertical; min-height: 60px; }

.input-prefix {
  position: absolute;
  left: 0.85rem;
  color: #94a3b8;
  font-size: 0.88rem;
  font-weight: 600;
  pointer-events: none;
}
.input-shell input.has-prefix { padding-left: 1.6rem; }

/* ========== UPLOAD AREA ========== */
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  cursor: pointer;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
}
.upload-area:hover { border-color: #667eea; background: #f8faff; }
.upload-area.has-file { border-style: solid; border-color: #10b981; background: #f0fdf4; }

.upload-placeholder { color: #94a3b8; display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-icon-circle {
  width: 52px; height: 52px; border-radius: 50%;
  background: linear-gradient(135deg, #eef2ff, #e0e7ff);
  color: #6366f1;
  display: flex; align-items: center; justify-content: center;
}
.upload-icon-circle.amber {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  color: #f59e0b;
}
.upload-main-text { font-size: 0.88rem; font-weight: 500; color: #475569; margin: 0; }
.upload-hint { font-size: 0.75rem; color: #94a3b8; margin: 0; }

.file-preview { position: relative; display: inline-block; }
.preview-img {
  max-width: 280px; max-height: 180px;
  border-radius: 10px; object-fit: contain;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.remove-btn {
  position: absolute; top: -8px; right: -8px;
  width: 24px; height: 24px;
  background: #ef4444; color: white;
  border: 2px solid #fff; border-radius: 50%;
  cursor: pointer; font-size: 12px; line-height: 1;
  display: flex; align-items: center; justify-content: center;
}

.file-preview.file-doc {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.75rem 1rem; background: #fff; border-radius: 10px;
  border: 1px solid #e2e8f0; width: 100%;
}
.file-doc-icon { color: #6366f1; flex-shrink: 0; }
.file-name { font-size: 0.85rem; color: #475569; flex: 1; text-align: left; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.remove-btn-inline {
  background: none; border: none; color: #94a3b8; cursor: pointer;
  padding: 4px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
}
.remove-btn-inline:hover { color: #ef4444; background: #fef2f2; }

/* ========== TOGGLE SWITCH ========== */
.toggle-switch {
  display: flex; align-items: center; gap: 8px; cursor: pointer; user-select: none;
}
.toggle-switch input[type="checkbox"] { display: none; }
.toggle-track {
  width: 42px; height: 24px;
  background: #cbd5e1; border-radius: 12px;
  position: relative;
}
.toggle-thumb {
  position: absolute; width: 18px; height: 18px;
  background: #fff; border-radius: 50%;
  top: 3px; left: 3px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.15);
}
.toggle-switch input:checked + .toggle-track { background: #10b981; }
.toggle-switch input:checked + .toggle-track .toggle-thumb { transform: translateX(18px); }
.toggle-label { font-size: 0.8rem; color: #64748b; font-weight: 500; }

/* ========== INVOICE FORM ========== */
.invoice-form { margin-top: 1rem; display: flex; flex-direction: column; gap: 1rem; }
.invoice-upload { border-color: #fde68a; }
.invoice-upload:hover { border-color: #f59e0b; background: #fffbeb; }

.invoice-details { display: flex; flex-direction: column; gap: 1rem; }

/* ========== INVOICE UPLOAD ZONE ========== */
.invoice-upload-zone {
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}
.invoice-upload-zone:hover { border-color: #f59e0b; background: #fffbeb; }
.invoice-upload-zone.has-file {
  border-style: solid;
  border-color: #fde68a;
  background: linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%);
}
.invoice-file-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 16px;
}
.invoice-file-icon {
  flex-shrink: 0;
  width: 40px; height: 40px;
  display: flex; align-items: center; justify-content: center;
  background: #fff; border-radius: 10px;
  border: 1px solid #fde68a;
  color: #f59e0b;
}
.invoice-file-meta {
  flex: 1; min-width: 0;
  display: flex; flex-direction: column; gap: 2px;
}
.invoice-file-name {
  font-size: 0.85rem; font-weight: 600; color: #1e293b;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.invoice-file-size { font-size: 0.75rem; color: #94a3b8; }
.invoice-file-actions {
  display: flex; gap: 6px; flex-shrink: 0;
}
.invoice-action-btn {
  width: 32px; height: 32px;
  display: flex; align-items: center; justify-content: center;
  background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
  cursor: pointer; color: #64748b; transition: all 0.15s ease;
}
.invoice-action-btn:hover { border-color: #f59e0b; color: #f59e0b; background: #fffbeb; }
.invoice-action-btn.danger:hover { border-color: #ef4444; color: #ef4444; background: #fef2f2; }

/* ========== INVOICE PREVIEW PANEL ========== */
.invoice-preview-panel {
  background: #fff;
  border-radius: 12px;
  border: 1px solid #e8ecf1;
  overflow: hidden;
}
.preview-panel-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #fefce8 0%, #fef9c3 100%);
  border-bottom: 1px solid #fde68a;
}
.preview-panel-title {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.85rem; font-weight: 600; color: #92400e;
}
.preview-panel-title svg { color: #f59e0b; }
.ai-parse-trigger {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 14px;
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: white; border: none; border-radius: 8px;
  cursor: pointer; font-size: 0.78rem; font-weight: 600;
  white-space: nowrap; transition: all 0.15s ease;
  box-shadow: 0 2px 8px rgba(245, 158, 11, 0.25);
}
.ai-parse-trigger:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(245, 158, 11, 0.35); }
.ai-parsing-badge {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px;
  background: #f3f4f6; border-radius: 8px;
  font-size: 0.78rem; color: #6b7280; font-weight: 500;
}

.image-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  min-height: 200px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.image-container:hover { background: #fefce8; }
.invoice-thumbnail {
  max-width: 100%; max-height: 320px;
  border-radius: 8px; object-fit: contain;
  border: 1px solid #e5e7eb;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.invoice-thumbnail:hover {
  transform: scale(1.02);
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
}

/* ========== PDF PREVIEW CARD ========== */
.pdf-preview-card {
  display: flex; align-items: center; gap: 14px;
  padding: 1.25rem; background: #fffbeb; border-radius: 10px;
  border: 1px solid #fde68a; width: 100%;
}
.pdf-icon-wrap { flex-shrink: 0; }
.pdf-info { display: flex; flex-direction: column; gap: 3px; }
.pdf-filename { font-size: 0.85rem; font-weight: 600; color: #1e293b; }
.pdf-hint { font-size: 0.75rem; color: #92400e; opacity: 0.7; }

/* ========== IMAGE LOADING / ERROR ========== */
.image-loading {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 180px; min-height: 160px;
  background: #fefce8; border-radius: 10px;
  border: 2px dashed #fde68a;
}
.loading-spinner {
  width: 32px; height: 32px;
  border: 3px solid #fde68a; border-top-color: #f59e0b;
  border-radius: 50%; animation: spin 0.7s linear infinite;
  margin-bottom: 10px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.image-loading p { margin: 0; color: #92400e; font-size: 0.8rem; }

.image-error {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 180px; min-height: 160px;
  background: #fef2f2; border-radius: 10px;
  border: 2px solid #fecaca; gap: 8px;
}
.image-error p { margin: 0; color: #ef4444; font-size: 0.8rem; font-weight: 500; }
.retry-btn {
  padding: 6px 16px;
  background: linear-gradient(135deg, #ef4444, #f87171);
  color: white; border: none; border-radius: 8px;
  cursor: pointer; font-size: 0.8rem; font-weight: 600;
}

.parse-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 14px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white; border: none; border-radius: 8px;
  cursor: pointer; font-size: 0.78rem; font-weight: 600;
  white-space: nowrap;
}
.parse-btn.parsing { background: #94a3b8; cursor: not-allowed; }
.btn-spinner-sm {
  width: 14px; height: 14px;
  border: 2px solid #d97706; border-top-color: transparent;
  border-radius: 50%; animation: spin 0.7s linear infinite;
  display: inline-block;
}

/* ========== INVOICE FIELDS GRID ========== */
.invoice-fields-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;
}

/* ========== AI ERROR BANNER ========== */
.ai-error-banner {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px;
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border: 1px solid #fbbf24;
  border-radius: 10px;
  color: #92400e;
  font-size: 0.85rem;
  font-weight: 500;
}
.ai-error-banner svg { flex-shrink: 0; color: #f59e0b; }
.ai-error-close {
  margin-left: auto;
  background: none; border: none;
  color: #92400e; font-size: 1.2rem;
  cursor: pointer; padding: 0 4px;
  line-height: 1;
}
.ai-error-close:hover { color: #78350f; }

/* ========== RECEIPT PREVIEW ========== */
.receipt-preview-container { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.fixed-preview-box {
  position: relative;
  width: 280px; height: 200px;
  border-radius: 10px; overflow: hidden;
  background: #f8fafc;
  border: 2px solid #e8ecf0;
  display: flex; align-items: center; justify-content: center;
}
.fixed-preview-box .preview-img {
  max-width: 100%; max-height: 100%;
  width: auto; height: auto;
  object-fit: contain;
  cursor: pointer;
}
.reupload-overlay-btn {
  position: absolute; top: 8px; right: 8px;
  width: 28px; height: 28px;
  background: rgba(255,255,255,0.9);
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: #64748b;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.reupload-overlay-btn:hover { background: #fff; color: #667eea; border-color: #667eea; }
.reupload-overlay-btn.amber:hover { color: #f59e0b; border-color: #f59e0b; }

.file-info-bar {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.75rem; color: #94a3b8;
  max-width: 280px; width: 100%;
}
.file-info-name {
  flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  color: #64748b; font-weight: 500;
}
.file-info-size { flex-shrink: 0; color: #94a3b8; }

/* ========== INVOICE FILE THUMBNAIL (kept for other usages) ========== */
.invoice-file-thumb-wrap {
  position: relative; flex-shrink: 0;
  width: 80px; height: 80px;
  border-radius: 8px; overflow: hidden;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
}
.invoice-file-thumb {
  width: 100%; height: 100%;
  object-fit: cover;
}
.file-doc-info {
  display: flex; flex-direction: column; gap: 2px;
  flex: 1; min-width: 0;
}

/* ========== IMAGE ZOOM OVERLAY ========== */
.image-zoom-overlay {
  position: fixed; inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.92);
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.zoom-close-btn {
  position: fixed; top: 20px; right: 20px;
  background: rgba(255,255,255,0.15);
  color: white; border: none;
  font-size: 1.8rem; cursor: pointer;
  width: 44px; height: 44px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  z-index: 2010;
  line-height: 1;
}
.zoom-close-btn:hover { background: rgba(255,255,255,0.3); }
.zoom-controls {
  position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 4px;
  background: rgba(0,0,0,0.7);
  border-radius: 10px; padding: 6px 10px;
  z-index: 2010;
}
.zoom-controls button {
  background: rgba(255,255,255,0.15); color: white;
  border: none; border-radius: 6px;
  width: 36px; height: 32px;
  cursor: pointer; font-size: 1rem; font-weight: 600;
  display: flex; align-items: center; justify-content: center;
}
.zoom-controls button:hover { background: rgba(255,255,255,0.3); }
.zoom-controls span {
  color: rgba(255,255,255,0.8);
  font-size: 0.78rem; font-weight: 500;
  min-width: 44px; text-align: center;
}
.zoomed-image {
  max-width: 90vw; max-height: 85vh;
  object-fit: contain;
  user-select: none;
  -webkit-user-drag: none;
  will-change: transform;
}

/* ========== FORM ACTIONS ========== */
.form-actions {
  display: flex; justify-content: flex-end; gap: 0.75rem;
  padding-top: 1rem; border-top: 1px solid #f1f5f9;
}
.cancel-btn {
  padding: 0.65rem 1.25rem;
  background: #f1f5f9; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 10px;
  cursor: pointer; font-size: 0.88rem; font-weight: 500;
}
.cancel-btn:hover { background: #e2e8f0; }
.submit-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 0.65rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white; border: none; border-radius: 10px;
  cursor: pointer; font-size: 0.88rem; font-weight: 600;
  box-shadow: 0 2px 8px rgba(102,126,234,0.25);
}
.submit-btn:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

/* ========== TOAST NOTIFICATION ========== */
.toast-notification {
  position: fixed; top: 24px; right: 24px; z-index: 3000;
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px; border-radius: 12px;
  font-size: 0.85rem; font-weight: 500;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  max-width: 380px;
}
.toast-notification.success { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.toast-notification.error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.toast-notification.info { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.toast-icon { font-size: 1rem; flex-shrink: 0; }
.toast-text { line-height: 1.4; }

/* ========== DETAIL MODAL ========== */
.detail-modal .modal-body { padding: 0; }
.detail-section {
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #f1f5f9;
}
.detail-section:last-child { border-bottom: none; }
.detail-section-label {
  display: flex; align-items: center; gap: 8px;
  font-size: 0.85rem; font-weight: 700; color: #1e293b;
  margin-bottom: 1rem;
  letter-spacing: 0.02em;
}
.detail-section-label svg { color: #f59e0b; }
.detail-section-label.amber svg { color: #f59e0b; }

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.detail-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0.75rem 1rem;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
}
.detail-item.full-width { grid-column: span 2; }
.detail-item.accent {
  background: linear-gradient(135deg, #fffbeb, #fef3c7);
  border-color: #fde68a;
}
.detail-label {
  font-size: 0.72rem; color: #94a3b8; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.detail-value { font-size: 0.9rem; color: #1e293b; font-weight: 600; }
.detail-value.amount { font-size: 1.1rem; color: #dc2626; font-weight: 800; font-variant-numeric: tabular-nums; }
.detail-value.mono { font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace; letter-spacing: 0.03em; }

/* ========== DETAIL IMAGE PREVIEWS ========== */
.detail-images {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.detail-image-card {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: #fff;
}
.detail-image-header {
  padding: 8px 14px;
  font-size: 0.78rem; font-weight: 700; color: #475569;
  background: #f8fafc;
  border-bottom: 1px solid #e5e7eb;
}
.detail-image-header.amber {
  background: linear-gradient(135deg, #fefce8, #fef9c3);
  border-bottom-color: #fde68a;
  color: #92400e;
}
.detail-image-body {
  position: relative;
  display: flex; align-items: center; justify-content: center;
  min-height: 200px; max-height: 360px;
  padding: 12px;
  cursor: pointer;
  transition: background 0.15s ease;
  overflow: hidden;
}
.detail-image-body:hover { background: #fefce8; }
.detail-preview-img {
  max-width: 100%; max-height: 340px;
  object-fit: contain;
  border-radius: 6px;
  transition: transform 0.2s ease;
}
.detail-image-body:hover .detail-preview-img { transform: scale(1.02); }
.detail-image-hint {
  position: absolute; bottom: 8px; left: 50%; transform: translateX(-50%);
  padding: 3px 10px;
  background: rgba(0,0,0,0.5); color: #fff;
  font-size: 0.7rem; border-radius: 10px;
  opacity: 0; transition: opacity 0.15s ease;
  pointer-events: none;
}
.detail-image-body:hover .detail-image-hint { opacity: 1; }
.detail-image-empty {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 2rem; color: #9ca3af; font-size: 0.8rem;
}

@media (max-width: 768px) {
  .form-row, .detail-grid, .detail-images, .invoice-fields-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; }
  .stats-panel { grid-template-columns: repeat(2, 1fr); }
  .action-buttons { flex-wrap: wrap; }
  .modal-content { width: 96%; max-height: 88vh; border-radius: 14px; }
  .modal-overlay { padding: 12px; }
  .modal-header { padding: 1rem 1.25rem; }
  .modal-body { padding: 1rem 1.25rem; }
  .form-actions { flex-direction: column; }
  .cancel-btn, .submit-btn { width: 100%; min-height: 44px; justify-content: center; }
  .zoom-close-btn { top: 10px; right: 10px; }
  .toast-notification { left: 16px; right: 16px; max-width: none; top: 16px; }
}

@media (max-width: 480px) {
  .page-title { font-size: 1.5rem; }
  .stats-panel { grid-template-columns: 1fr; gap: 8px; }
  .stat-card { padding: 12px; }
  .stat-value { font-size: 18px; }
  .filter-grid { gap: 0.5rem; }
  .filter-group input, .filter-group select { min-height: 44px; font-size: 16px; }
  .filter-actions .apply-btn, .filter-actions .reset-btn { min-height: 44px; flex: 1; }
  .action-buttons { gap: 0.4rem; }
  .action-buttons .action-btn { min-height: 40px; font-size: 12px; flex: 1; min-width: calc(50% - 0.4rem); }
  .detail-item.full-width { grid-column: span 1; }
  .modal-body { padding: 0.85rem 1rem; }
  .modal-header { padding: 0.85rem 1rem; }
  .modal-subtitle { display: none; }
  .detail-section { padding: 1rem; }
  .detail-images { grid-template-columns: 1fr; }
  .image-thumb { width: 70px; height: 70px; }
  .zoomed-image { max-width: 98vw; max-height: 90vh; }
  .section-header-row { flex-wrap: wrap; }
  .upload-area { min-height: 100px; padding: 1rem; }
  .upload-icon-circle { width: 44px; height: 44px; }
  .upload-icon-circle svg { width: 22px; height: 22px; }
  .invoice-thumbnail { max-width: 100%; max-height: 150px; }
  .fixed-preview-box { width: 100%; max-width: 280px; height: 180px; }
  .zoom-controls { bottom: 12px; }
  .zoom-controls button { width: 40px; height: 36px; }
  .ai-error-banner { font-size: 0.8rem; padding: 10px 12px; }
  .form-section { padding: 1rem; }
  .input-shell input, .input-shell select, .input-shell textarea { font-size: 16px; min-height: 44px; }
  .records-toolbar { padding: 0.6rem 0.75rem; }
  .sort-control { width: 100%; }
  .sort-select { min-height: 44px; flex: 1; }
  .sort-order-btn { min-height: 44px; }
  .record-count { font-size: 12px; }
  .btn-view-sm, .btn-edit-sm, .btn-reimburse-sm, .btn-approve-sm, .btn-delete-sm { min-width: 40px; min-height: 40px; font-size: 13px; }
  .header-actions { flex-wrap: wrap; gap: 0.4rem; }
  .header-actions .action-button { min-height: 44px; font-size: 13px; flex: 1; min-width: calc(50% - 0.4rem); }
}
</style>
