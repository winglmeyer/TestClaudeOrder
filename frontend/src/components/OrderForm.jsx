import { useEffect, useState } from "react";

const EMPTY_ORDER = { ProductID: "", Qty: "", Price: "", OrderDate: "" };

export default function OrderForm({ editingOrder, onSubmit, onCancel }) {
  const [form, setForm] = useState(EMPTY_ORDER);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (editingOrder) {
      setForm({
        ProductID: editingOrder.ProductID,
        Qty: editingOrder.Qty,
        Price: editingOrder.Price,
        OrderDate: editingOrder.OrderDate,
      });
    } else {
      setForm(EMPTY_ORDER);
    }
  }, [editingOrder]);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    try {
      await onSubmit({
        ProductID: form.ProductID,
        Qty: Number(form.Qty),
        Price: Number(form.Price),
        OrderDate: form.OrderDate,
      });
      setForm(EMPTY_ORDER);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <form className="order-form" onSubmit={handleSubmit}>
      <h3>{editingOrder ? `Edit Order #${editingOrder.OrderID}` : "Add Order"}</h3>
      {error && <p className="form-error">{error}</p>}
      <label>
        Product ID
        <input
          name="ProductID"
          type="text"
          value={form.ProductID}
          onChange={handleChange}
          required
        />
      </label>
      <label>
        Qty
        <input
          name="Qty"
          type="number"
          min="1"
          value={form.Qty}
          onChange={handleChange}
          required
        />
      </label>
      <label>
        Price
        <input
          name="Price"
          type="number"
          step="0.01"
          min="0"
          value={form.Price}
          onChange={handleChange}
          required
        />
      </label>
      <label>
        Order Date
        <input
          name="OrderDate"
          type="date"
          value={form.OrderDate}
          onChange={handleChange}
          required
        />
      </label>
      <div className="form-actions">
        <button type="submit">{editingOrder ? "Save" : "Add"}</button>
        {editingOrder && (
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
