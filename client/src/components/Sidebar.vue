<template>
  <aside class="sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-brand">
      <span class="brand-mark">CC</span>
      <div class="brand-text">
        <h1>{{ t('nav.companyName') }}</h1>
        <span class="brand-subtitle">{{ t('nav.subtitle') }}</span>
      </div>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="nav-link"
        :aria-current="route.path === item.path ? 'page' : null"
      >
        <span class="nav-icon" aria-hidden="true">
          <svg viewBox="0 0 20 20" width="20" height="20" fill="none" v-html="item.icon"></svg>
        </span>
        <span class="nav-label">{{ t(item.labelKey) }}</span>
      </router-link>
    </nav>

    <button
      type="button"
      class="collapse-toggle"
      :aria-label="t('nav.toggleSidebar')"
      @click="toggleCollapsed"
    >
      <svg viewBox="0 0 20 20" width="18" height="18" fill="none">
        <path
          d="M12.5 4L7.5 10L12.5 16"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>

    <div class="sidebar-footer">
      <LanguageSwitcher />
      <ProfileMenu
        @show-profile-details="$emit('show-profile-details')"
        @show-tasks="$emit('show-tasks')"
      />
    </div>
  </aside>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from '../composables/useI18n'
import ProfileMenu from './ProfileMenu.vue'
import LanguageSwitcher from './LanguageSwitcher.vue'

const STORAGE_KEY = 'sidebar-collapsed'
const COLLAPSE_BREAKPOINT = 1024

const NAV_ITEMS = [
  {
    path: '/',
    labelKey: 'nav.overview',
    icon: '<rect x="3" y="3" width="6.5" height="6.5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10.5" y="3" width="6.5" height="6.5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="10.5" y="10.5" width="6.5" height="6.5" rx="1" stroke="currentColor" stroke-width="1.5"/><rect x="3" y="10.5" width="6.5" height="6.5" rx="1" stroke="currentColor" stroke-width="1.5"/>'
  },
  {
    path: '/inventory',
    labelKey: 'nav.inventory',
    icon: '<path d="M3 6.5L10 3L17 6.5L10 10L3 6.5Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M3 6.5V14L10 17.5V10" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M17 6.5V14L10 17.5" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>'
  },
  {
    path: '/orders',
    labelKey: 'nav.orders',
    icon: '<rect x="4" y="3" width="12" height="14" rx="1.5" stroke="currentColor" stroke-width="1.5"/><path d="M7.5 2.5V3.5C7.5 4.05228 7.94772 4.5 8.5 4.5H11.5C12.0523 4.5 12.5 4.05228 12.5 3.5V2.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M7 8H13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M7 11H13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M7 14H10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
  },
  {
    path: '/demand',
    labelKey: 'nav.demandForecast',
    icon: '<path d="M3 13.5L8 8.5L11 11.5L17 5.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M12.5 5.5H17V10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
  },
  {
    path: '/restocking',
    labelKey: 'nav.restocking',
    icon: '<path d="M17 10a7 7 0 01-12.5 4.35" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M3 10a7 7 0 0112.5-4.35" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M3 4v4.35h4.35" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/><path d="M17 16v-4.35h-4.35" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
  },
  {
    path: '/spending',
    labelKey: 'nav.finance',
    icon: '<path d="M4 17V10.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M10 17V4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M16 17V13" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
  },
  {
    path: '/reports',
    labelKey: 'nav.reports',
    icon: '<path d="M6 2H12L16 6V17C16 17.5523 15.5523 18 15 18H6C5.44772 18 5 17.5523 5 17V3C5 2.44772 5.44772 2 6 2Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M12 2V6H16" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/><path d="M7.5 10H12.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><path d="M7.5 13H12.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>'
  }
]

export default {
  name: 'Sidebar',
  components: {
    ProfileMenu,
    LanguageSwitcher
  },
  emits: ['show-profile-details', 'show-tasks', 'update:collapsed'],
  setup(props, { emit }) {
    const route = useRoute()
    const { t } = useI18n()

    const isCollapsed = ref(false)

    const readStoredPreference = () => {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored === null ? null : stored === 'true'
    }

    const applyCollapseState = () => {
      const stored = readStoredPreference()
      isCollapsed.value = stored === null ? window.innerWidth < COLLAPSE_BREAKPOINT : stored
    }

    const handleResize = () => {
      // Only auto-collapse/expand on resize if the user hasn't set an explicit preference
      if (readStoredPreference() === null) {
        isCollapsed.value = window.innerWidth < COLLAPSE_BREAKPOINT
      }
    }

    const toggleCollapsed = () => {
      isCollapsed.value = !isCollapsed.value
      localStorage.setItem(STORAGE_KEY, String(isCollapsed.value))
    }

    watch(isCollapsed, (value) => emit('update:collapsed', value), { immediate: true })

    onMounted(() => {
      applyCollapseState()
      window.addEventListener('resize', handleResize)
    })

    onBeforeUnmount(() => {
      window.removeEventListener('resize', handleResize)
    })

    return {
      t,
      route,
      navItems: NAV_ITEMS,
      isCollapsed,
      toggleCollapsed
    }
  }
}
</script>

<style scoped>
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  background: var(--sidebar-bg);
  color: var(--text-on-dark);
  display: flex;
  flex-direction: column;
  width: var(--sidebar-w);
  z-index: 100;
  transition: width 0.2s ease;
  overflow: hidden;
}

.sidebar.collapsed {
  width: var(--sidebar-w-collapsed);
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-5) var(--space-4);
  min-height: var(--topbar-h);
}

.brand-mark {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  background: rgba(37, 99, 235, 0.2);
  color: var(--text-on-dark-active);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.813rem;
  letter-spacing: 0.02em;
}

.brand-text {
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.brand-text h1 {
  font-size: 0.938rem;
  font-weight: 600;
  color: var(--text-on-dark-active);
  letter-spacing: -0.01em;
}

.brand-subtitle {
  display: block;
  font-size: 0.75rem;
  color: var(--text-on-dark);
}

.sidebar.collapsed .brand-text {
  display: none;
}

.sidebar-nav {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  flex: 1;
  overflow-y: auto;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  color: var(--text-on-dark);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-left: 2px solid transparent;
  transition: background 0.15s ease, color 0.15s ease;
  white-space: nowrap;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-on-dark-active);
}

.nav-link[aria-current='page'] {
  color: var(--text-on-dark-active);
  background: rgba(37, 99, 235, 0.15);
  border-left-color: var(--accent);
}

.nav-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
}

.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar.collapsed .nav-link {
  justify-content: center;
  padding: 0;
}

.sidebar.collapsed .nav-label {
  display: none;
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 var(--space-2) var(--space-2);
  padding: var(--space-2);
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: var(--radius-sm);
  color: var(--text-on-dark);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, transform 0.2s ease;
}

.collapse-toggle:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-on-dark-active);
}

.sidebar.collapsed .collapse-toggle svg {
  transform: rotate(180deg);
}

.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-2);
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

@media (max-width: 1024px) {
  .sidebar-brand {
    padding: var(--space-4) var(--space-3);
  }

  .nav-link {
    height: 44px;
  }
}
</style>
