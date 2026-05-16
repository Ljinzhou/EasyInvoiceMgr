import { ref, computed } from 'vue'

// Make Vue reactivity APIs available globally (they are auto-imported in Nuxt)
;(globalThis as any).ref = ref
;(globalThis as any).computed = computed
