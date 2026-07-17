<template>
  <div class="projects-page">
    <div class="page-header">
      <h1 class="page-title">项目管理</h1>
      <button @click="goToCreate" class="create-button">创建比赛</button>
    </div>

    <!-- 已加入的比赛 -->
    <div v-if="joinedEvents.length > 0" class="projects-section">
      <h2 class="section-label joined-label">✅ 已加入的比赛 ({{ joinedEvents.length }})</h2>
      <div class="projects-list">
      <div v-for="event in joinedEvents" :key="event.event_id" class="project-card">
        <div class="project-header">
          <div class="project-title-section">
            <h3 class="project-title">{{ event.event_name }}</h3>
            <span class="project-status" :class="event.status">
              {{ event.status === 'ongoing' ? '进行中' : (event.status === 'finished' ? '已结束' : '已归档') }}
            </span>
          </div>
          <div class="action-buttons">
            <button @click="goToInvoiceManage(event)" class="action-btn invoice-btn">📄 购买记录</button>
            <button @click="toggleEventStatus(event)" class="action-btn end-btn" :class="{ 'restart-btn': event.status === 'finished' }">{{ event.status === 'ongoing' ? '⏹ 结束' : '▶ 重新开启' }}</button>
            <button @click="viewMembers(event)" class="action-btn view-btn">📋 人员管理</button>
            <button v-if="canEditEvent(event)" @click="editEvent(event)" class="edit-button">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              编辑
            </button>
            <button v-if="canEditEvent(event)" @click="confirmDelete(event)" class="delete-button">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              删除
            </button>
          </div>
        </div>

        <div class="project-body">
          <!-- 预算信息面板 -->
          <div class="budget-overview">
            <div class="budget-item total">
              <span class="b-label">总预算</span>
              <span class="b-value">¥ {{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="budget-item spent">
              <span class="b-label">已用金额</span>
              <span class="b-value">¥ {{ formatMoney(event.spent_amount) }}</span>
              <div class="mini-progress">
                <div class="mini-fill spent-fill" :style="{ width: getBudgetUsagePercent(event) + '%' }"></div>
              </div>
            </div>
            <div class="budget-item invoice">
              <span class="b-label">发票总额</span>
              <span class="b-value">¥ {{ formatMoney(event.invoice_total_amount) }}</span>
            </div>
            <div class="budget-item reimbursed">
              <span class="b-label">已报销</span>
              <span class="b-value">¥ {{ formatMoney(event.reimbursed_amount) }}</span>
            </div>
            <div class="budget-item remaining" :class="{ 'low': getRemainingPercent(event) < 20 }">
              <span class="b-label">剩余预算</span>
              <span class="b-value">¥ {{ formatMoney(getRemainingBudget(event)) }}</span>
              <div class="mini-progress">
                <div class="mini-fill" :style="{ width: getRemainingPercent(event) + '%' }"></div>
              </div>
            </div>
            <div class="budget-item count">
              <span class="b-label">记录数</span>
              <span class="b-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span class="info-value">{{ formatDateTime(event.event_start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span class="info-value">{{ formatDateTime(event.event_end_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上传开始</span>
              <span class="info-value">{{ formatDateTime(event.upload_start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">上传结束</span>
              <span class="info-value">{{ formatDateTime(event.upload_end_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">总预算</span>
              <span class="info-value budget">¥{{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已用金额</span>
              <span class="info-value spent">¥{{ formatMoney(event.spent_amount) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已报销</span>
              <span class="info-value">¥{{ formatMoney(event.reimbursed_amount) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">剩余预算</span>
              <span class="info-value remaining">¥{{ formatMoney(event.remaining_budget) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">记录数量</span>
              <span class="info-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>
          <div class="description-section" v-if="event.description">
            <span class="info-label">描述</span>
            <p class="description-text">{{ event.description }}</p>
          </div>
        </div>
      </div>

      </div>
    </div>

    <!-- 未加入的比赛 -->
    <div v-if="notJoinedEvents.length > 0" class="projects-section">
      <h2 class="section-label not-joined-label">🔒 未加入的比赛 ({{ notJoinedEvents.length }})</h2>
      <div class="projects-list">
      <div v-for="event in notJoinedEvents" :key="event.event_id" class="project-card not-joined-project">
        <div class="project-header not-joined-project-header">
          <div class="project-title-section">
            <h3 class="project-title">{{ event.event_name }}</h3>
            <span class="project-status" :class="event.status">
              {{ event.status === 'ongoing' ? '进行中' : (event.status === 'finished' ? '已结束' : '已归档') }}
            </span>
            <span class="not-member-badge">您未加入该比赛</span>
          </div>
          <div class="action-buttons">
            <button @click="$router.push(`/purchases/${event.event_id}`)" class="action-btn preview-btn">👁 预览</button>
          </div>
        </div>

        <div class="project-body">
          <div class="budget-overview">
            <div class="budget-item total">
              <span class="b-label">总预算</span>
              <span class="b-value">¥ {{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="budget-item spent">
              <span class="b-label">已用金额</span>
              <span class="b-value">¥ {{ formatMoney(event.spent_amount) }}</span>
            </div>
            <div class="budget-item remaining">
              <span class="b-label">剩余预算</span>
              <span class="b-value">¥ {{ formatMoney(getRemainingBudget(event)) }}</span>
            </div>
            <div class="budget-item count">
              <span class="b-label">记录数</span>
              <span class="b-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 已结束的比赛（已加入） -->
    <div v-if="joinedFinishedEvents.length > 0" class="projects-section finished-section">
      <h2 class="section-label finished-label">🏁 已结束的比赛 ({{ joinedFinishedEvents.length }})</h2>
      <div class="projects-list">
      <div v-for="event in joinedFinishedEvents" :key="event.event_id" class="project-card finished-project">
        <div class="project-header finished-project-header">
          <div class="project-title-section">
            <h3 class="project-title">{{ event.event_name }}</h3>
            <span class="project-status finished">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              已结束
            </span>
          </div>
          <div class="action-buttons">
            <button @click="goToInvoiceManage(event)" class="action-btn invoice-btn">📄 购买记录</button>
            <button @click="toggleEventStatus(event)" class="action-btn restart-btn">▶ 重新开启</button>
            <button @click="viewMembers(event)" class="action-btn view-btn">📋 人员管理</button>
            <button v-if="canEditEvent(event)" @click="editEvent(event)" class="edit-button">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              编辑
            </button>
            <button v-if="canEditEvent(event)" @click="confirmDelete(event)" class="delete-button">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
              删除
            </button>
          </div>
        </div>

        <div class="project-body">
          <div class="budget-overview">
            <div class="budget-item total">
              <span class="b-label">总预算</span>
              <span class="b-value">¥ {{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="budget-item spent">
              <span class="b-label">已用金额</span>
              <span class="b-value">¥ {{ formatMoney(event.spent_amount) }}</span>
              <div class="mini-progress">
                <div class="mini-fill spent-fill" :style="{ width: getBudgetUsagePercent(event) + '%' }"></div>
              </div>
            </div>
            <div class="budget-item invoice">
              <span class="b-label">发票总额</span>
              <span class="b-value">¥ {{ formatMoney(event.invoice_total_amount) }}</span>
            </div>
            <div class="budget-item reimbursed">
              <span class="b-label">已报销</span>
              <span class="b-value">¥ {{ formatMoney(event.reimbursed_amount) }}</span>
            </div>
            <div class="budget-item remaining">
              <span class="b-label">剩余预算</span>
              <span class="b-value">¥ {{ formatMoney(getRemainingBudget(event)) }}</span>
            </div>
            <div class="budget-item count">
              <span class="b-label">记录数</span>
              <span class="b-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>

          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">开始时间</span>
              <span class="info-value">{{ formatDateTime(event.event_start_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">结束时间</span>
              <span class="info-value">{{ formatDateTime(event.event_end_time) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">总预算</span>
              <span class="info-value budget">¥{{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">已用金额</span>
              <span class="info-value spent">¥{{ formatMoney(event.spent_amount) }}</span>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>

    <!-- 已结束的比赛（未加入） -->
    <div v-if="notJoinedFinishedEvents.length > 0" class="projects-section finished-section">
      <h2 class="section-label finished-not-joined-label">🏁 已结束的比赛 - 未加入 ({{ notJoinedFinishedEvents.length }})</h2>
      <div class="projects-list">
      <div v-for="event in notJoinedFinishedEvents" :key="event.event_id" class="project-card finished-project not-joined-project">
        <div class="project-header finished-project-header not-joined-project-header">
          <div class="project-title-section">
            <h3 class="project-title">{{ event.event_name }}</h3>
            <span class="project-status finished">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
              已结束
            </span>
            <span class="not-member-badge">您未加入该比赛</span>
          </div>
          <div class="action-buttons">
            <button @click="$router.push(`/purchases/${event.event_id}`)" class="action-btn preview-btn">👁 预览</button>
          </div>
        </div>

        <div class="project-body">
          <div class="budget-overview">
            <div class="budget-item total">
              <span class="b-label">总预算</span>
              <span class="b-value">¥ {{ formatMoney(event.total_budget) }}</span>
            </div>
            <div class="budget-item spent">
              <span class="b-label">已用金额</span>
              <span class="b-value">¥ {{ formatMoney(event.spent_amount) }}</span>
            </div>
            <div class="budget-item remaining">
              <span class="b-label">剩余预算</span>
              <span class="b-value">¥ {{ formatMoney(getRemainingBudget(event)) }}</span>
            </div>
            <div class="budget-item count">
              <span class="b-label">记录数</span>
              <span class="b-value">{{ event.voucher_count || 0 }} 条</span>
            </div>
          </div>
        </div>
      </div>
      </div>
    </div>

    <div v-if="events.length === 0" class="empty-state">
        <div class="empty-icon">📭</div>
        <div class="empty-text">暂无比赛数据</div>
        <button @click="goToCreate" class="create-button">创建第一个比赛</button>
      </div>

    <!-- 编辑弹窗 (Warm Editorial Design) -->
    <transition name="editorial-modal">
      <div v-if="showEditModal" class="edit-modal-overlay" @mousedown.self="showEditModal = false">
        <div class="edit-modal">
          <!-- Header -->
          <div class="edit-modal__header">
            <div class="edit-modal__header-content">
              <div class="edit-modal__icon">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
              </div>
              <div>
                <h2 class="edit-modal__title">编辑比赛</h2>
                <p class="edit-modal__subtitle">修改比赛信息与配置</p>
              </div>
            </div>
            <button @click="showEditModal = false" class="edit-modal__close" title="关闭">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <!-- Form -->
          <form @submit.prevent="updateEvent" class="edit-modal__body">
            <!-- Section: Basic Info -->
            <div class="form-section">
              <h3 class="form-section__title">基本信息</h3>
              <div class="form-group">
                <label class="form-label">比赛名称 <span class="required">*</span></label>
                <input v-model="editForm.event_name" type="text" class="form-input" placeholder="请输入比赛名称" required />
              </div>
              <div class="form-group">
                <label class="form-label">比赛描述</label>
                <textarea v-model="editForm.description" class="form-textarea" rows="3" placeholder="请输入比赛描述（选填）"></textarea>
              </div>
            </div>

            <!-- Section: Time Settings -->
            <div class="form-section">
              <h3 class="form-section__title">时间设置</h3>
              <div class="form-grid">
                <div class="form-group">
                  <label class="form-label">比赛开始 <span class="required">*</span></label>
                  <input v-model="editForm.event_start_time" type="datetime-local" class="form-input" required />
                </div>
                <div class="form-group">
                  <label class="form-label">比赛结束 <span class="required">*</span></label>
                  <input v-model="editForm.event_end_time" type="datetime-local" class="form-input" required />
                </div>
                <div class="form-group">
                  <label class="form-label">上传开始</label>
                  <input v-model="editForm.upload_start_time" type="datetime-local" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">上传结束</label>
                  <input v-model="editForm.upload_end_time" type="datetime-local" class="form-input" />
                </div>
              </div>
              <div class="quick-set-row">
                <button type="button" @click="syncEditUploadTimes" class="quick-set-button" :disabled="!editForm.event_start_time || !editForm.event_end_time">
                  与比赛时间同步
                </button>
              </div>
            </div>

            <!-- Section: Budget & Leader -->
            <div class="form-section">
              <h3 class="form-section__title">预算与负责人</h3>
              <div class="form-grid">
                <div class="form-group">
                  <label class="form-label">总预算（元）</label>
                  <input v-model.number="editForm.total_budget" type="number" step="0.01" min="0" class="form-input" placeholder="0.00" />
                </div>
                <div class="form-group">
                  <label class="form-label">负责人</label>
                  <div class="leader-autocomplete">
                    <input
                      v-model="leaderSearch"
                      type="text"
                      class="form-input"
                      placeholder="搜索负责人姓名..."
                      @focus="showLeaderDropdown = true"
                    />
                    <transition name="dropdown-slide">
                      <div v-if="showLeaderDropdown && filteredUsers.length > 0" class="leader-dropdown">
                        <div
                          v-for="user in filteredUsers"
                          :key="user.user_id"
                          class="leader-dropdown__item"
                          @click="selectLeader(user)"
                        >
                          <div class="leader-dropdown__avatar">{{ (user.real_name || '?').charAt(0) }}</div>
                          <div class="leader-dropdown__info">
                            <span class="leader-dropdown__name">{{ user.real_name }}</span>
                            <span class="leader-dropdown__role">{{ getUserTypeText(user.user_type) }}</span>
                          </div>
                        </div>
                      </div>
                    </transition>
                  </div>
                </div>
              </div>
            </div>

            <!-- Footer -->
            <div class="edit-modal__footer">
              <button type="button" @click="showEditModal = false" class="btn-edit-cancel">取消</button>
              <button type="submit" class="btn-edit-save" :disabled="updating">
                <svg v-if="updating" class="btn-spin" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
                <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
                {{ updating ? '保存中...' : '保存修改' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </transition>

    <!-- 删除确认弹窗 (Dramatic Dark Theme) -->
    <transition name="delete-modal">
      <div v-if="showDeleteModal" class="delete-modal-overlay" @mousedown.self="showDeleteModal = false">
        <div class="delete-modal">
          <!-- Danger Header -->
          <div class="delete-modal__header">
            <div class="delete-modal__danger-indicator">
              <div class="delete-modal__danger-ring delete-modal__danger-ring--1"></div>
              <div class="delete-modal__danger-ring delete-modal__danger-ring--2"></div>
              <div class="delete-modal__danger-ring delete-modal__danger-ring--3"></div>
              <svg class="delete-modal__danger-icon" viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
            </div>
            <button @click="showDeleteModal = false; confirmName = ''" class="delete-modal__close" title="关闭">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <!-- Content -->
          <div class="delete-modal__content">
            <h2 class="delete-modal__title">确认删除项目</h2>
            <p class="delete-modal__desc">此操作不可撤销，删除后所有相关数据将永久移除。</p>

            <div class="delete-modal__project-info">
              <div class="delete-modal__project-icon">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              </div>
              <span class="delete-modal__project-name">{{ deletingEvent?.event_name }}</span>
            </div>

            <!-- Confirmation Input -->
            <div class="delete-modal__verify">
              <label class="delete-modal__verify-label">请输入项目名称以确认删除</label>
              <input
                v-model="confirmName"
                type="text"
                class="delete-modal__verify-input"
                :placeholder="deletingEvent?.event_name"
                autocomplete="off"
              />
            </div>

            <!-- Warning -->
            <div class="delete-modal__warning-box">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span>删除后，该项目下的所有采购记录、发票数据和成员信息将一并删除。</span>
            </div>
          </div>

          <!-- Actions -->
          <div class="delete-modal__actions">
            <button type="button" @click="showDeleteModal = false; confirmName = ''" class="btn-delete-cancel">取消</button>
            <button
              type="button"
              @click="deleteEvent"
              class="btn-delete-confirm"
              :disabled="deleting || confirmName !== deletingEvent?.event_name"
            >
              <svg v-if="deleting" class="btn-spin" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
              {{ deleting ? '删除中...' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useEventStore } from '~/stores/eventStore'
import { useUserSearch } from '~/composables/useUserSearch'

definePageMeta({
  layout: 'default'
})

const { $api } = useNuxtApp()
const { getUploadUrl } = useUploadUrl()
const eventStore = useEventStore()

// Events from the unified store (reactive)
const currentUser = ref(null)
const events = ref([])

const showEditModal = ref(false)
const showDeleteModal = ref(false)
const confirmName = ref('')
const updating = ref(false)
const deleting = ref(false)
const editingEventId = ref(null)
const deletingEvent = ref(null)

const editForm = ref({
  event_name: '',
  description: '',
  event_start_time: '',
  event_end_time: '',
  upload_start_time: '',
  upload_end_time: '',
  total_budget: 0,
  leader_id: null
})

const { searchText: leaderSearch, results: filteredUsers } = useUserSearch()
const showLeaderDropdown = ref(false)

onMounted(async () => {
  const token = localStorage.getItem('token')

  if (!token) {
    navigateTo('/login')
    return
  }

  const userStr = localStorage.getItem('user')
  currentUser.value = userStr ? JSON.parse(userStr) : null

  await eventStore.ensureLoaded()
  syncFromStore()
})

const joinedEvents = computed(() => events.value.filter(e => isEventMember(e) && e.status === 'ongoing'))
const notJoinedEvents = computed(() => events.value.filter(e => !isEventMember(e) && e.status === 'ongoing'))
const joinedFinishedEvents = computed(() => events.value.filter(e => isEventMember(e) && e.status === 'finished'))
const notJoinedFinishedEvents = computed(() => events.value.filter(e => !isEventMember(e) && e.status === 'finished'))

const canEditEvent = (event) => {
  if (!currentUser.value) return false
  const userType = currentUser.value.user_type
  if (['admin', 'teacher', 'student_admin'].includes(userType)) return true
  if (event.creator_id === currentUser.value.user_id) return true
  return false
}

const isEventMember = (event) => {
  if (!currentUser.value) return false
  const userType = currentUser.value.user_type
  // admin/teacher/student_admin can always operate
  if (['admin', 'teacher', 'student_admin'].includes(userType)) return true
  // Use the is_member flag from the API response
  if (event.is_member !== undefined) return event.is_member
  // Fallback: check if user is creator
  if (event.creator_id === currentUser.value.user_id) return true
  return false
}

// Keep local events in sync with store (reactive binding)
const syncFromStore = () => {
  events.value = [...eventStore.events]
}

// Watch store data version to sync when data changes
watch(() => eventStore.dataVersion, () => {
  syncFromStore()
})

const goToCreate = () => {
  navigateTo('/events/create')
}

const editEvent = (event) => {
  editingEventId.value = event.event_id
  // 直接从列表数据中获取负责人姓名，无需额外的API请求
  console.log('[编辑项目] leader_id:', event.leader_id, 'leader_name:', event.leader_name)
  if (event.leader_name) {
    leaderSearch.value = event.leader_name
    console.log('[编辑项目] 已填充负责人:', event.leader_name)
  } else {
    leaderSearch.value = ''
    console.log('[编辑项目] 无负责人信息')
  }
  editForm.value = {
    event_name: event.event_name,
    description: event.description || '',
    event_start_time: formatDateTimeLocal(event.event_start_time),
    event_end_time: formatDateTimeLocal(event.event_end_time),
    upload_start_time: formatDateTimeLocal(event.upload_start_time),
    upload_end_time: formatDateTimeLocal(event.upload_end_time),
    total_budget: parseFloat(event.total_budget),
    leader_id: event.leader_id || null
  }
  showEditModal.value = true
}

const formatDateTimeLocal = (dateStr) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toISOString().slice(0, 16)
}

const updateEvent = async () => {
  updating.value = true
  try {
    const token = localStorage.getItem('token')
    const response = await $api.put(`/events/${editingEventId.value}`, editForm.value, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showEditModal.value = false
      const eventId = editingEventId.value
      if (eventId) {
        await eventStore.invalidateAndRefresh({ eventId })
      }
      syncFromStore()
    }
  } catch (error) {
    console.error('更新比赛失败:', error.message)
    alert('更新比赛失败，请稍后重试')
  } finally {
    updating.value = false
  }
}


const selectLeader = (user) => {
  editForm.value.leader_id = user.user_id
  leaderSearch.value = user.real_name
  showLeaderDropdown.value = false
}

const syncEditUploadTimes = () => {
  editForm.value.upload_start_time = editForm.value.event_start_time
  editForm.value.upload_end_time = editForm.value.event_end_time
}

const formatDateTime = (dateStr) => {
  if (!dateStr) return '未设置'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const confirmDelete = (event) => {
  deletingEvent.value = event
  confirmName.value = ''
  showDeleteModal.value = true
}

const goToInvoiceManage = (event) => {
  navigateTo(`/purchases/${event.event_id}`)
}

const toggleEventStatus = async (event) => {
  // 如果项目进行中，询问是否结束；如果已结束，询问是否重新开启
  // 注意: 数据库枚举值为 'ongoing' 和 'finished'
  const newStatus = event.status === 'ongoing' ? 'finished' : 'ongoing'
  const confirmMsg = event.status === 'ongoing'
    ? `确定要将比赛 "${event.event_name}" 结束吗？结束后将无法添加新的购买记录。`
    : `确定要将比赛 "${event.event_name}" 重新开启吗？`

  if (!confirm(confirmMsg)) return

  try {
    const token = localStorage.getItem('token')
    const eventId = Number(event.event_id)
    console.log(`[结束项目] event_id=${eventId}, newStatus=${newStatus}`)
    const response = await $api.put(`/events/${eventId}`, { status: newStatus }, {
      headers: { Authorization: `Bearer ${token}` }
    })
    console.log(`[结束项目] 响应:`, response.data)

    if (response.data.code === 200) {
      const successMsg = newStatus === 'finished' ? '比赛已结束' : '比赛已重新开启'
      alert(successMsg)
      await eventStore.invalidateAndRefresh({ eventId })
      syncFromStore()
    } else {
      alert(response.data.message || '操作失败，请稍后重试')
    }
  } catch (error) {
    console.error('操作失败:', error)
    const errorMsg = error.response?.data?.message || error.message || '操作失败，请稍后重试'
    alert(`操作失败: ${errorMsg}`)
  }
}

const viewMembers = (event) => {
  navigateTo(`/events/${event.event_id}/members`)
}

const getUserTypeText = (type) => {
  const map = { admin: '管理员', teacher: '老师', student_admin: '学生管理员', student: '学生' }
  return map[type] || type
}

const formatMoney = (value) => {
  if (!value && value !== 0) return '0.00'
  return Number(value).toFixed(2)
}

const getRemainingBudget = (event) => {
  if (!event) return 0
  return Number(event.total_budget || 0) - Number(event.spent_amount || 0)
}

const getRemainingPercent = (event) => {
  const total = Number(event.total_budget || 0)
  if (total === 0) return 100
  return Math.max(0, Math.min(100, (getRemainingBudget(event) / total) * 100))
}

const getBudgetUsagePercent = (event) => {
  const budget = Number(event.total_budget || 0)
  const spent = Number(event.spent_amount || 0)
  if (budget <= 0) return 0
  return Math.min(100, (spent / budget) * 100)
}

const deleteEvent = async () => {
  if (!deletingEvent.value) return

  deleting.value = true

  try {
    const token = localStorage.getItem('token')
    const response = await $api.delete(`/events/${deletingEvent.value.event_id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })

    if (response.data.code === 200) {
      showDeleteModal.value = false
      confirmName.value = ''
      const deletedId = deletingEvent.value?.event_id
      deletingEvent.value = null
      await eventStore.invalidateAndRefresh({ eventId: deletedId })
      syncFromStore()
      alert('项目删除成功')
    } else {
      alert(response.data.message || '删除失败，请稍后重试')
    }
  } catch (error) {
    console.error('删除项目失败:', error.message)
    const message = error.response?.data?.message || '删除失败，请稍后重试'
    alert(message)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped>
.projects-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.create-button {
  padding: 0.8rem 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 5px;
  font-weight: 500;
  cursor: pointer;
  transition: opacity 0.3s ease;
}

.create-button:hover {
  opacity: 0.9;
}

.projects-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.project-card {
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.project-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.project-title-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.project-title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 600;
}

.project-status {
  padding: 0.3rem 0.8rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.2);
}

.project-status.ongoing {
  background: #27ae60;
}

.project-status.finished {
  background: #95a5a6;
}

.project-status.archived {
  background: #7f8c8d;
}

.not-member-badge {
  padding: 0.2rem 0.6rem;
  background: #fef2f2;
  color: #dc2626;
  border: 1px solid #fecaca;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}
.preview-btn {
  background: rgba(255,255,255,0.15) !important;
  border: 1px solid rgba(255,255,255,0.25) !important;
  color: white !important;
}

/* Section labels */
.projects-section {
  margin-bottom: 2rem;
}
.finished-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px dashed #d1d5db;
}
.section-label {
  font-size: 1.1rem;
  font-weight: 600;
  margin-bottom: 0.8rem;
  padding-bottom: 0.4rem;
  border-bottom: 2px solid #e2e8f0;
}
.section-label.joined-label { color: #16a34a; border-bottom-color: #bbf7d0; }
.section-label.not-joined-label { color: #94a3b8; border-bottom-color: #e2e8f0; }
.section-label.finished-label { color: #6b7280; border-bottom-color: #d1d5db; display: flex; align-items: center; gap: 8px; }
.section-label.finished-not-joined-label { color: #9ca3af; border-bottom-color: #e5e7eb; }

/* Not-joined project card */
.project-card.not-joined-project { opacity: 0.7; }
.project-card.not-joined-project:hover { opacity: 0.85; }
.not-joined-project-header { background: linear-gradient(135deg, #94a3b8 0%, #64748b 100%) !important; }

/* Finished project card */
.project-card.finished-project {
  opacity: 0.85;
  border: 1px solid #e5e7eb;
}
.project-card.finished-project:hover {
  opacity: 1;
  border-color: #d1d5db;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}
.finished-project-header {
  background: linear-gradient(135deg, #9ca3af 0%, #6b7280 100%) !important;
}
.project-status.finished {
  background: #6b7280;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.edit-button {
  padding: 0.45rem 0.9rem;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
  backdrop-filter: blur(4px);
}

.edit-button:hover {
  background: rgba(255, 255, 255, 0.28);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-1px);
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.delete-button {
  padding: 0.45rem 0.9rem;
  background: rgba(220, 53, 69, 0.75);
  border: 1px solid rgba(220, 53, 69, 0.85);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  font-weight: 500;
}

.delete-button:hover {
  background: rgba(220, 53, 69, 1);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(220, 53, 69, 0.35);
}

.project-body {
  padding: 1.5rem;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.info-label {
  font-size: 0.85rem;
  color: #7f8c8d;
}

.info-value {
  font-size: 0.95rem;
  color: #2c3e50;
  font-weight: 500;
}

.info-value.budget {
  color: #27ae60;
}

.info-value.spent {
  color: #e74c3c;
}

.info-value.remaining {
  color: #3498db;
}

.description-section {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.description-text {
  margin: 0.5rem 0 0 0;
  color: #2c3e50;
  line-height: 1.6;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 1rem;
}

.empty-text {
  color: #7f8c8d;
  font-size: 1.1rem;
  margin-bottom: 1.5rem;
}

/* ===== EDIT MODAL (Warm Editorial) ===== */
.edit-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(30, 20, 15, 0.5);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.edit-modal {
  background: #faf8f5;
  border-radius: 20px;
  width: 100%;
  max-width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 30px 80px rgba(30, 20, 15, 0.25), 0 0 0 1px rgba(139, 90, 43, 0.08);
}

.edit-modal__header {
  padding: 1.5rem 1.75rem;
  background: linear-gradient(135deg, #f5ebe0 0%, #eddcd2 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(139, 90, 43, 0.1);
}

.edit-modal__header-content {
  display: flex;
  align-items: center;
  gap: 14px;
}

.edit-modal__icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #c96b4f, #a0522d);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(180, 90, 40, 0.3);
}

.edit-modal__title {
  margin: 0;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', Georgia, serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #3d2c1e;
  letter-spacing: -0.01em;
}

.edit-modal__subtitle {
  margin: 3px 0 0;
  font-size: 0.8rem;
  color: #9c8a7a;
}

.edit-modal__close {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: none;
  background: rgba(255, 255, 255, 0.6);
  color: #9c8a7a;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.edit-modal__close:hover {
  background: #fee2e2;
  color: #dc3545;
}

.edit-modal__body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 1.75rem;
}

.form-section {
  margin-bottom: 1.5rem;
}

.form-section:last-of-type {
  margin-bottom: 1rem;
}

.form-section__title {
  margin: 0 0 1rem;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', Georgia, serif;
  font-size: 0.88rem;
  font-weight: 600;
  color: #7c6354;
  letter-spacing: 0.03em;
  padding-bottom: 0.5rem;
  border-bottom: 1.5px solid #e8ddd2;
}

.form-group {
  margin-bottom: 1rem;
}

.form-label {
  display: block;
  margin-bottom: 0.45rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #5a4a3e;
}

.form-label .required {
  color: #c96b4f;
  margin-left: 2px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-input {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border: 1.5px solid #ddd2c4;
  border-radius: 10px;
  font-size: 0.92rem;
  color: #3d2c1e;
  background: #fff;
  transition: all 0.25s ease;
  box-sizing: border-box;
  outline: none;
  font-family: inherit;
}

.form-input:hover {
  border-color: #c9b8a8;
}

.form-input:focus {
  border-color: #c96b4f;
  box-shadow: 0 0 0 3px rgba(201, 107, 79, 0.1);
  background: #fffdf9;
}

.form-input::placeholder {
  color: #c4b5a5;
}

.form-textarea {
  width: 100%;
  padding: 0.7rem 0.9rem;
  border: 1.5px solid #ddd2c4;
  border-radius: 10px;
  font-size: 0.92rem;
  color: #3d2c1e;
  background: #fff;
  transition: all 0.25s ease;
  box-sizing: border-box;
  outline: none;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
}

.form-textarea:hover {
  border-color: #c9b8a8;
}

.form-textarea:focus {
  border-color: #c96b4f;
  box-shadow: 0 0 0 3px rgba(201, 107, 79, 0.1);
  background: #fffdf9;
}

.form-textarea::placeholder {
  color: #c4b5a5;
}

/* Leader Autocomplete */
.leader-autocomplete {
  position: relative;
}

.leader-dropdown {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1.5px solid #e8ddd2;
  border-radius: 12px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 20;
  box-shadow: 0 10px 30px rgba(60, 40, 20, 0.12);
}

.leader-dropdown__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f5ebe0;
}

.leader-dropdown__item:last-child {
  border-bottom: none;
}

.leader-dropdown__item:hover {
  background: #faf5ef;
}

.leader-dropdown__avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c96b4f, #a0522d);
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.leader-dropdown__info {
  flex: 1;
  min-width: 0;
}

.leader-dropdown__name {
  display: block;
  font-size: 0.88rem;
  font-weight: 600;
  color: #3d2c1e;
}

.leader-dropdown__role {
  display: block;
  font-size: 0.75rem;
  color: #9c8a7a;
  margin-top: 2px;
}

/* Toggle Switch */
.toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.1rem;
  background: #fff;
  border: 1.5px solid #e8ddd2;
  border-radius: 12px;
}

.toggle-row__info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggle-row__label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #3d2c1e;
}

.toggle-row__hint {
  font-size: 0.78rem;
  color: #9c8a7a;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 48px;
  height: 26px;
  flex-shrink: 0;
  cursor: pointer;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-switch__track {
  position: absolute;
  inset: 0;
  background: #d4c8bb;
  border-radius: 13px;
  transition: background 0.3s ease;
}

.toggle-switch__thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  background: #fff;
  border-radius: 50%;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

.toggle-switch input:checked + .toggle-switch__track {
  background: linear-gradient(135deg, #c96b4f, #a0522d);
}

.toggle-switch input:checked + .toggle-switch__track .toggle-switch__thumb {
  transform: translateX(22px);
}

/* Edit Modal Footer */
.edit-modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 1.25rem 1.75rem;
  border-top: 1.5px solid #e8ddd2;
  background: #f5ebe0;
}

.btn-edit-cancel {
  padding: 0.7rem 1.4rem;
  border: 1.5px solid #d4c8bb;
  border-radius: 10px;
  background: #fff;
  color: #5a4a3e;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-edit-cancel:hover {
  background: #f5ebe0;
  border-color: #c9b8a8;
}

.btn-edit-save {
  padding: 0.7rem 1.6rem;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #c96b4f, #a0522d);
  color: #fff;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  box-shadow: 0 4px 14px rgba(180, 90, 40, 0.3);
  font-family: inherit;
}

.btn-edit-save:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(180, 90, 40, 0.4);
}

.btn-edit-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.quick-set-row {
  display: flex;
  justify-content: flex-end;
  margin-top: -0.25rem;
  margin-bottom: 0.5rem;
}

.quick-set-button {
  padding: 0.35rem 0.9rem;
  background: transparent;
  border: 1px dashed #c96b4f;
  border-radius: 8px;
  color: #c96b4f;
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.quick-set-button:hover:not(:disabled) {
  background: #c96b4f;
  color: white;
  border-style: solid;
}

.quick-set-button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-spin {
  animation: btn-spin 1s linear infinite;
}

@keyframes btn-spin {
  to { transform: rotate(360deg); }
}

/* Edit Modal Transition */
.editorial-modal-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.editorial-modal-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.editorial-modal-enter-from,
.editorial-modal-leave-to {
  opacity: 0;
}
.editorial-modal-enter-from .edit-modal {
  transform: translateY(20px) scale(0.97);
  opacity: 0;
}
.editorial-modal-leave-to .edit-modal {
  transform: scale(0.98);
  opacity: 0;
}

/* Dropdown Slide Transition */
.dropdown-slide-enter-active {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}
.dropdown-slide-leave-active {
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.dropdown-slide-enter-from,
.dropdown-slide-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ===== DELETE MODAL (Dramatic Dark) ===== */
.delete-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 8, 6, 0.6);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.delete-modal {
  background: #1a1614;
  border-radius: 22px;
  width: 100%;
  max-width: 440px;
  overflow: hidden;
  box-shadow: 0 40px 100px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.06), inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.delete-modal__header {
  padding: 1.75rem 1.5rem 1rem;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.delete-modal__danger-indicator {
  position: relative;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.delete-modal__danger-icon {
  color: #ef4444;
  z-index: 1;
  filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.4));
}

.delete-modal__danger-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid rgba(239, 68, 68, 0.3);
  animation: danger-pulse 2s ease-out infinite;
}

.delete-modal__danger-ring--1 {
  animation-delay: 0s;
}

.delete-modal__danger-ring--2 {
  animation-delay: 0.5s;
}

.delete-modal__danger-ring--3 {
  animation-delay: 1s;
}

@keyframes danger-pulse {
  0% {
    transform: scale(0.6);
    opacity: 1;
  }
  100% {
    transform: scale(1.3);
    opacity: 0;
  }
}

.delete-modal__close {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.delete-modal__close:hover {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.3);
  color: #ef4444;
}

.delete-modal__content {
  padding: 0 1.75rem 1.5rem;
}

.delete-modal__title {
  margin: 0 0 0.5rem;
  font-family: 'Noto Serif SC', 'Source Han Serif SC', Georgia, serif;
  font-size: 1.25rem;
  font-weight: 700;
  color: #f5f0ec;
  letter-spacing: -0.01em;
}

.delete-modal__desc {
  margin: 0 0 1.25rem;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.45);
  line-height: 1.5;
}

.delete-modal__project-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0.85rem 1rem;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  margin-bottom: 1.25rem;
}

.delete-modal__project-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.delete-modal__project-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #f5f0ec;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.delete-modal__verify {
  margin-bottom: 1rem;
}

.delete-modal__verify-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.55);
}

.delete-modal__verify-input {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: #f5f0ec;
  font-size: 0.92rem;
  outline: none;
  transition: all 0.25s;
  box-sizing: border-box;
  font-family: inherit;
}

.delete-modal__verify-input:hover {
  border-color: rgba(255, 255, 255, 0.18);
}

.delete-modal__verify-input:focus {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12);
  background: rgba(255, 255, 255, 0.06);
}

.delete-modal__verify-input::placeholder {
  color: rgba(255, 255, 255, 0.2);
}

.delete-modal__warning-box {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 0.8rem 1rem;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.12);
  border-radius: 10px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 0.78rem;
  line-height: 1.5;
}

.delete-modal__warning-box svg {
  flex-shrink: 0;
  color: #ef4444;
  margin-top: 1px;
}

/* Delete Modal Actions */
.delete-modal__actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 1.25rem 1.75rem;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
}

.btn-delete-cancel {
  padding: 0.7rem 1.4rem;
  border: 1.5px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}

.btn-delete-cancel:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.85);
}

.btn-delete-confirm {
  padding: 0.7rem 1.6rem;
  border: none;
  border-radius: 10px;
  background: linear-gradient(135deg, #dc2626, #b91c1c);
  color: #fff;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  box-shadow: 0 4px 14px rgba(220, 38, 38, 0.35);
  font-family: inherit;
}

.btn-delete-confirm:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(220, 38, 38, 0.5);
}

.btn-delete-confirm:disabled {
  opacity: 0.35;
  cursor: not-allowed;
  box-shadow: none;
}

/* Delete Modal Transition */
.delete-modal-enter-active {
  transition: all 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
.delete-modal-leave-active {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.delete-modal-enter-from,
.delete-modal-leave-to {
  opacity: 0;
}
.delete-modal-enter-from .delete-modal {
  transform: translateY(16px) scale(0.97);
  opacity: 0;
}
.delete-modal-leave-to .delete-modal {
  transform: scale(0.96);
  opacity: 0;
}

@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }

  .info-grid {
    grid-template-columns: 1fr 1fr;
  }

  .project-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .project-title-section {
    flex-wrap: wrap;
  }

  .action-buttons {
    flex-wrap: wrap;
    width: 100%;
  }

  .action-btn {
    flex: 1;
    min-width: calc(50% - 0.5rem);
    min-height: 40px;
    justify-content: center;
    font-size: 13px;
    padding: 0.5rem 0.6rem;
  }

  .edit-button, .delete-button {
    min-height: 40px;
    padding: 0.45rem 0.9rem;
  }

  .budget-overview {
    grid-template-columns: repeat(2, 1fr);
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .create-button {
    width: 100%;
    min-height: 48px;
    text-align: center;
    justify-content: center;
  }

  .edit-modal {
    max-width: 100%;
    max-height: 85vh;
  }

  .edit-modal__header {
    padding: 1.25rem 1.25rem;
  }

  .edit-modal__body {
    padding: 1.25rem;
  }

  .edit-modal__footer {
    padding: 1rem 1.25rem;
  }

  .delete-modal {
    max-width: 100%;
  }

  .member-modal {
    width: 95%;
    max-height: 85vh;
  }
}

@media (max-width: 480px) {
  .page-title { font-size: 1.5rem; }
  .project-title { font-size: 1.1rem; }
  .project-status { font-size: 0.75rem; padding: 0.2rem 0.6rem; }
  .info-grid { grid-template-columns: 1fr; }
  .budget-overview { grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px; }
  .budget-item { padding: 8px 6px; }
  .b-value { font-size: 14px; }
  .action-btn { min-width: 100%; }
  .not-member-badge { font-size: 0.7rem; padding: 0.15rem 0.45rem; }
  .project-title-section { flex-wrap: wrap; gap: 6px; }

  .edit-modal__body { padding: 1rem; }
  .edit-modal__header { padding: 1rem; }
  .edit-modal__footer { flex-direction: column; }
  .btn-edit-cancel, .btn-edit-save { width: 100%; min-height: 44px; justify-content: center; }

  .delete-modal__content { padding: 0 1.25rem 1.25rem; }
  .delete-modal__actions { flex-direction: column; padding: 1rem 1.25rem; }
  .btn-delete-cancel, .btn-delete-confirm { width: 100%; min-height: 44px; justify-content: center; }

  .member-modal__body { padding: 1rem; }
  .member-modal__footer { flex-direction: column; }
  .member-modal__btn { width: 100%; justify-content: center; min-height: 44px; }
}

/* 操作按钮样式 */
.action-btn {
  padding: 0.4rem 0.8rem;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: white;
}

.invoice-btn { background: #3498db; }
.invoice-btn:hover { background: #2980b9; }

.end-btn { background: #e67e22; }
.end-btn:hover { background: #d35400; }
.restart-btn { background: #3498db; }
.restart-btn:hover { background: #2980b9; }

.view-btn { background: #1abc9c; }
.view-btn:hover { background: #16a085; }

/* 预算概览面板 */
.budget-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 1.2rem;
  padding: 14px;
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 10px;
  border: 1px solid #dee2e6;
}

.budget-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px;
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.b-label {
  font-size: 11px;
  color: #7f8c8d;
  margin-bottom: 4px;
}

.b-value {
  font-size: 16px;
  font-weight: 700;
  color: #2c3e50;
}

.budget-item.total .b-value { color: #3498db; }
.budget-item.spent .b-value { color: #e74c3c; }
.budget-item.invoice .b-value { color: #f39c12; }
.budget-item.reimbursed .b-value { color: #27ae60; }
.budget-item.remaining .b-value { color: #9b59b6; }
.budget-item.remaining.low .b-value { color: #e74c3c; }
.budget-item.count .b-value { color: #1abc9c; }

.mini-progress {
  width: 100%;
  height: 3px;
  background: #ecf0f1;
  border-radius: 2px;
  margin-top: 5px;
  overflow: hidden;
}

.mini-fill {
  height: 100%;
  background: linear-gradient(90deg, #9b59b6, #8e44ad);
  border-radius: 2px;
  transition: width 0.4s ease;
}

.mini-fill.spent-fill {
  background: linear-gradient(90deg, #e74c3c, #f39c12);
}

/* Checkbox group styles */
.checkbox-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.checkbox-group input[type="checkbox"] {
  width: 18px;
  height: 18px;
  cursor: pointer;
}

.checkbox-group label {
  margin: 0;
  cursor: pointer;
  font-weight: normal;
}
</style>
