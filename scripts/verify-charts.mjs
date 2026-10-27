import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const root = resolve(import.meta.dirname, "..");
const require = createRequire(resolve(root, "frontend/package.json"));
const { createServer } = await import(pathToFileURL(require.resolve("vite")));
const { chromium } = require("playwright");
export async function verifyCharts(connectedBrowser) {
  const output = resolve(
    root,
    "target/chart-verification",
    new Date().toISOString().replaceAll(":", "-"),
  );
  await mkdir(output, { recursive: true });
  const id = resolve(root, "frontend/__chart-fixture.tsx").replaceAll(
    "\\",
    "/",
  );
  const server = await createServer({
    root: resolve(root, "frontend"),
    configFile: resolve(root, "frontend/vite.config.ts"),
    server: { host: "127.0.0.1", port: 0 },
    plugins: [
      {
        name: "chart-verification",
        resolveId(source) {
          if (source === "/__chart-fixture.tsx" || source === id) return id;
        },
        load(source) {
          if (source === id)
            return readFile(resolve(root, "scripts/chart-fixture.tsx"), "utf8");
        },
        configureServer(vite) {
          vite.middlewares.use(async (req, res, next) => {
            if (req.url?.split("?")[0] !== "/__charts") return next();
            res.setHeader("Content-Type", "text/html; charset=utf-8");
            res.end(
              await vite.transformIndexHtml(
                "/__charts",
                '<!doctype html><html><head><meta charset="utf-8"></head><body><div id="root"></div><script type="module" src="/__chart-fixture.tsx"></script></body></html>',
              ),
            );
          });
        },
      },
    ],
  });
  let browser;
  let page;
  const results = [];
  try {
    await server.listen();
    browser =
      connectedBrowser ||
      (process.env.CHART_TEST_CDP
        ? await chromium.connectOverCDP(process.env.CHART_TEST_CDP)
        : await chromium.launch({
            headless: true,
            channel: process.platform === "win32" ? "msedge" : undefined,
          }));
    const context =
      connectedBrowser || process.env.CHART_TEST_CDP
        ? browser.contexts()[0]
        : await browser.newContext();
    page = await context.newPage();
    await page.addInitScript(() => localStorage.clear());
    const errors = [];
    page.on("pageerror", (error) => errors.push(error.message));
    const scenarios = [
      ...[400, 489, 1080].flatMap((width) =>
        [15, 18].flatMap((font) =>
          [false, true].map((dark) => ({
            width,
            font,
            dark,
            kind: width === 400 ? "study" : width === 489 ? "strategy" : "run",
            sample: "normal",
          })),
        ),
      ),
      ...[
        "title",
        "legend",
        "count",
        "drawdown",
        "time",
        "pie",
        "state",
      ].flatMap((sample) =>
        [false, true].map((dark) => ({
          width: 400,
          font: 18,
          dark,
          kind: "study",
          sample,
        })),
      ),
    ];
    for (const scenario of scenarios) {
      await page.setViewportSize({ width: scenario.width, height: 1000 });
      await page.goto(
        `${server.resolvedUrls.local[0]}__charts?${new URLSearchParams({ case: scenario.sample, font: String(scenario.font), dark: String(scenario.dark), kind: scenario.kind })}`,
      );
      await page.locator(".content-chart-canvas svg").waitFor();
      await page.evaluate(() => document.fonts.ready);
      await page.evaluate(
        () =>
          new Promise((done) =>
            requestAnimationFrame(() => requestAnimationFrame(done)),
          ),
      );
      const metrics = await page.evaluate(async () => {
        const element = document.querySelector(".content-chart-canvas");
        const rect = element.getBoundingClientRect();
        const texts = [...element.querySelectorAll("svg text")].filter(
          (node) => {
            let parent = node.parentElement;
            while (parent && parent !== element) {
              if (parent.hasAttribute("clip-path")) return false;
              parent = parent.parentElement;
            }
            return (
              node.getBoundingClientRect().width > 0 &&
              getComputedStyle(node).visibility !== "hidden"
            );
          },
        );
        const overflow = texts.flatMap((node) => {
          const box = node.getBoundingClientRect();
          return box.left < rect.left - 1 ||
            box.right > rect.right + 1 ||
            box.top < rect.top - 1 ||
            box.bottom > rect.bottom + 1
            ? [
                {
                  text: node.textContent,
                  left: box.left - rect.left,
                  right: box.right - rect.right,
                  top: box.top - rect.top,
                  bottom: box.bottom - rect.bottom,
                },
              ]
            : [];
        });
        const chart = window.chartFixture();
        const option = chart.getOption();
        return {
          width: rect.width,
          viewport: innerWidth,
          overflow,
          texts: texts.map((node) => node.textContent),
          color: option.color,
          titleInside: option.title?.length || 0,
          header: document.querySelector(".content-chart-heading")?.textContent,
          legend: option.legend?.[0]?.type,
          dataZoom: option.dataZoom?.length || 0,
          zoom: option.dataZoom?.[0]
            ? [option.dataZoom[0].start, option.dataZoom[0].end]
            : null,
        };
      });
      const label = `${scenario.sample}-${scenario.width}-${scenario.font}-${scenario.dark ? "dark" : "light"}`;
      await page.screenshot({
        path: resolve(output, `${label}.png`),
        fullPage: true,
      });
      results.push({ ...scenario, ...metrics });
      assert.equal(metrics.viewport, scenario.width, label);
      assert.deepEqual(metrics.overflow, [], `${label}: text outside chart`);
      if (scenario.sample === "title") {
        assert.equal(metrics.titleInside, 0);
        assert(metrics.header.includes("完整换行"));
      }
      if (scenario.sample === "count") {
        assert(metrics.texts.includes("0"));
        assert(!metrics.texts.some((text) => /^\d+\.5$/.test(text)));
      }
      if (scenario.sample === "pie") assert.equal(metrics.dataZoom, 0);
      if (scenario.sample === "legend") assert.equal(metrics.legend, "scroll");
      if (scenario.sample === "state")
        assert.deepEqual(metrics.zoom, [5, 95], "Keep authored initial zoom");
      if (scenario.sample === "normal" || scenario.sample === "state") {
        const restored = await page.evaluate(async () => {
          const chart = window.chartFixture();
          chart.dispatchAction({ type: "dataZoom", start: 20, end: 70 });
          chart.dispatchAction({ type: "legendUnSelect", name: "合成策略" });
          document.documentElement.dataset.theme =
            document.documentElement.dataset.theme === "dark"
              ? "light"
              : "dark";
          window.dispatchEvent(new Event("research-appearance"));
          await new Promise((done) => requestAnimationFrame(done));
          const option = chart.getOption();
          return {
            zoom: [option.dataZoom[0].start, option.dataZoom[0].end],
            hidden: option.legend[0].selected["合成策略"] === false,
          };
        });
        assert.deepEqual(
          restored,
          { zoom: [20, 70], hidden: true },
          "Theme must preserve user view",
        );
        await page.setViewportSize({
          width: scenario.width + 80,
          height: 1000,
        });
        await page.waitForFunction(
          () =>
            window.chartFixture().getWidth() ===
            document.querySelector(".content-chart-canvas").clientWidth,
        );
        const resized = await page.evaluate(() => {
          const option = window.chartFixture().getOption();
          return {
            zoom: [option.dataZoom[0].start, option.dataZoom[0].end],
            hidden: option.legend[0].selected["合成策略"] === false,
          };
        });
        assert.deepEqual(resized, restored, "Resize must preserve user view");
      }
    }
    assert.deepEqual(errors, []);
    await page.close();
    console.log(`PASS ${results.length} rendered scenarios: ${output}`);
  } finally {
    await writeFile(
      resolve(output, "results.json"),
      JSON.stringify(results, null, 2),
    );
    if (page) await page.close();
    if (browser && !connectedBrowser) await browser.close();
    await server.close();
  }
}
if (
  process.argv[1] &&
  pathToFileURL(resolve(process.argv[1])).href === import.meta.url
)
  await verifyCharts();
