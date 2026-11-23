// Batch-search Pexels video results with the ego browser.
//
// This file is a TEMPLATE: copy it, edit QUERIES / OUT / LIMIT below, then run
//   ego-browser nodejs < work/pexels_search.js
// It writes {key: {query, items:[{id, slug, thumb, href}]}} to OUT.
//
// Why a browser instead of curl: pexels.com/search is behind Cloudflare and
// answers 403 to plain HTTP clients, but renders fine in the ego browser.

const fs = await import("node:fs/promises");

// ---- EDIT ME ----------------------------------------------------------
const QUERIES = [
  ["aurora", "northern lights norway"],
  ["church", "hallgrimskirkja"],
  ["waterfall", "gullfoss waterfall"],
];
const OUT = "/tmp/pexels_index.json";
const LIMIT = 20;          // results kept per query
const ORIENT = "landscape"; // landscape | portrait | squarish | ""
// -----------------------------------------------------------------------

const task = await taskSpace("pexels-search");
const page = task.page("p1");
const out = {};

for (const [key, q] of QUERIES) {
  try {
    const url = `https://www.pexels.com/search/videos/${encodeURIComponent(q)}/` +
                (ORIENT ? `?orientation=${ORIENT}` : "");
    await page.goto(url, { timeout: 60000 });
    await page.waitForTimeout(2000);
    await page.evaluate(() => window.scrollBy(0, 900));
    await page.waitForTimeout(1500);
    const items = await page.evaluate((limit) => {
      return [...document.querySelectorAll("article")].slice(0, limit).map((a) => {
        const link = a.querySelector('a[href^="/video/"]');
        const href = link && link.getAttribute("href");
        const id = href && (href.match(/-(\d+)\/$/) || [])[1];
        const img = a.querySelector("img");
        const thumb = img && (img.currentSrc || img.src);
        return id ? { id, href, slug: href.split("/")[2], thumb } : null;
      }).filter(Boolean);
    }, LIMIT);
    out[key] = { query: q, items };
    console.log(key, items.length);
  } catch (e) {
    out[key] = { query: q, items: [], error: String(e).slice(0, 160) };
    console.log(key, "ERROR", String(e).slice(0, 100));
  }
}

await fs.writeFile(OUT, JSON.stringify(out, null, 1));
console.log("wrote", OUT, Object.keys(out).length, "queries");
