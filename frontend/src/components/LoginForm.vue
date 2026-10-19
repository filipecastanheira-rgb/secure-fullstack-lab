<template>
  <div class="login-container">
    <h2>Login</h2>
    <form @submit.prevent="handleLogin">
      <input v-model="email" type="email" placeholder="Email" required />
      <input v-model="password" type="password" placeholder="Password" required />
      <button type="submit" :disabled="loading">
        {{ loading ? 'A entrar...' : 'Entrar' }}
      </button>
      <p v-if="error" class="error">{{ error }}</p>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { authService } from '../services/auth';

const email = ref('');
const password = ref('');
const loading = ref(false);
const error = ref('');

const emit = defineEmits(['login-success']);

const handleLogin = async () => {
  loading.value = true;
  error.value = '';
  try {
    await authService.login(email.value, password.value);
    emit('login-success'); // Avisa o App.vue que o login foi feito
  } catch (err) {
    error.value = err.response?.data?.detail || 'Erro ao fazer login.';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.login-container { max-width: 300px; margin: 50px auto; text-align: center; }
input { display: block; width: 100%; padding: 10px; margin-bottom: 10px; box-sizing: border-box; }
button { width: 100%; padding: 10px; background: #42b983; color: white; border: none; cursor: pointer; }
.error { color: red; font-size: 0.9em; }
</style>
