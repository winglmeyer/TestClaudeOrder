import { useState } from "react";

const EMPTY_FILTERS = { order_id: "", product_id: "", date_from: "", date_to: "" };

export default function SearchBar({ onSearch }) {
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  function handleChange(e) {
    setFilters({ ...filters, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    onSearch(filters);
  }

  function handleReset() {
    setFilters(EMPTY_FILTERS);
    onSearch(EMPTY_FILTERS);
  }

  return (
    <form className="search-bar" onSubmit={handleSubmit}>
      <input
        name="order_id"
        type="number"
        placeholder="Order ID"
        value={filters.order_id}
        onChange={handleChange}
      />
      <input
        name="product_id"
        type="text"
        placeholder="Product ID"
        value={filters.product_id}
        onChange={handleChange}
      />
      <label>
        From
        <input
          name="date_from"
          type="date"
          value={filters.date_from}
          onChange={handleChange}
        />
      </label>
      <label>
        To
        <input
          name="date_to"
          type="date"
          value={filters.date_to}
          onChange={handleChange}
        />
      </label>
      <button type="submit">Search</button>
      <button type="button" onClick={handleReset}>
        Reset
      </button>
    </form>
  );
}
