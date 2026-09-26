<script setup>
import { ref, onMounted } from 'vue'
import AssetList from './components/AssetList.vue'
import AssetForm from './components/AssetForm.vue'
import { API_ENDPOINTS } from './config'

const API_URL = API_ENDPOINTS.assets

const assets = ref([])
const loading = ref(false)
const error = ref('')

async function loadAssets() {
  loading.value = true
  error.value = ''

  try {
    const res = await fetch(API_URL)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    assets.value = await res.json()
  } catch (err) {
    error.value = 'Could not load assets: ' + err.message
  } finally {
    loading.value = false
  }
}

onMounted(loadAssets)
</script>

<template>
  <main>
    <h1>Secure Fullstack Lab</h1>
    <p class="subtitle">Asset inventory</p>

    <AssetForm @created="loadAssets" />

    <p v-if="loading" class="info">Loading...</p>
    <p v-else-if="error" class="error">{{ error }}</p>
    <AssetList v-else :assets="assets" />
  </main>
</template>

<style scoped>
main {
  max-width: 900px;
  margin: 2rem auto;
  padding: 0 1rem;
  font-family: system-ui, -apple-system, sans-serif;
}
h1 {
  color: #42b883;
  margin-bottom: 0.25rem;
}
.subtitle {
  color: #666;
  margin-top: 0;
}
.info {
  color: #888;
}
.error {
  color: #c0392b;
}
</style>
