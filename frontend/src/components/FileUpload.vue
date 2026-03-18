<template>
  <div class="upload-container">
    <h2>📄 Upload PDF Statement</h2>
    
    <!-- Upload Message -->
    <div v-if="message" :class="['message', messageType]">
      {{ message }}
      <button v-if="messageType === 'success'" @click="message = ''" class="close">×</button>
    </div>
    
    <!-- Upload Zone (single-step upload to Neon DB) -->
    <div 
      class="upload-zone"
      :class="{ dragging: isDragging, uploading: isUploading, disabled: disabled }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="!isInteractionDisabled && handleDrop($event)"
    >
      <input
        ref="fileInput"
        type="file"
        accept=".pdf"
        hidden
        :disabled="isInteractionDisabled"
        @change="handleFileSelect"
      />
      
      <div v-if="!isUploading" class="upload-content">
        <div class="upload-icon">📂</div>
        <p class="upload-text">
          <button
            class="link-button"
            type="button"
            :disabled="isInteractionDisabled"
            @click="!isInteractionDisabled && $refs.fileInput?.click()"
          >
            Click to upload
          </button>
          or drag and drop
        </p>
        <p class="upload-hint">
          PDF files up to 10MB
          <span v-if="disabled"> · Waiting for server to be ready…</span>
        </p>
      </div>
      
      <!-- Progress Bar -->
      <div v-else class="upload-progress">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
        <p>{{ uploadProgress }}% - {{ fileName }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { uploadPDF } from '../utils/api'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
})

const fileInput = ref(null)
const isDragging = ref(false)
const isUploading = ref(false)
const uploadProgress = ref(0)
const fileName = ref('')
const message = ref('')
const messageType = ref('error')

const emit = defineEmits(['upload-success'])

const isInteractionDisabled = computed(() => props.disabled || isUploading.value)

async function handleFileSelect(event) {
  const file = event.target.files?.[0]
  if (file) {
    await uploadFile(file)
  }
}

function handleDrop(event) {
  isDragging.value = false
  const file = event.dataTransfer?.files[0]
  if (file) {
    uploadFile(file)
  }
}

async function uploadFile(file) {
  // Validation
  if (!file.name.endsWith('.pdf')) {
    message.value = 'Only PDF files are allowed'
    messageType.value = 'error'
    return
  }
  
  if (file.size > 10 * 1024 * 1024) {
    message.value = 'File must be smaller than 10MB'
    messageType.value = 'error'
    return
  }
  
  isUploading.value = true
  fileName.value = file.name
  uploadProgress.value = 0
  message.value = ''
  
  try {
    const response = await uploadPDF(file, (percent) => {
      // Guard against NaN or unexpected values
      if (Number.isFinite(percent)) {
        uploadProgress.value = Math.min(100, Math.max(0, percent))
      }
    })
    // Ensure progress bar shows complete state before hiding
    uploadProgress.value = 100
    isUploading.value = false
    message.value = response.message || '✓ Successfully stored transactions in Neon database'
    messageType.value = 'success'
    fileInput.value.value = ''
    emit('upload-success', response)
  } catch (err) {
    isUploading.value = false
    message.value = err.error || err.message || 'Upload failed'
    messageType.value = 'error'
  }
}
</script>

<style scoped>
.upload-container {
  width: 100%;
}

.upload-container h2 {
  margin-bottom: 20px;
  color: #333;
}

.confirmation-section {
  background: #f9f9f9;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
}

.confirmation-section h3 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
}

.confirmation-info {
  color: #666;
  margin-bottom: 20px;
  font-size: 14px;
}

.button-group {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 14px;
}

.btn-primary {
  background-color: #667eea;
  color: white;
}

.btn-primary:hover {
  background-color: #5568d3;
}

.btn-success {
  background-color: #3cb371;
  color: white;
}

.btn-success:hover:not(:disabled) {
  background-color: #2d9255;
}

.btn-success:disabled {
  background-color: #aaa;
  cursor: not-allowed;
  opacity: 0.7;
}

.btn-secondary {
  background-color: #e0e0e0;
  color: #333;
}

.btn-secondary:hover {
  background-color: #d0d0d0;
}

.message {
  padding: 12px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 500;
}

.message.error {
  background-color: #fee;
  color: #c33;
  border: 1px solid #fcc;
}

.message.success {
  background-color: #efe;
  color: #3c3;
  border: 1px solid #cfc;
}

.message .close {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: inherit;
  padding: 0;
  width: 24px;
  height: 24px;
}

.upload-zone {
  border: 2px dashed #ccc;
  border-radius: 12px;
  padding: 40px;
  text-align: center;
  transition: all 0.3s ease;
  cursor: pointer;
  background-color: #fafafa;
}

.upload-zone.dragging {
  border-color: #667eea;
  background-color: #f0f4ff;
  box-shadow: 0 0 20px rgba(102, 126, 234, 0.1);
}

.upload-zone.uploading {
  opacity: 0.7;
  cursor: not-allowed;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.upload-icon {
  font-size: 48px;
}

.upload-text {
  font-size: 16px;
  margin: 10px 0;
}

.link-button {
  background: none;
  border: none;
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  font-size: inherit;
  padding: 0;
}

.link-button:hover {
  color: #764ba2;
}

.upload-hint {
  font-size: 14px;
  color: #999;
  margin: 5px 0;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background-color: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  max-width: 300px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
  border-radius: 4px;
}

.upload-progress p {
  font-size: 14px;
  color: #666;
}

@media (max-width: 768px) {
  .upload-zone {
    padding: 30px 20px;
  }
  
  .upload-icon {
    font-size: 36px;
  }
  
  .upload-text {
    font-size: 14px;
  }
}
</style>
