<template>
  <div class="avatar-upload">
    <!-- 头像展示区域 -->
    <div class="avatar-display-section">
      <div
        class="avatar-wrapper"
        :class="{ 'is-cropping': showCropper, 'is-uploading': uploading }"
      >
        <img
          v-if="previewUrl && !showCropper"
          :src="previewUrl"
          alt="头像预览"
          class="avatar-img"
          @error="handleImageError"
        />
        <div v-else-if="!showCropper" class="avatar-placeholder">
          <svg viewBox="0 0 120 120" width="60" height="60" xmlns="http://www.w3.org/2000/svg">
            <circle cx="60" cy="50" r="28" fill="currentColor" opacity="0.6"/>
            <ellipse cx="60" cy="108" rx="48" ry="32" fill="currentColor" opacity="0.4"/>
          </svg>
        </div>

        <!-- 裁剪模式下的预览 -->
        <ClientOnly>
          <div v-if="showCropper" class="cropper-wrapper">
            <CropperImage
              ref="cropperComponentRef"
              :src="cropSourceUrl"
              :canvas-props="{ background: true }"
              :image-props="{ rotatable: true, scalable: true, translatable: true }"
              :selection-props="{ aspectRatio: 1, initialCoverage: 0.85, movable: true, resizable: true }"
              @ready="onCropperReady"
              @change="onCropChange"
              @error="onCropperError"
            />
          </div>
        </ClientOnly>

        <!-- Hover 遮罩 - 非裁剪模式下显示 -->
        <div v-if="!showCropper && !uploading" class="avatar-overlay" @click="triggerFileInput">
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
          <span>{{ previewUrl ? '更换头像' : '上传头像' }}</span>
        </div>

        <!-- 上传中遮罩 -->
        <div v-if="uploading" class="uploading-overlay">
          <div class="spinner-ring">
            <div></div><div></div><div></div><div></div>
          </div>
          <span class="uploading-text">上传中...</span>
        </div>
      </div>

      <!-- 头像下方信息 -->
      <div class="avatar-meta">
        <p class="avatar-hint">支持 JPG、PNG、WEBP 格式，最大 5MB</p>
      </div>
    </div>

    <!-- 裁剪工具栏 -->
    <transition name="toolbar-slide">
      <div v-if="showCropper" class="cropper-toolbar">
        <div class="toolbar-group">
          <button
            class="tool-btn"
            title="放大"
            :disabled="uploading"
            @click="handleZoomIn"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="11" y1="8" x2="11" y2="14"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>
          <button
            class="tool-btn"
            title="缩小"
            :disabled="uploading"
            @click="handleZoomOut"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              <line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>
          <div class="toolbar-divider"></div>
          <button
            class="tool-btn"
            title="向左旋转"
            :disabled="uploading"
            @click="handleRotate"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="1 4 1 10 7 10"/>
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/>
            </svg>
          </button>
          <button
            class="tool-btn"
            title="重置"
            :disabled="uploading"
            @click="handleReset"
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="1 4 1 10 7 10"/>
              <polyline points="23 20 23 14 17 14"/>
              <path d="M20.49 9A9 9 0 0 0 5.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 0 1 3.51 15"/>
            </svg>
          </button>
        </div>

        <div class="crop-dimensions">
          <span>{{ cropWidth }} × {{ cropHeight }} px</span>
        </div>
      </div>
    </transition>

    <!-- 操作按钮 -->
    <transition name="actions-slide">
      <div v-if="showCropper" class="cropper-actions">
        <button class="action-btn secondary" :disabled="uploading" @click="cancelCrop">
          取消
        </button>
        <button
          class="action-btn primary"
          :disabled="uploading || !isCropperReady"
          @click="confirmCrop"
        >
          {{ uploading ? '上传中...' : '确认保存' }}
        </button>
      </div>
    </transition>

    <!-- 非裁剪模式下的操作 -->
    <div v-if="!showCropper && previewUrl" class="avatar-actions-row">
      <button class="text-btn" @click="triggerFileInput">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
          <circle cx="12" cy="13" r="4"/>
        </svg>
        更换头像
      </button>
      <button class="text-btn danger" :disabled="deleting" @click="handleDelete">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="3 6 5 6 21 6"/>
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
        </svg>
        {{ deleting ? '删除中...' : '删除头像' }}
      </button>
    </div>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="file-input-hidden"
      @change="handleFileSelect"
    />

    <!-- 状态提示 -->
    <transition name="status-fade">
      <div v-if="statusMessage" class="status-toast" :class="statusType">
        <svg v-if="statusType === 'success'" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
        <svg v-else-if="statusType === 'error'" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="16" x2="12" y2="12"/>
          <line x1="12" y1="8" x2="12.01" y2="8"/>
        </svg>
        <span>{{ statusMessage }}</span>
        <button v-if="statusType === 'error' && lastSourceFile" class="retry-btn" @click="retrySelect">
          重试
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onBeforeUnmount } from 'vue'
import { CropperImage } from '@xcvzmoon/vue-cropperjs'

