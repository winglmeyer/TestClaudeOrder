import { useEffect, useState } from "react";
import { createOrder, deleteOrder, searchOrders, updateOrder } from "./api";
import Dashboard from "./components/Dashboard";
import ImportForm from "./components/ImportForm";
import OrderForm from "./components/OrderForm";
import OrderTable from "./components/OrderTable";
import SearchBar from "./components/SearchBar";

export default function App() {
  const [tab, setTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [filters, setFilters] = useState({});
  const [editingOrder, setEditingOrder] = useState(null);
  const [error, setError] = useState(null);

  async function refresh(currentFilters = filters) {
    try {
      setError(null);
      const results = await searchOrders(currentFilters);
      setOrders(results);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    refresh({});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSearch(newFilters) {
    setFilters(newFilters);
    refresh(newFilters);
  }

  async function handleFormSubmit(order) {
    if (editingOrder) {
      await updateOrder(editingOrder.OrderID, order);
      setEditingOrder(null);
    } else {
      await createOrder(order);
    }
    refresh();
  }

  async function handleDelete(orderId) {
    if (!confirm(`Delete order #${orderId}?`)) return;
    try {
      await deleteOrder(orderId);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="app">
      <h1>Order Enquiry System</h1>

      <div className="tabs">
        <button
          className={tab === "orders" ? "active" : ""}
          onClick={() => setTab("orders")}
        >
          Orders
        </button>
        <button
          className={tab === "dashboard" ? "active" : ""}
          onClick={() => setTab("dashboard")}
        >
          Dashboard
        </button>
      </div>

      {tab === "dashboard" ? (
        <Dashboard />
      ) : (
        <>
          {error && <p className="form-error">{error}</p>}

          <section className="panel">
            <OrderForm
              editingOrder={editingOrder}
              onSubmit={handleFormSubmit}
              onCancel={() => setEditingOrder(null)}
            />
          </section>

          <section className="panel">
            <ImportForm onImported={() => refresh()} />
          </section>

          <section className="panel">
            <h3>Search Orders</h3>
            <SearchBar onSearch={handleSearch} />
            <OrderTable
              orders={orders}
              onEdit={setEditingOrder}
              onDelete={handleDelete}
            />
          </section>
        </>
      )}
    </div>
  );
}
