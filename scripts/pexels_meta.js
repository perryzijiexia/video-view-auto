// Verify what a Pexels clip actually shows by reading its page title/description.
//
// This is the step that stops "generic alpine cable car" from being sold as
// "Fjellheisen". Title text is the only metadata we can trust; slugs lie less
// often than thumbnails but they still lie.
//
// Copy, edit IDS / OUT, then:
//   ego-browser nodejs < work/pexels_meta.js

const fs = await import("node:fs/promises");

// ---- EDIT ME ----------------------------------------------------------
const IDS = ["4595479", "29477417", "11707765"];
const OUT = "/tmp/pexels_meta.json";
// -----------------------------------------------------------------------

const task = await taskSpace("pexels-meta");
const page = task.page("p1");
const out = {};

for (const id of IDS) {
  try {
    await page.goto(`https://www.pexels.com/video/${id}/`, { timeout: 45000 });
    await page.waitForTimeout(1200);
    const d = await page.evaluate(() => {
      const txt = document.body.innerText.replace(/\s+/g, " ");
      return {
        h1: (document.querySelector("h1") || {}).innerText || "",
        title: document.title.replace(" Free Stock Video Footage, Royalty-Free 4K & HD Video Clip", ""),
        body: txt.slice(0, 260),
      };
    });
    out[id] = d;
    console.log(id, "|", d.title);
  } catch (e) {
    out[id] = { error: String(e).slice(0, 160) };
    console.log(id, "ERROR");
  }
}

await fs.writeFile(OUT, JSON.stringify(out, null, 1));
console.log("wrote", OUT);
