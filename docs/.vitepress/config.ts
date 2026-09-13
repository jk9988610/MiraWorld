import { defineConfig } from 'vitepress'

export default defineConfig({
  vite: {
    server: {
      proxy: {
        '/miraworld/api': {
          target: 'http://127.0.0.1:8787',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/miraworld\/api/, ''),
        },
      },
    },
  },
  lang: 'zh-Hans',
  title: '米拉世界',
  titleTemplate: ':title · 米拉世界',
  description: '米拉世界 MiraWorld — 潮灯市可探索的异步文字世界',
  base: '/miraworld/',
  cleanUrls: false,
  themeConfig: {
    logo: undefined,
    siteTitle: '米拉世界',
    nav: [
      { text: '潮灯市', link: '/play/city' },
      { text: '世界', link: '/world/overview' },
      { text: '探索', link: '/world/exploration' },
      { text: '术语', link: '/reference/glossary' },
    ],
    sidebar: [
      {
        text: '总览',
        items: [
          { text: '首页', link: '/' },
          { text: '如何阅读本站', link: '/guide/how-to-read' },
          { text: '登录', link: '/auth/login' },
          { text: '注册', link: '/auth/register' },
        ],
      },
      {
        text: '游戏',
        items: [
          { text: '潮灯市', link: '/play/city' },
          { text: '通知', link: '/play/messages' },
          { text: '背包', link: '/play/stacks' },
          { text: '我的', link: '/play/me' },
        ],
      },
      {
        text: '世界',
        items: [
          { text: '世界概览', link: '/world/overview' },
          { text: '时间线', link: '/world/timeline' },
          { text: '探索法则', link: '/world/exploration' },
        ],
      },
      {
        text: '地点',
        items: [
          { text: '灰烬港', link: '/places/ashen-harbor' },
          { text: '镜湖驿', link: '/places/mirror-lake' },
          { text: '断弦塔', link: '/places/broken-string-tower' },
        ],
      },
      {
        text: '势力与人物',
        items: [
          { text: '潮灯商会', link: '/factions/tide-lantern' },
          { text: '拾遗院', link: '/factions/relic-archive' },
          { text: '林溯', link: '/characters/lin-su' },
          { text: '柯岚', link: '/characters/ke-lan' },
        ],
      },
      {
        text: '词条',
        items: [
          { text: '术语表', link: '/reference/glossary' },
        ],
      },
    ],
    outline: {
      level: [2, 3],
      label: '本页目录',
    },
    search: {
      provider: 'local',
      options: {
        translations: {
          button: {
            buttonText: '搜索',
            buttonAriaLabel: '搜索',
          },
          modal: {
            noResultsText: '无结果',
            resetButtonTitle: '清除',
            footer: {
              selectText: '选择',
              navigateText: '切换',
              closeText: '关闭',
            },
          },
        },
      },
    },
    docFooter: {
      prev: '上一页',
      next: '下一页',
    },
    returnToTopLabel: '回到顶部',
    sidebarMenuLabel: '菜单',
    darkModeSwitchLabel: '外观',
    lightModeSwitchTitle: '切换到浅色',
    darkModeSwitchTitle: '切换到深色',
  },
})
