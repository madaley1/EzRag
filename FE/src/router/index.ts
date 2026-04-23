import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '../views/ChatView.vue'
import FilesView from '../views/FilesView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/chat' },
    { path: '/chat', component: ChatView },
    { path: '/files', component: FilesView },
  ],
})

export default router
