import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DCC-MCP-IPC',
  description: 'Multi-protocol IPC adapter layer for DCC software integration with MCP',
  base: '/dcc-mcp-ipc/',

  head: [
    ['link', { rel: 'icon', href: '/dcc-mcp-ipc/logo.svg' }],
  ],

  locales: {
    root: {
      label: 'English',
      lang: 'en',
    },
    zh: {
      label: '中文',
      lang: 'zh-CN',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/guide/getting-started' },
          { text: 'API', link: '/zh/api/' },
          { text: '架构', link: '/zh/architecture' },
        ],
        sidebar: {
          '/zh/guide/': [
            {
              text: '入门',
              items: [
                { text: '快速开始', link: '/zh/guide/getting-started' },
                { text: '安装', link: '/zh/guide/installation' },
              ],
            },
            {
              text: '核心概念',
              items: [
                { text: '传输层', link: '/zh/guide/transport' },
                { text: '使用示例', link: '/zh/guide/usage' },
              ],
            },
          ],
        },
      },
    },
  },

  themeConfig: {
    logo: '/logo.svg',

    nav: [
      { text: 'Guide', link: '/guide/getting-started' },
      { text: 'API', link: '/api/' },
      { text: 'Architecture', link: '/architecture' },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/getting-started' },
            { text: 'Installation', link: '/guide/installation' },
          ],
        },
        {
          text: 'Core Concepts',
          items: [
            { text: 'Transport Layer', link: '/guide/transport' },
            { text: 'Usage Examples', link: '/guide/usage' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Transport', link: '/api/' },
            { text: 'Client', link: '/api/client' },
            { text: 'Server', link: '/api/server' },
            { text: 'Discovery', link: '/api/discovery' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/loonghao/dcc-mcp-ipc' },
    ],

    editLink: {
      pattern: 'https://github.com/loonghao/dcc-mcp-ipc/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-present Long Hao',
    },

    search: {
      provider: 'local',
    },
  },

  markdown: {
    // Enable mermaid diagrams
    config: (md) => {
      // Mermaid support is built-in to VitePress
    },
  },
})
