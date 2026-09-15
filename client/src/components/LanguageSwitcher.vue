<template>
  <div ref="rootEl" class="language-switcher" :class="{ collapsed: isSidebarCollapsed }">
    <button
      ref="buttonEl"
      class="language-button"
      @click="toggleDropdown"
      @blur="handleBlur"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        class="globe-icon"
      >
        <circle cx="10" cy="10" r="7.5" stroke="currentColor" stroke-width="1.5"/>
        <path d="M3 10H17" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10 3C10 3 7.5 5.5 7.5 10C7.5 14.5 10 17 10 17" stroke="currentColor" stroke-width="1.5"/>
        <path d="M10 3C10 3 12.5 5.5 12.5 10C12.5 14.5 10 17 10 17" stroke="currentColor" stroke-width="1.5"/>
      </svg>
      <span class="language-label">{{ localeName }}</span>
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
      <button
        v-for="locale in availableLocales"
        :key="locale"
        class="dropdown-item"
        :class="{ active: currentLocale === locale }"
        @mousedown.prevent="selectLanguage(locale)"
      >
        <span class="language-name">{{ getLanguageName(locale) }}</span>
        <svg
          v-if="currentLocale === locale"
          width="18"
          height="18"
          viewBox="0 0 18 18"
          fill="none"
          class="check-icon"
        >
          <path d="M4 9L7.5 12.5L14 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from '../composables/useI18n'

const { currentLocale, setLocale, availableLocales, localeName } = useI18n()

const isDropdownOpen = ref(false)

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

const languageNames = {
  en: 'English',
  ja: '日本語'
}

const getLanguageName = (locale) => {
  return languageNames[locale] || locale
}

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

const selectLanguage = (locale) => {
  setLocale(locale)
  closeDropdown()
}
</script>

<style scoped>
.language-switcher {
  position: relative;
  width: 100%;
}

.language-button {
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
  font-size: 0.875rem;
  color: var(--text-on-dark);
}

.language-button:hover {
  background: rgba(255, 255, 255, 0.06);
}

.globe-icon {
  flex-shrink: 0;
  color: var(--text-on-dark);
}

.language-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: left;
  font-weight: 500;
  color: var(--text-on-dark-active);
}

.chevron {
  color: var(--text-on-dark);
  transition: transform 0.2s ease;
  flex-shrink: 0;
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
  min-width: 160px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  z-index: 1000;
  overflow: hidden;
}

.dropdown-item {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
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

.dropdown-item.active {
  background: var(--accent-soft);
  color: var(--accent);
}

.language-name {
  flex: 1;
}

.check-icon {
  color: var(--accent);
  flex-shrink: 0;
}

/* Collapsed sidebar: icon-only trigger, no label overflow/wrap */
.language-switcher.collapsed .language-button {
  justify-content: center;
  padding: var(--space-2);
}

.language-switcher.collapsed .language-label,
.language-switcher.collapsed .chevron {
  display: none;
}
</style>
