// Reproduces the trellis_subagent model-resolution failure without any network
// call: runs pi's own resolver against its built-in catalog.
//
//   node probe-model-resolution.mjs                       # default refs
//   node probe-model-resolution.mjs "openai/gpt-5:high"    # exact refs to test
//
// Expected today: a bare id + ":thinking" (the shape the Trellis pi extension
// always produces) can resolve to an unauthenticated amazon-bedrock model.
import { execFileSync } from "node:child_process";

const PI_CORE =
  "file:///D:/scoop/persist/nvm/nodejs/v24.12.0/node_modules/@earendil-works/pi-coding-agent/dist/core/";

const { ModelRuntime } = await import(PI_CORE + "model-runtime.js");
const { resolveCliModel } = await import(PI_CORE + "model-resolver.js");

const refs = process.argv.slice(2);
const check = refs.length > 0 ? refs : ["gpt-5", "gpt-5:high", "openai/gpt-5:high"];

const rt = await ModelRuntime.create({});
const all = [...rt.getModels()];
console.log(`catalog: ${all.length} models / ${new Set(all.map((m) => m.provider)).size} providers\n`);

for (const ref of check) {
  const r = resolveCliModel({ cliModel: ref, modelRuntime: rt });
  const picked = r.model ? `${r.model.provider}/${r.model.id}` : "(none)";
  const authed = r.model ? rt.hasConfiguredAuth(r.model.provider) : false;
  console.log(
    `${ref.padEnd(24)} -> ${picked.padEnd(48)} auth=${authed}` +
      (r.warning ? `  warn=${r.warning}` : "") +
      (r.error ? `  err=${r.error}` : ""),
  );
}

// Why a fuzzy ref lands where it does: pi ranks partial matches by id descending.
const pattern = "gpt-5";
const isAlias = (id) => id.endsWith("-latest") || !/-\d{8}$/.test(id);
const matches = all.filter(
  (m) => m.id.toLowerCase().includes(pattern) || m.name?.toLowerCase().includes(pattern),
);
const ranked = matches.filter((m) => isAlias(m.id)).sort((a, b) => b.id.localeCompare(a.id));
console.log(`\nid contains "${pattern}": ${matches.length} matches, top 3 by pi's ranking:`);
for (const m of ranked.slice(0, 3)) console.log(`   ${m.provider}/${m.id}`);

// What the user can actually select (unauthenticated entries never appear here).
try {
  const listing = execFileSync("pi --list-models", { encoding: "utf8", shell: true });
  const rows = listing.trim().split("\n");
  console.log(
    `\npi --list-models: ${rows.length} rows, amazon-bedrock rows: ${rows.filter((l) => l.includes("amazon-bedrock")).length}`,
  );
} catch (e) {
  console.log(`\n(skipped: pi --list-models unavailable — ${e.message.split("\n")[0]})`);
}
