<template>
  <div class="avatar-upload">
    <!-- 头像展示圆形 -->
    <div class="avatar-circle" :class="{ 'has-avatar': displayUrl }" @click="triggerFileInput">
      <img
        v-if="displayUrl"
        :src="displayUrl"
        alt="用户头像"
        class="avatar-img"
        @error="onImageError"
      />
      <div v-else class="avatar-placeholder">
        <svg viewBox="0 0 120 120" width="56" height="56" xmlns="http://www.w3.org/2000/svg">
          <circle cx="60" cy="48" r="28" fill="currentColor" opacity="0.55"/>
          <ellipse cx="60" cy="112" rx="52" ry="36" fill="currentColor" opacity="0.35"/>
        </svg>
      </div>
      <!-- 悬浮遮罩 -->
      <div class="avatar-overlay">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
        <span>更换头像</span>
      </div>
    </div>

    <!-- 操作按钮行 -->
    <div class="avatar-actions">
      <button type="button" class="action-link" @click="triggerFileInput">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>
        更换头像
      </button>
      <button v-if="displayUrl" type="button" class="action-link danger" :disabled="deleting" @click="handleDelete">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        {{ deleting ? '删除中...' : '删除头像' }}
      </button>
    </div>

    <!-- 格式提示 -->
    <p class="avatar-hint">支持 JPG、PNG、WEBP，最大 5MB</p>

    <!-- 状态提示 -->
    <transition name="toast-fade">
      <div v-if="statusMessage" class="status-toast" :class="statusType">
        <span>{{ statusMessage }}</span>
      </div>
    </transition>

    <!-- 隐藏的文件选择框 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="file-input-hidden"
      @change="onFileSelect"
    />

    <!-- ========== 裁剪模态框（Teleport 到 body 避免层级和溢出问题） ========== -->
    <Teleport to="body">
      <transition name="modal-fade">
        <div v-if="showCropper" class="crop-modal-overlay" @click.self="cancelCrop">
          <div class="crop-modal">
            <div class="crop-modal-header">
              <h3>裁剪头像</h3>
              <button class="crop-close-btn" @click="cancelCrop" :disabled="uploading">&times;</button>
            </div>

            <div class="crop-modal-body">
              <div class="crop-container">
                <CropperImage
                  ref="cropperRef"
                  :src="cropSourceUrl"
                  :selection-props="{ aspectRatio: 1, initialCoverage: 0.85, movable: true, resizable: true }"
                  :image-props="{ rotatable: true, scalable: true, translatable: true }"
                  :canvas-props="{ background: true }"
                  @ready="onCropperReady"
                  @error="onCropperError"
                />
              </div>

              <!-- 工具栏 -->
              <div class="crop-toolbar">
                <div class="toolbar-group">
                  <button type="button" class="tool-btn" title="放大" @click="handleZoomIn">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
                  </button>
                  <button type="button" class="tool-btn" title="缩小" @click="handleZoomOut">
                    <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
                  </button>
                </div>
              </div>
            </div>

            <div class="crop-modal-footer">
              <button type="button" class="crop-btn cancel" @click="cancelCrop" :disabled="uploading">取消</button>
              <button type="button" class="crop-btn confirm" :disabled="!cropperReady || uploading" @click="confirmCrop">
                <span v-if="uploading" class="btn-spinner"></span>
                {{ uploading ? '上传中...' : '确认保存' }}
              </button>
            </div>
          </div>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { CropperImage } from '@xcvzmoon/vue-cropperjs'

const MAX_FILE_SIZE = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const props = defineProps({
  currentAvatarUrl: { type: String, default: '' }
})

const emit = defineEmits(['avatar-updated'])

const { $api } = useNuxtApp()

const fileInputRef = ref(null)
const cropperRef = ref(null)
const displayUrl = ref(props.currentAvatarUrl || '')
const showCropper = ref(false)
const cropSourceUrl = ref('')
const cropperReady = ref(false)
const uploading = ref(false)
const deleting = ref(false)
const statusMessage = ref('')
const statusType = ref('info')
let statusTimer = null

// 同步外部头像 URL 变化
watch(() => props.currentAvatarUrl, (url) => {
  displayUrl.value = url || ''
})

function showStatus(msg, type = 'info') {
  statusMessage.value = msg
  statusType.value = type
  if (statusTimer) clearTimeout(statusTimer)
  if (type !== 'error') {
    statusTimer = setTimeout(() => { statusMessage.value = '' }, 3500)
  }
}

