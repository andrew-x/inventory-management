<template>
  <div ref="rootEl" class="profile-menu" :class="{ collapsed: isSidebarCollapsed }">
    <button
      ref="buttonEl"
      class="profile-button"
      @click="toggleDropdown"
      @blur="handleBlur"
    >
      <div class="avatar">
        {{ getInitials(currentUser.name) }}
      </div>
      <span class="profile-name">{{ currentUser.name }}</span>
      <svg
        class="chevron"
        :class="{ 'chevron-open': isDropdownOpen }"
        width="16"
        height="16"
        viewBox="0 0 16 16"
        fill="none"
      >
        <path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </button>

    <div v-if="isDropdownOpen" class="dropdown-menu" :style="dropdownStyle">
      <div class="dropdown-header">
        <div class="avatar-large">
          {{ getInitials(currentUser.name) }}
        </div>
        <div class="user-info">
          <div class="user-name">{{ currentUser.name }}</div>
          <div class="user-email">{{ currentUser.email }}</div>
        </div>
      </div>

      <div class="dropdown-divider"></div>

      <button
        class="dropdown-item"
        @mousedown.prevent="showProfileDetails"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M9 9C10.6569 9 12 7.65685 12 6C12 4.34315 10.6569 3 9 3C7.34315 3 6 4.34315 6 6C6 7.65685 7.34315 9 9 9Z" stroke="currentColor" stroke-width="1.5"/>
          <path d="M15 15C15 12.7909 12.3137 11 9 11C5.68629 11 3 12.7909 3 15" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        {{ t('profile.profileDetails') }}
      </button>

      <button
        class="dropdown-item"
        @mousedown.prevent="showTasks"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M15 3H3C2.44772 3 2 3.44772 2 4V14C2 14.5523 2.44772 15 3 15H15C15.5523 15 16 14.5523 16 14V4C16 3.44772 15.5523 3 15 3Z" stroke="currentColor" stroke-width="1.5"/>
          <path d="M6 7L8 9L12 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ t('profile.myTasks') }}
        <span v-if="pendingTaskCount > 0" class="task-badge">{{ pendingTaskCount }}</span>
      </button>

      <div class="dropdown-divider"></div>

      <button
        class="dropdown-item logout"
        @mousedown.prevent="handleLogout"
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <path d="M7 15H4C3.44772 15 3 14.5523 3 14V4C3 3.44772 3.44772 3 4 3H7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          <path d="M11 12L15 9M15 9L11 6M15 9H7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ t('profile.logout') }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useI18n } from '../composables/useI18n'

const { currentUser, logout, getInitials } = useAuth()
const { t } = useI18n()

const isDropdownOpen = ref(false)
const emit = defineEmits(['show-profile-details', 'show-tasks'])

// The sidebar footer sits inside `.sidebar`, which needs `overflow: hidden`
// for its expand/collapse width animation (Sidebar.vue, not ours to edit).
// That clips any absolutely-positioned dropdown wider than the sidebar
// column itself. Render the dropdown `position: fixed` instead, computed
// from the trigger's own bounding rect, so it escapes that clipping.
const buttonEl = ref(null)
const dropdownStyle = ref({})

const updateDropdownPosition = () => {
  const btn = buttonEl.value
  if (!btn) return
  const rect = btn.getBoundingClientRect()
  dropdownStyle.value = {
    position: 'fixed',
    left: `${rect.left}px`,
    bottom: `${window.innerHeight - rect.top + 8}px`,
    top: 'auto',
    right: 'auto'
  }
}

// Sidebar.vue tracks its own collapsed state and toggles a `.collapsed` class
// on its root `.sidebar` element (a foreign scope this component can't reach
// with plain/`:deep()` scoped-CSS selectors, since that ancestor sits outside
// this component's template). Mirror the class locally via a MutationObserver
// so the trigger can go icon-only without any prop/emit contract change.
const rootEl = ref(null)
const isSidebarCollapsed = ref(false)
let sidebarObserver = null

