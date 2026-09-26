<script setup>
defineProps({
  assets: {
    type: Array,
    required: true,
  },
})
</script>

<template>
  <div class="asset-list">
    <h2>Assets</h2>

    <p v-if="assets.length === 0" class="empty">No assets yet.</p>

    <table v-else>
      <thead>
        <tr>
          <th>ID</th>
          <th>Hostname</th>
          <th>IP Address</th>
          <th>OS</th>
          <th>Created</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="asset in assets" :key="asset.id">
          <td>{{ asset.id }}</td>
          <td>{{ asset.hostname }}</td>
          <td>{{ asset.ip_address }}</td>
          <td>{{ asset.os }}</td>
          <td>{{ new Date(asset.created_at).toLocaleString() }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.asset-list {
  margin-top: 1.5rem;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin-top: 0.5rem;
}
th, td {
  text-align: left;
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid #ddd;
}
th {
  background: #f5f5f5;
  font-weight: 600;
}
.empty {
  color: #888;
  font-style: italic;
}
</style>
