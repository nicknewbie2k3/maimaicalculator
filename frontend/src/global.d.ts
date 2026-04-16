declare global {
  interface Window {
    html2canvas: (
      element: HTMLElement,
      options?: Record<string, unknown>
    ) => Promise<HTMLCanvasElement>
    bootstrap: {
      Modal: new (element: Element | null) => { show(): void }
    }
  }
}

export {}
