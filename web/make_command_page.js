import fs from "fs";
import path from "path";

const cacheFile = path.resolve("./cache/commands.json");
const outFile = path.resolve("./commands.md");

if (!fs.existsSync(cacheFile)) {
  console.error("commands.json not found!");
  process.exit(1);
}

const commands = JSON.parse(fs.readFileSync(cacheFile, "utf8"));

const grouped = {};
for (const cmd of commands) {
  const cog = cmd.cog_name || "uncategorized";
  if (!grouped[cog]) grouped[cog] = [];
  grouped[cog].push(cmd);
}
function formatDate(date = new Date()) {
  const pad = (n) => n.toString().padStart(2, "0");

  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hours = pad(date.getUTCHours());
  const minutes = pad(date.getUTCMinutes());
  const seconds = pad(date.getUTCSeconds());

  return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
}

let md = `---
title: Commands
aside: true
---
<!-- auto generated on ${formatDate()} -->
# Commands
`;

for (const cog of Object.keys(grouped)) {
  md += `\n## ${cog} (module)\n${grouped[cog][0].cog_description}  \n${grouped[cog].length} commands`;
  for (const cmd of grouped[cog]) {
    md += `\n## ${cmd.full_name}\n`;
    if (cmd.dpy_description) md += `${cmd.dpy_description}\n`;
    const opts = cmd.command?.options || [];
    if (opts.length) {
      md += `\n### Options:\n`;
      for (const o of opts) {
        md += `- **${o.name}** (${o.required ? "required" : "optional"}) — ${
          o.description
        }\n`;
      }
    }
  }
}
md += `\nthis page was automatically generated on ${formatDate()}`;
fs.writeFileSync(outFile, md);
console.log(`generated ${outFile}`);
