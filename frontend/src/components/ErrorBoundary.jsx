import React from 'react';

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('React rendering error', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="error-boundary">
          <h1>Something went wrong</h1>
          <p>The UI failed to render. Please refresh the page or check the browser console.</p>
          <pre>{this.state.error.message}</pre>
        </main>
      );
    }

    return this.props.children;
  }
}
