import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'DCC-MCP-IPC',
  description: 'Multi-protocol IPC adapter layer for DCC software integration with Model Context Protocol',
  base: '/dcc-mcp-ipc/',
  lang: 'en-US',

  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/dcc-mcp-ipc/logo.svg' }],
    ['meta', { name: 'theme-color', content: '#646cff' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:title', content: 'DCC-MCP-IPC' }],
    ['meta', { property: 'og:description', content: 'Multi-protocol IPC adapter layer for DCC software' }],
  ],

  themeConfig: {
    logo: {
      src: '/logo.svg',
      alt: 'DCC-MCP-IPC',
    },

    nav: [
      { text: 'Guide', link: '/guide/introduction' },
      { text: 'API Reference', link: '/api/overview' },
      { text: 'Examples', link: '/examples/quickstart' },
      {
        text: 'v2.0.0',
        items: [
          { text: 'Changelog', link: 'https://github.com/loonghao/dcc-mcp-ipc/blob/main/CHANGELOG.md' },
          { text: 'Contributing', link: 'https://github.com/loonghao/dcc-mcp-ipc/blob/main/CONTRIBUTING.md' },
        ],
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: 'Getting Started',
          items: [
            { text: 'Introduction', link: '/guide/introduction' },
            { text: 'Installation', link: '/guide/installation' },
            { text: 'Quick Start', link: '/guide/quickstart' },
          ],
        },
        {
          text: 'Core Concepts',
          items: [
            { text: 'Architecture', link: '/guide/architecture' },
            { text: 'Action System', link: '/guide/action-system' },
            { text: 'Skills System', link: '/guide/skills' },
            { text: 'Transport Layer', link: '/guide/transports' },
            { text: 'Service Discovery', link: '/guide/discovery' },
          ],
        },
        {
          text: 'Advanced',
          items: [
            { text: 'Connection Pool', link: '/guide/connection-pool' },
            { text: 'Async Client', link: '/guide/async-client' },
            { text: 'Custom Adapters', link: '/guide/custom-adapters' },
            { text: 'Testing', link: '/guide/testing' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API Reference',
          items: [
            { text: 'Overview', link: '/api/overview' },
            { text: 'ActionAdapter', link: '/api/action-adapter' },
            { text: 'SkillManager', link: '/api/skill-manager' },
            { text: 'DCCServer', link: '/api/server' },
            { text: 'BaseDCCClient', link: '/api/client' },
            { text: 'ConnectionPool', link: '/api/connection-pool' },
            { text: 'Transports', link: '/api/transports' },
            { text: 'Discovery', link: '/api/discovery' },
          ],
        },
      ],
      '/examples/': [
        {
          text: 'Examples',
          items: [
            { text: 'Quick Start', link: '/examples/quickstart' },
            { text: 'Maya Integration', link: '/examples/maya' },
            { text: 'Houdini Integration', link: '/examples/houdini' },
            { text: 'Blender Integration', link: '/examples/blender' },
            { text: 'Service Factories', link: '/examples/service-factories' },
            { text: 'Skills Example', link: '/examples/skills' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/loonghao/dcc-mcp-ipc' },
    ],

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2024-present Hal Long',
    },

    editLink: {
      pattern: 'https://github.com/loonghao/dcc-mcp-ipc/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    search: {
      provider: 'local',
    },
  },

  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
  },
})
