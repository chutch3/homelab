import '@testing-library/jest-dom/vitest';

// jsdom has no matchMedia implementation. Remove Vitest's undefined property
// so Mantine's feature detection uses its existing fallback.
if (typeof window.matchMedia !== 'function') {
  delete (window as Partial<Window>).matchMedia;
}

// jsdom does not implement layout, so Recharts' ResponsiveContainer would
// otherwise measure a 0x0 container and render no chart at all.
if (typeof window.ResizeObserver !== 'function') {
  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}
// Only Recharts' own measured wrapper gets a real size. Stubbing every element
// (including the legend it measures separately) made the legend report the same
// size as the whole chart, so it consumed the entire plot area for itself.
const CHART_SIZE = { width: 800, height: 300 };
function isChartContainer(element: Element): boolean {
  return element.classList.contains('recharts-responsive-container');
}
Object.defineProperties(HTMLElement.prototype, {
  offsetWidth: { configurable: true, get(this: HTMLElement) { return isChartContainer(this) ? CHART_SIZE.width : 0; } },
  offsetHeight: { configurable: true, get(this: HTMLElement) { return isChartContainer(this) ? CHART_SIZE.height : 0; } },
  clientWidth: { configurable: true, get(this: HTMLElement) { return isChartContainer(this) ? CHART_SIZE.width : 0; } },
  clientHeight: { configurable: true, get(this: HTMLElement) { return isChartContainer(this) ? CHART_SIZE.height : 0; } },
});
HTMLElement.prototype.getBoundingClientRect = function (this: HTMLElement) {
  const { width, height } = isChartContainer(this) ? CHART_SIZE : { width: 0, height: 0 };
  return { width, height, top: 0, left: 0, right: width, bottom: height, x: 0, y: 0, toJSON() {} } as DOMRect;
};
