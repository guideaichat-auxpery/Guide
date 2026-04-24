import { Component, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackHomeHref?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: unknown) {
    if (typeof console !== 'undefined' && console.error) {
      console.error('ErrorBoundary caught an error:', error, info);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      const message = this.state.error?.message || 'An unexpected error occurred while rendering this page.';
      const homeHref = this.props.fallbackHomeHref || '/';
      return (
        <div className="animate-fade-in p-4 sm:p-6">
          <div className="max-w-xl mx-auto bg-eco-card rounded-2xl border border-eco-border p-6 shadow-sm">
            <div className="flex items-start gap-3 mb-4">
              <div className="w-10 h-10 rounded-xl bg-soft-rose/40 flex items-center justify-center shrink-0">
                <AlertTriangle size={20} className="text-danger" />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-lg font-serif text-ink">Something went wrong</h2>
                <p className="text-sm text-eco-text/70 mt-1">
                  This page hit an unexpected problem. You can try again, or use the sidebar to navigate elsewhere.
                </p>
              </div>
            </div>
            <div className="p-3 bg-sand/30 rounded-xl text-xs text-eco-text/70 font-mono break-words mb-4">
              {message}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={this.handleReset}
                className="flex items-center gap-2 px-4 py-2 bg-leaf hover:bg-leaf-dark text-white text-sm font-medium rounded-xl transition-colors"
              >
                <RefreshCw size={14} />
                Try again
              </button>
              <a
                href={homeHref}
                className="flex items-center gap-2 px-4 py-2 bg-sand/40 hover:bg-sand/60 text-ink text-sm font-medium rounded-xl transition-colors"
              >
                <Home size={14} />
                Go home
              </a>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
