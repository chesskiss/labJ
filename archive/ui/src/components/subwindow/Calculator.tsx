import React, { useState, useEffect, useMemo, useCallback } from "react";
import { create, all } from "mathjs";
import type { CalculatorState, CalculatorEntry } from "../../types";
import "./Calculator.css";

interface CalculatorProps {
  initialContent: string;
  onStateChange: (state: CalculatorState) => void;
}

const DEFAULT_STATE: CalculatorState = {
  history: [],
  currentExpression: "",
  settings: {
    angleUnit: "deg",
    precision: 14,
  },
};

export const Calculator: React.FC<CalculatorProps> = ({
  initialContent,
  onStateChange,
}) => {
  const [state, setState] = useState<CalculatorState>(() => {
    try {
      return initialContent ? JSON.parse(initialContent) : DEFAULT_STATE;
    } catch {
      return DEFAULT_STATE;
    }
  });

  const [currentResult, setCurrentResult] = useState<string>("");
  const [error, setError] = useState<string>("");

  // Initialize math.js with custom units
  const math = useMemo(() => {
    const mathInstance = create(all);

    // Configure lab-specific units
    mathInstance.createUnit("uL", { definition: "1e-6 L", aliases: ["μL", "microliter"] });
    mathInstance.createUnit("mM", { definition: "1e-3 mol/L", aliases: ["millimolar"] });
    mathInstance.createUnit("uM", { definition: "1e-6 mol/L", aliases: ["μM", "micromolar"] });
    mathInstance.createUnit("nM", { definition: "1e-9 mol/L", aliases: ["nanomolar"] });
    mathInstance.createUnit("ng", { definition: "1e-9 g", aliases: ["nanogram"] });
    mathInstance.createUnit("pg", { definition: "1e-12 g", aliases: ["picogram"] });

    // Configure precision
    mathInstance.config({
      number: "BigNumber",
      precision: state.settings?.precision || 14,
    });

    return mathInstance;
  }, [state.settings?.precision]);

  // Format result for display
  const formatResult = useCallback((result: any): string => {
    if (result === null || result === undefined) return "";

    if (typeof result === "object" && result.toString) {
      return result.toString();
    }

    if (typeof result === "number") {
      // Round to avoid floating point issues
      if (Math.abs(result) < 1e-10) return "0";
      if (Math.abs(result) > 1e10 || Math.abs(result) < 1e-4) {
        return result.toExponential(6);
      }
      return result.toString();
    }

    return String(result);
  }, []);

  // Evaluate expression
  const evaluateExpression = useCallback(
    (expr: string) => {
      if (!expr.trim()) {
        setCurrentResult("");
        setError("");
        return;
      }

      try {
        const result = math.evaluate(expr);
        const formatted = formatResult(result);
        setCurrentResult(formatted);
        setError("");
        return formatted;
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : "Invalid expression";
        setError(errorMsg);
        setCurrentResult("");
        return null;
      }
    },
    [math, formatResult]
  );

  // Debounced evaluation
  useEffect(() => {
    const timer = setTimeout(() => {
      evaluateExpression(state.currentExpression);
    }, 300);

    return () => clearTimeout(timer);
  }, [state.currentExpression, evaluateExpression]);

  // Sync state to parent
  useEffect(() => {
    onStateChange(state);
  }, [state, onStateChange]);

  const handleExpressionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setState((prev) => ({
      ...prev,
      currentExpression: e.target.value,
    }));
  };

  const handleEvaluate = () => {
    const expr = state.currentExpression.trim();
    if (!expr) return;

    const result = evaluateExpression(expr);
    if (result !== null && result !== undefined) {
      const entry: CalculatorEntry = {
        id: `calc-${Date.now()}`,
        expression: expr,
        result: result,
        timestamp: new Date().toISOString(),
      };

      setState((prev) => ({
        ...prev,
        history: [entry, ...prev.history].slice(0, 50), // Keep last 50
      }));
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      handleEvaluate();
    }
  };

  const handleClear = () => {
    setState((prev) => ({
      ...prev,
      currentExpression: "",
    }));
    setCurrentResult("");
    setError("");
  };

  const handleClearHistory = () => {
    setState((prev) => ({
      ...prev,
      history: [],
    }));
  };

  const handleUseHistoryEntry = (entry: CalculatorEntry) => {
    setState((prev) => ({
      ...prev,
      currentExpression: entry.expression,
    }));
  };

  return (
    <div className="calculator-container">
      <div className="calculator-input-section">
        <input
          type="text"
          className="calculator-input"
          value={state.currentExpression}
          onChange={handleExpressionChange}
          onKeyPress={handleKeyPress}
          placeholder="Enter expression (e.g., 2*pi*r, 5 ml to uL)"
          autoFocus
        />
        <div className="calculator-result-display">
          {error ? (
            <span className="calculator-error">{error}</span>
          ) : (
            <span className="calculator-result">
              {currentResult && `= ${currentResult}`}
            </span>
          )}
        </div>
      </div>

      <div className="calculator-controls">
        <button onClick={handleEvaluate} className="calculator-btn">
          Evaluate
        </button>
        <button onClick={handleClear} className="calculator-btn">
          Clear
        </button>
        <button onClick={handleClearHistory} className="calculator-btn">
          Clear History
        </button>
      </div>

      <div className="calculator-history">
        <div className="calculator-history-header">History</div>
        {state.history.length === 0 ? (
          <div className="calculator-history-empty">No calculations yet</div>
        ) : (
          <div className="calculator-history-list">
            {state.history.map((entry) => (
              <div
                key={entry.id}
                className="calculator-history-item"
                onClick={() => handleUseHistoryEntry(entry)}
                title="Click to reuse expression"
              >
                <div className="calculator-history-expression">
                  {entry.expression}
                </div>
                <div className="calculator-history-result">= {entry.result}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="calculator-reference">
        <details>
          <summary className="calculator-reference-header">Quick Reference</summary>
          <div className="calculator-reference-content">
            <div className="calculator-reference-section">
              <strong>Basic:</strong> +, -, *, /, ^
            </div>
            <div className="calculator-reference-section">
              <strong>Scientific:</strong> sin, cos, tan, log, ln, exp, sqrt
            </div>
            <div className="calculator-reference-section">
              <strong>Statistics:</strong> mean([...]), std([...]), variance([...]), median([...])
            </div>
            <div className="calculator-reference-section">
              <strong>Units:</strong> ml, uL (μL), mM, uM (μM), nM, ng, pg
            </div>
            <div className="calculator-reference-section">
              <strong>Constants:</strong> pi, e
            </div>
            <div className="calculator-reference-section">
              <strong>Examples:</strong>
              <div className="calculator-reference-example">2*pi*r</div>
              <div className="calculator-reference-example">sqrt(16)</div>
              <div className="calculator-reference-example">5 ml to uL</div>
              <div className="calculator-reference-example">mean([1,2,3,4,5])</div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
};
