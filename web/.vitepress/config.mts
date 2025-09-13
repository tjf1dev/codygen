import { defineConfig } from "vitepress";

// https://vitepress.dev/reference/site-config
export default defineConfig({
  title: "codygen",
  description: "an all-in-one discord bot",
  themeConfig: {
    // https://vitepress.dev/reference/default-theme-config
    nav: [
      { text: "Home", link: "/" },
      { text: "Commands", link: "/commands" },
    ],

    sidebar: [
      {
        items: [
          { text: "Home", link: "/" },
          { text: "Commands", link: "/commands" },
        ],
      },
      {
        text: "Advanced",
        items: [{ text: "Command caching", link: "/command_cache" }],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/tjf1dev/codygen" },
    ],
  },
  cleanUrls: true,
});