onMounted(() => {
  const sidebarEl = rootEl.value?.closest('.sidebar')
  if (sidebarEl) {
    isSidebarCollapsed.value = sidebarEl.classList.contains('collapsed')
    sidebarObserver = new MutationObserver(() => {
      isSidebarCollapsed.value = sidebarEl.classList.contains('collapsed')
    })
    sidebarObserver.observe(sidebarEl, { attributes: true, attributeFilter: ['class'] })
  }
})

onBeforeUnmount(() => {
  sidebarObserver?.disconnect()
  window.removeEventListener('resize', updateDropdownPosition)
})

const pendingTaskCount = computed(() => {
  return currentUser.value.tasks.filter(task => task.status === 'pending').length
})

const closeDropdown = () => {
  isDropdownOpen.value = false
  window.removeEventListener('resize', updateDropdownPosition)
}

const toggleDropdown = () => {
  isDropdownOpen.value = !isDropdownOpen.value
  if (isDropdownOpen.value) {
    nextTick(() => {
      updateDropdownPosition()
      window.addEventListener('resize', updateDropdownPosition)
    })
  } else {
    window.removeEventListener('resize', updateDropdownPosition)
  }
}

const handleBlur = () => {
  // Delay to allow mousedown events on dropdown items to fire first
  setTimeout(() => {
    closeDropdown()
  }, 200)
}

const showProfileDetails = () => {
  closeDropdown()
  emit('show-profile-details')
}

const showTasks = () => {
  closeDropdown()
  emit('show-tasks')
}

const handleLogout = () => {
  closeDropdown()
  logout()
}
</script>

<style scoped>
.profile-menu {
  position: relative;
  width: 100%;
}

.profile-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s ease;
  font-family: inherit;
  color: var(--text-on-dark);
}

.profile-button:hover {
  background: rgba(255, 255, 255, 0.06);
}

.avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.75rem;
  letter-spacing: 0.025em;
}

.profile-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-on-dark-active);
}

.chevron {
  flex-shrink: 0;
  color: var(--text-on-dark);
  transition: transform 0.2s ease;
}

.chevron-open {
  transform: rotate(180deg);
}

.dropdown-menu {
  /* Fallback only: actual position is computed inline as `position: fixed`
     (see updateDropdownPosition) so the dropdown escapes `.sidebar`'s
     `overflow: hidden`, which it needs for its width-collapse animation. */
  position: absolute;
  bottom: calc(100% + var(--space-2));
  top: auto;
  left: 0;
  right: auto;
  min-width: 280px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  z-index: 1000;
  overflow: hidden;
}

.dropdown-header {
  padding: var(--space-4);
  display: flex;
  gap: var(--space-3);
  align-items: center;
  background: var(--canvas);
}

.avatar-large {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  letter-spacing: 0.025em;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-weight: 600;
  color: var(--text);
  font-size: 0.938rem;
  margin-bottom: var(--space-1);
}

.user-email {
  font-size: 0.813rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dropdown-divider {
  height: 1px;
  background: var(--border);
  margin: var(--space-2) 0;
}

.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
}

.dropdown-item:hover {
  background: var(--canvas);
}

.dropdown-item svg {
  color: var(--text-muted);
  flex-shrink: 0;
}

.dropdown-item.logout {
  color: var(--danger);
}

.dropdown-item.logout svg {
  color: var(--danger);
}

.dropdown-item.logout:hover {
  background: #fef2f2;
}

.task-badge {
  margin-left: auto;
  background: var(--accent);
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.125rem var(--space-2);
  border-radius: 12px;
  min-width: 20px;
  text-align: center;
}

/* Collapsed sidebar: icon-only trigger, no label overflow/wrap */
.profile-menu.collapsed .profile-button {
  justify-content: center;
  padding: var(--space-2);
}

.profile-menu.collapsed .profile-name,
.profile-menu.collapsed .chevron {
  display: none;
}
</style>