const MAX_FILE_SIZE = 5 * 1024 * 1024
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

const props = defineProps({
  currentAvatarUrl: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['avatar-updated'])

const { $api } = useNuxtApp()

const fileInputRef = ref(null)
const cropperComponentRef = ref(null)
const previewUrl = ref(props.currentAvatarUrl || '')
const showCropper = ref(false)
const cropSourceUrl = ref('')
const uploading = ref(false)
const deleting = ref(false)
const isCropperReady = ref(false)
const cropWidth = ref(0)
const cropHeight = ref(0)
const statusMessage = ref('')
const statusType = ref('info')
const lastSourceFile = ref(null)
let statusTimer = null

function validateFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    showStatus('不支持的文件格式，请选择 JPG、PNG 或 WEBP 图片', 'error')
    return false
  }
  if (file.size > MAX_FILE_SIZE) {
    showStatus('文件大小不能超过 5MB', 'error')
    return false
  }
  return true
}

function showStatus(message, type = 'info') {
  statusMessage.value = message
  statusType.value = type
  if (statusTimer) clearTimeout(statusTimer)
  if (type !== 'error') {
    statusTimer = setTimeout(() => {
      statusMessage.value = ''
    }, 4000)
  }
}

function clearStatus() {
  statusMessage.value = ''
  statusType.value = 'info'
  if (statusTimer) clearTimeout(statusTimer)
}

function openCropper(file) {
  lastSourceFile.value = file
  cropSourceUrl.value = URL.createObjectURL(file)
  showCropper.value = true
  clearStatus()
}

function cancelCrop() {
  if (cropSourceUrl.value) {
    URL.revokeObjectURL(cropSourceUrl.value)
  }
  showCropper.value = false
  cropSourceUrl.value = ''
  isCropperReady.value = false
  cropWidth.value = 0
  cropHeight.value = 0
  clearStatus()
}

function onCropperReady() {
  isCropperReady.value = true
}

function onCropChange(event) {
  const detail = event.detail
  if (detail) {
    cropWidth.value = Math.round(detail.width)
    cropHeight.value = Math.round(detail.height)
  }
}

function onCropperError(error) {
  showStatus(`图片加载失败: ${error.message}`, 'error')
}

function handleZoomIn() {
  cropperComponentRef.value?.zoomImage(0.1)
}

function handleZoomOut() {
  cropperComponentRef.value?.zoomImage(-0.1)
}

function handleRotate() {
  cropperComponentRef.value?.rotateImage(90)
}

function handleReset() {
  cropperComponentRef.value?.resetImageTransform()
  cropperComponentRef.value?.resetSelection()
}

async function confirmCrop() {
  const cropper = cropperComponentRef.value
  if (!cropper || !isCropperReady.value) return

  uploading.value = true
  showStatus('正在处理头像...', 'info')

  try {
    const canvas = await cropper.toCanvas()
    if (!canvas) {
      showStatus('裁切失败，请重试', 'error')
      return
    }

    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob)
        else reject(new Error('Canvas toBlob failed'))
      }, 'image/png')
    })

    const formData = new FormData()
    formData.append('file', blob, 'avatar.png')

    const response = await $api.post('/auth/avatar/upload', formData)

    if (response.data?.code === 200 && response.data?.data?.avatar_url) {
      const newUrl = response.data.data.avatar_url
      previewUrl.value = newUrl
      emit('avatar-updated', newUrl)
      showStatus('头像更新成功', 'success')
      cancelCrop()
    } else {
      showStatus(response.data?.message || '上传失败，请重试', 'error')
    }
  } catch (error) {
    showStatus(error.response?.data?.message || '上传失败，请检查网络连接', 'error')
  } finally {
    uploading.value = false
  }
}

function triggerFileInput() {
  if (uploading.value) return
  fileInputRef.value?.click()
}

function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (!file) return

  if (validateFile(file)) {
    openCropper(file)
  }
  event.target.value = ''
}

function retrySelect() {
  lastSourceFile.value = null
  clearStatus()
  triggerFileInput()
}

async function handleDelete() {
  if (deleting.value) return

  deleting.value = true
  showStatus('正在删除头像...', 'info')

  try {
    const response = await $api.delete('/auth/avatar')
    if (response.data?.code === 200) {
      previewUrl.value = ''
      emit('avatar-updated', '')
      showStatus('头像已删除', 'success')
    } else {
      showStatus(response.data?.message || '删除失败，请重试', 'error')
    }
  } catch (error) {
    showStatus(error.response?.data?.message || '删除失败，请检查网络连接', 'error')
  } finally {
    deleting.value = false
  }
}

function handleImageError() {
  previewUrl.value = ''
}

onBeforeUnmount(() => {
  if (cropSourceUrl.value) {
    URL.revokeObjectURL(cropSourceUrl.value)
  }
  if (statusTimer) clearTimeout(statusTimer)
})
</script>

