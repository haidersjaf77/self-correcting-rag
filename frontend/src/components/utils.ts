export function domain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function cleanTitle(title: string, url: string): string {
  // Page titles often end with " \ Anthropic" or " | Lil'Log"; keep the article name.
  const t = title.split(/\s[\\|]\s/)[0].trim()
  return t || domain(url)
}