function clearStatus() {
  statusMessage.value = ''
  if (statusTimer) clearTimeout(statusTimer)
}

function triggerFileInput() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

// ============ 文件选择 & 校验 ============
function onFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (!ALLOWED_TYPES.includes(file.type)) {
    showStatus('仅支持 JPG、PNG、WEBP 格式', 'error')
    event.target.value = ''
    return
  }
  if (file.size > MAX_FILE_SIZE) {
    showStatus('文件大小不能超过 5MB', 'error')
    event.target.value = ''
    return
  }

  cropSourceUrl.value = URL.createObjectURL(file)
  showCropper.value = true
  cropperReady.value = false
  clearStatus()
  event.target.value = ''
}

// ============ 裁剪相关 ============
function onCropperReady() {
  cropperReady.value = true
}

function onCropperError(err) {
  showStatus(`图片加载失败: ${err.message || '请重试'}`, 'error')
}

function handleZoomIn() {
  cropperRef.value?.zoomImage(0.1)
}

function handleZoomOut() {
  cropperRef.value?.zoomImage(-0.1)
}

function handleRotate() {
  cropperRef.value?.rotateImage(90)
}

function handleReset() {
  cropperRef.value?.resetImageTransform()
  cropperRef.value?.resetSelection()
}

function cancelCrop() {
  if (uploading.value) return
  if (cropSourceUrl.value) {
    URL.revokeObjectURL(cropSourceUrl.value)
  }
  showCropper.value = false
  cropSourceUrl.value = ''
  cropperReady.value = false
}

async function confirmCrop() {
  const cropper = cropperRef.value
  if (!cropper || !cropperReady.value) return

  uploading.value = true
  showStatus('正在上传头像...', 'info')

  try {
    const canvas = await cropper.toCanvas()
    if (!canvas) {
      showStatus('裁剪失败，请重试', 'error')
      return
    }

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((b) => b ? resolve(b) : reject(new Error('转换失败')), 'image/png')
    })

    const formData = new FormData()
    formData.append('file', blob, 'avatar.png')

    const res = await $api.post('/auth/avatar/upload', formData)

    if (res.data?.code === 200 && res.data?.data?.avatar_url) {
      const newUrl = res.data.data.avatar_url
      displayUrl.value = newUrl
      emit('avatar-updated', newUrl)
      showStatus('头像更新成功', 'success')
      cancelCrop()
    } else {
      showStatus(res.data?.message || '上传失败，请重试', 'error')
    }
  } catch (err) {
    showStatus(err.response?.data?.message || '上传失败，请检查网络连接', 'error')
  } finally {
    uploading.value = false
  }
}

// ============ 删除头像 ============
async function handleDelete() {
  if (deleting.value) return
  deleting.value = true
  showStatus('正在删除头像...', 'info')

  try {
    const res = await $api.delete('/auth/avatar')
    if (res.data?.code === 200) {
      displayUrl.value = ''
      emit('avatar-updated', '')
      showStatus('头像已删除', 'success')
    } else {
      showStatus(res.data?.message || '删除失败', 'error')
    }
  } catch (err) {
    showStatus(err.response?.data?.message || '删除失败', 'error')
  } finally {
    deleting.value = false
  }
}

function onImageError() {
  // 图片加载失败时回退显示占位符
  displayUrl.value = ''
}

onBeforeUnmount(() => {
  if (cropSourceUrl.value) URL.revokeObjectURL(cropSourceUrl.value)
  if (statusTimer) clearTimeout(statusTimer)
})
</script>

<style scoped>
.avatar-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* ---- 头像圆形 ---- */
.avatar-circle {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  background: linear-gradient(135deg, #e8ecf1, #d5dbe3);
  border: 3px solid #e0e4ea;
  transition: border-color .25s, box-shadow .25s, transform .25s;
  flex-shrink: 0;
}
.avatar-circle:hover {
  border-color: #667eea;
  box-shadow: 0 4px 22px rgba(102,126,234,.28);
  transform: scale(1.03);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0aec0;
}

/* ---- 悬浮遮罩 ---- */
.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(102,126,234,.78);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  color: #fff;
  opacity: 0;
  transition: opacity .25s;
}
.avatar-circle:hover .avatar-overlay {
  opacity: 1;
}
.avatar-overlay span {
  font-size: 13px;
  font-weight: 500;
}

