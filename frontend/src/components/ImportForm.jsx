import { useState } from "react";
import { importOrders } from "../api";

export default function ImportForm({ onImported }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;

    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const summary = await importOrders(file);
      setResult(summary);
      onImported();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="import-form" onSubmit={handleSubmit}>
      <h3>Import Orders from Excel</h3>
      <p className="hint">
        File must have columns: OrderID, ProductID, Qty, Price, OrderDate
      </p>
      <input
        type="file"
        accept=".xlsx,.xls"
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button type="submit" disabled={!file || busy}>
        {busy ? "Importing..." : "Import"}
      </button>
      {error && <p className="form-error">{error}</p>}
      {result && (
        <p className="import-result">
          Inserted {result.inserted}, failed {result.failed}.
          {result.errors.length > 0 && (
            <ul>
              {result.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          )}
        </p>
      )}
    </form>
  );
}
