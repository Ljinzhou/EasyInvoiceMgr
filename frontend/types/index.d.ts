declare module '#app' {
  interface NuxtApp {
    $api: import('../plugins/axios').ApiInstance
  }
}

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $api: import('../plugins/axios').ApiInstance
  }
}

export {}

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}