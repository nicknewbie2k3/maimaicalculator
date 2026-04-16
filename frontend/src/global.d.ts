declare global {
  interface Window {
    bootstrap: {
      Modal: new (element: Element | null) => { show(): void }
    }
  }
}

export {}
