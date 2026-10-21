import { Component } from "react";
export default class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error) {
    console.error("CustomerOps interface error", error);
  }
  render() {
    if (this.state.failed)
      return (
        <main className="empty">
          <h1>This page could not be displayed.</h1>
          <p>Reload the application to try again.</p>
          <button className="primary" onClick={() => window.location.reload()}>
            Reload
          </button>
        </main>
      );
    return this.props.children;
  }
}
