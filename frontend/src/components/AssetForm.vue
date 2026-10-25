<script setup>
import { ref } from 'vue'

import { API_ENDPOINTS } from '../config'
import { authService } from '../services/auth'

const emit = defineEmits(['created'])

const hostname = ref('')
const ipAddress = ref('')
const os = ref('')
const error = ref('')
const loading = ref(false)

const API_URL = API_ENDPOINTS.assets

async function submit() {
  error.value = ''
  loading.value = true

  try {
    await authService.api.post(API_URL, {
      hostname: hostname.value,
      ip_address: ipAddress.value,
      os: os.value,
    })

    hostname.value = ''
    ipAddress.value = ''
    os.value = ''
    emit('created')
  } catch (err) {
    const detail = err.response?.data?.detail
    error.value =
      (Array.isArray(detail) ? detail[0]?.msg : detail) ||
      (err.response ? `HTTP ${err.response.status}` : err.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <form class="asset-form" @submit.prevent="submit">
    <h2>Add Asset</h2>

    <div class="row">
      <label>
        Hostname
        <input v-model="hostname" type="text" required maxlength="100" />
      </label>

      <label>
        IP Address
        <input v-model="ipAddress" type="text" required maxlength="45" />
      </label>

      <label>
        OS
        <input v-model="os" type="text" required maxlength="100" />
      </label>

      <button type="submit" :disabled="loading">
        {{ loading ? 'Saving...' : 'Add' }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
  </form>
</template>

<style scoped>
.asset-form {
  margin-top: 1.5rem;
  padding: 1rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #fafafa;
}
.row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  align-items: flex-end;
}
label {
  display: flex;
  flex-direction: column;
  font-size: 0.85rem;
  color: #444;
  gap: 0.25rem;
}
input {
  padding: 0.4rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 4px;
  font-size: 0.95rem;
}
button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #42b883;
  color: white;
  font-weight: 600;
  cursor: pointer;
}
button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.error {
  color: #c0392b;
  margin-top: 0.75rem;
}
</style>
