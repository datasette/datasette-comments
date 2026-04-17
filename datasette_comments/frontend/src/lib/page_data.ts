export function loadPageData<T>(): T {
  const el = document.getElementById("pageData");
  if (el) return JSON.parse(el.textContent!);
  return (window as any).DATASETTE_COMMENTS_META;
}
