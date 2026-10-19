<template>
  <div id="app">
    <h1>Secure Fullstack Lab</h1>
    
    <div v-if="!isLoggedIn">
      <LoginForm @login-success="onLoginSuccess" />
    </div>
    
    <div v-else>
      <button @click="handleLogout" style="margin-bottom: 20px;">Logout</button>
      <!-- O teu AssetList e AssetForm vão aqui -->
      <AssetList :assets="assets" />
      <AssetForm @created="fetchAssets" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { authService } from './services/auth';
import LoginForm from './components/LoginForm.vue';
import AssetList from './components/AssetList.vue';
import AssetForm from './components/AssetForm.vue';

const isLoggedIn = ref(authService.isAuthenticated());
const assets = ref([]);

const onLoginSuccess = () => {
  isLoggedIn.value = true;
  fetchAssets();
};

const handleLogout = () => {
  authService.logout();
  isLoggedIn.value = false;
  assets.value = [];
};

const fetchAssets = async () => {
  try {
    const res = await authService.api.get('/api/assets');
    assets.value = res.data;
  } catch (err) {
    console.error('Erro ao carregar assets:', err);
  }
};

onMounted(() => {
  if (isLoggedIn.value) fetchAssets();
});
</script>