/* ---- 操作按钮 ---- */
.avatar-actions {
  display: flex;
  gap: 18px;
  margin-top: 14px;
}
.action-link {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: none;
  border: none;
  color: #667eea;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: 6px;
  transition: background .2s;
}
.action-link:hover:not(:disabled) {
  background: rgba(102,126,234,.08);
}
.action-link.danger {
  color: #e74c3c;
}
.action-link.danger:hover:not(:disabled) {
  background: rgba(231,76,60,.08);
}
.action-link:disabled {
  opacity: .45;
  cursor: not-allowed;
}

.avatar-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: #95a5a6;
}

/* ---- 状态提示 ---- */
.status-toast {
  margin-top: 14px;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  animation: toast-in .3s ease;
}
.status-toast.success {
  background: #d4edda; color: #155724;
}
.status-toast.error {
  background: #f8d7da; color: #721c24;
}
.status-toast.info {
  background: #e8f4fd; color: #0c5460;
}
.toast-fade-enter-active, .toast-fade-leave-active { transition: all .3s ease; }
.toast-fade-enter-from, .toast-fade-leave-to { opacity: 0; transform: translateY(6px); }

@keyframes toast-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* ---- 隐藏 input ---- */
.file-input-hidden {
  position: absolute;
  width: 0; height: 0; opacity: 0; pointer-events: none;
}

/* ========== 裁剪模态框 ========== */
.crop-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0,0,0,.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.crop-modal {
  background: #fff;
  border-radius: 14px;
  width: 520px;
  max-width: 95vw;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 12px 48px rgba(0,0,0,.25);
  overflow: hidden;
}
.crop-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
}
.crop-modal-header h3 {
  margin: 0;
  font-size: 1.05rem;
  color: #2c3e50;
}
.crop-close-btn {
  background: none;
  border: none;
  font-size: 1.6rem;
  color: #999;
  cursor: pointer;
  line-height: 1;
  padding: 0 4px;
}
.crop-close-btn:hover { color: #333; }
.crop-close-btn:disabled { opacity: .4; cursor: not-allowed; }

.crop-modal-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  overflow-y: auto;
  flex: 1;
}

/* 裁剪容器 */
.crop-container {
  width: 100%;
  max-width: 420px;
  background: #f5f5f5;
  border-radius: 10px;
  overflow: hidden;
}
/* cropper 根元素必须拥有确定的尺寸，否则 handle 无法定位 */
.crop-container :deep([data-vue-cropper-root]) {
  min-height: 320px;
  width: 100%;
}
.crop-container :deep(cropper-canvas) {
  display: block;
  width: 100%;
  height: 320px;
  overflow: hidden;
}

/* 工具栏 */
.crop-toolbar {
  display: flex;
  justify-content: center;
}
.toolbar-group {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #f1f3f5;
  border-radius: 10px;
  padding: 6px 12px;
}
.tool-btn {
  width: 38px;
  height: 38px;
  border: none;
  background: #fff;
  border-radius: 8px;
  cursor: pointer;
  color: #555;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s;
  box-shadow: 0 1px 3px rgba(0,0,0,.06);
}
.tool-btn:hover {
  background: #667eea;
  color: #fff;
  box-shadow: 0 2px 8px rgba(102,126,234,.35);
}

.crop-modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #eee;
  justify-content: flex-end;
}
.crop-btn {
  padding: 10px 28px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all .25s;
}
.crop-btn.cancel {
  background: #f0f0f0;
  color: #666;
}
.crop-btn.cancel:hover:not(:disabled) { background: #e2e2e2; }
.crop-btn.confirm {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: #fff;
  box-shadow: 0 2px 8px rgba(102,126,234,.3);
  display: flex;
  align-items: center;
  gap: 6px;
}
.crop-btn.confirm:hover:not(:disabled) {
  opacity: .9;
  transform: translateY(-1px);
}
.crop-btn:disabled {
  opacity: .55;
  cursor: not-allowed;
}
.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 模态框过渡 */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity .25s;
}
.modal-fade-enter-active .crop-modal,
.modal-fade-leave-active .crop-modal {
  transition: transform .25s;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-from .crop-modal {
  transform: scale(.92) translateY(20px);
}
.modal-fade-leave-to .crop-modal {
  transform: scale(.92) translateY(20px);
}

/* 响应式 */
@media (max-width: 540px) {
  .crop-modal {
    width: 100%;
    max-width: none;
    border-radius: 14px 14px 0 0;
    margin-top: auto;
    max-height: 85vh;
  }
  .crop-container :deep([data-vue-cropper-root]) {
    min-height: 260px;
  }
  .crop-container :deep(cropper-canvas) {
    height: 260px;
  }
}
</style>