<style scoped>
.avatar-upload {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

/* 头像展示区域 */
.avatar-display-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.avatar-wrapper {
  position: relative;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  border: 3px solid #e8ecf1;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.avatar-wrapper:hover {
  border-color: #667eea;
  box-shadow: 0 4px 20px rgba(102, 126, 234, 0.25);
  transform: scale(1.02);
}

.avatar-wrapper.is-cropping {
  width: 280px;
  height: 280px;
  border-radius: 12px;
  cursor: default;
  border-color: #ddd;
}

.avatar-wrapper.is-cropping:hover {
  transform: none;
  box-shadow: none;
  border-color: #ddd;
}

.avatar-wrapper.is-uploading {
  cursor: not-allowed;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #a0aec0;
}

/* 裁剪器包装 */
.cropper-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cropper-wrapper :deep(cropper-canvas) {
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: 100%;
}

.cropper-wrapper :deep(cropper-image) {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* Hover 遮罩 */
.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(102, 126, 234, 0.75);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
  gap: 6px;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.avatar-overlay svg {
  width: 28px;
  height: 28px;
}

.avatar-overlay span {
  font-size: 13px;
  font-weight: 500;
}

/* 上传中遮罩 */
.uploading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #667eea;
}

.spinner-ring {
  display: inline-block;
  position: relative;
  width: 36px;
  height: 36px;
}

.spinner-ring div {
  box-sizing: border-box;
  display: block;
  position: absolute;
  width: 30px;
  height: 30px;
  margin: 3px;
  border: 3px solid #667eea;
  border-radius: 50%;
  animation: spinner-ring 1.2s cubic-bezier(0.5, 0, 0.5, 1) infinite;
  border-color: #667eea transparent transparent transparent;
}

.spinner-ring div:nth-child(1) { animation-delay: -0.45s; }
.spinner-ring div:nth-child(2) { animation-delay: -0.3s; }
.spinner-ring div:nth-child(3) { animation-delay: -0.15s; }

@keyframes spinner-ring {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.uploading-text {
  font-size: 13px;
  font-weight: 500;
  color: #667eea;
}

/* 头像元信息 */
.avatar-meta {
  margin-top: 12px;
  text-align: center;
}

.avatar-hint {
  font-size: 12px;
  color: #95a5a6;
  margin: 0;
}

/* 裁剪工具栏 */
.cropper-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 320px;
  margin-top: 16px;
  padding: 8px 12px;
  background: #f8f9fa;
  border-radius: 10px;
  border: 1px solid #e9ecef;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tool-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  color: #555;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.tool-btn:hover:not(:disabled) {
  background: #667eea;
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.toolbar-divider {
  width: 1px;
  height: 24px;
  background: #dee2e6;
  margin: 0 4px;
}

.crop-dimensions {
  font-size: 12px;
  color: #7f8c8d;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

/* 操作按钮 */
.cropper-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  width: 100%;
  max-width: 280px;
  justify-content: center;
}

.action-btn {
  flex: 1;
  padding: 10px 20px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.action-btn.secondary {
  background: #f0f0f0;
  color: #666;
}

.action-btn.secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.action-btn.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.action-btn.primary:hover:not(:disabled) {
  opacity: 0.9;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none !important;
}

/* 非裁剪模式操作行 */
.avatar-actions-row {
  display: flex;
  gap: 16px;
  margin-top: 14px;
}

.text-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: #667eea;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.text-btn:hover:not(:disabled) {
  background: rgba(102, 126, 234, 0.08);
}

.text-btn.danger {
  color: #e74c3c;
}

.text-btn.danger:hover:not(:disabled) {
  background: rgba(231, 76, 60, 0.08);
}

.text-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.text-btn svg {
  flex-shrink: 0;
}

/* 隐藏文件输入 */
.file-input-hidden {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

/* 状态提示 */
.status-toast {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  animation: slideUpFade 0.3s ease;
}

.status-toast.success {
  background: #d4edda;
  color: #155724;
}

.status-toast.error {
  background: #f8d7da;
  color: #721c24;
}

.status-toast.info {
  background: #e8f4fd;
  color: #0c5460;
}

.retry-btn {
  margin-left: 4px;
  padding: 3px 10px;
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.retry-btn:hover {
  background: rgba(0, 0, 0, 0.05);
}

/* 动画 */
@keyframes slideUpFade {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.toolbar-slide-enter-active,
.toolbar-slide-leave-active,
.actions-slide-enter-active,
.actions-slide-leave-active {
  transition: all 0.3s ease;
}

.toolbar-slide-enter-from,
.toolbar-slide-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.actions-slide-enter-from,
.actions-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition: all 0.3s ease;
}

.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

/* 响应式 */
@media (max-width: 480px) {
  .avatar-wrapper.is-cropping {
    width: 240px;
    height: 240px;
  }

  .cropper-toolbar {
    max-width: 260px;
    padding: 6px 8px;
  }

  .tool-btn {
    width: 32px;
    height: 32px;
  }

  .crop-dimensions {
    font-size: 11px;
  }
}
</style>
