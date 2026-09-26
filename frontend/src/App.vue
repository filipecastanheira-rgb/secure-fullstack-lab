<script setup>
import { ref, onMounted } from 'vue'

const message = ref('Loading...')

onMounted(async () => {
  try {
    const res = await fetch('http://192.168.1.173:8000/api/hello')
    const data = await res.json()
    message.value = data.message
  } catch (err) {
    message.value = 'Error contacting the API: ' + err.message
  }
})
</script>

<template>
  <h1>Secure Fullstack Lab</h1>
  <p>FastAPI response:</p>
  <p><strong>{{ message }}</strong></p>
</template>

<style scoped>
h1 { color: #42b883; }
</style>
